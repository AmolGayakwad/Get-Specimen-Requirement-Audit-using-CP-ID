import requests
import time
import os
import zipfile
import io
import csv
import pandas as pd
import re
import ast

BASE_URL = "https://demo.openspecimen.org"
USERNAME = "<Enter_Username>"
PASSWORD = "Enter_Password"

def get_token():
    url = f"{BASE_URL}/rest/ng/sessions"
    data = {"loginName": USERNAME, "password": PASSWORD, "domainName": "openspecimen"}
    resp = requests.post(url, json=data, headers={"Content-Type": "application/json"})
    resp.raise_for_status()
    return resp.json().get("token")

def fetch_pvs(token, attribute):
    url = f"{BASE_URL}/rest/ng/permissible-values/v"
    params = {
        "searchString": "",
        "attribute": attribute,
        "includeOnlyLeafValue": "true",
        "includeOnlyRootValue": "false",
        "query": "",
        "maxResults": 1000
    }
    resp = requests.get(url, headers={"X-OS-API-TOKEN": token}, params=params)
    resp.raise_for_status()
    return {pv["id"]: pv.get("value") or pv.get("attributeValue") or str(pv["id"]) for pv in resp.json()}

def fetch_pv_by_id(token, attr, pv_id):
    url = f"{BASE_URL}/rest/ng/permissible-values/v/{pv_id}"
    resp = requests.get(url, headers={"X-OS-API-TOKEN": token})
    resp.raise_for_status()
    pv = resp.json()
    return pv.get("value") or pv.get("attributeValue") or str(pv["id"])

def get_cp_events(cp_id, token):
    url = f"{BASE_URL}/rest/ng/collection-protocol-events?cpId={cp_id}"
    resp = requests.get(url, headers={"X-OS-API-TOKEN": token})
    resp.raise_for_status()
    return [{"id": e["id"], "label": e["eventLabel"]} for e in resp.json()]

def get_specimen_requirements(cp_id, event_label, token):
    url = f"{BASE_URL}/rest/ng/specimen-requirements"
    params = {"cpId": cp_id, "eventLabel": event_label, "includeChildReqs": "true"}
    resp = requests.get(url, headers={"X-OS-API-TOKEN": token}, params=params)
    resp.raise_for_status()
    return resp.json()

def flatten_requirements(req_list):
    flat = []
    for r in req_list:
        flat.append({"id": r["id"], "eventLabel": r.get("eventLabel")})
        children = r.get("children", [])
        if children:
            flat.extend(flatten_requirements(children))
    return flat

def export_specimen_req_audit(req_id, token):
    now = int(time.time() * 1000)
    last_year = now - 365 * 24 * 60 * 60 * 1000
    payload = {
        "recordIds": [int(req_id)],
        "entities": ["SpecimenRequirement"],
        "includeModifiedProps": True,
        "startDate": last_year,
        "endDate": now
    }
    url = f"{BASE_URL}/rest/ng/audit/export-revisions"
    resp = requests.post(url, json=payload, headers={"X-OS-API-TOKEN": token, "Content-Type": "application/json"})
    resp.raise_for_status()
    return resp.json().get("fileId")

def wait_for_file(file_id, token, max_wait=60):
    url = f"{BASE_URL}/rest/ng/audit/revisions-file?fileId={file_id}"
    for _ in range(max_wait // 5):
        resp = requests.get(url, headers={"X-OS-API-TOKEN": token}, stream=True)
        if resp.status_code == 200:
            return resp
        elif resp.status_code == 404:
            time.sleep(5)
        else:
            resp.raise_for_status()
    raise Exception("File not ready.")

def split_changes(log):
    parts, cur, lvl = [], "", 0
    for ch in log:
        if ch == "," and lvl == 0:
            parts.append(cur.strip())
            cur = ""
        else:
            if ch in "[{": lvl += 1
            elif ch in "]}": lvl -= 1
            cur += ch
    if cur:
        parts.append(cur.strip())
    return parts

def convert_id_to_pv(cell, pv_maps, token=None, field_name=None):
    if pd.isna(cell):
        return cell
    s = str(cell)

    ids = re.findall(r'\{id=(\d+)\}', s)
    if ids:
        values = []
        for i in ids:
            i_int = int(i)
            val = pv_maps.get(i_int)
            if val is None and token and field_name:
                try:
                    val = fetch_pv_by_id(token, field_name, i_int)
                    pv_maps[i_int] = val
                except:
                    val = str(i_int)
            values.append(val if val else str(i_int))
        return ", ".join(values)

    try:
        val = ast.literal_eval(s)
        if isinstance(val, list):
            values = []
            for item in val:
                if isinstance(item, dict) and 'id' in item:
                    pv_val = pv_maps.get(int(item['id']))
                    if pv_val is None and token and field_name:
                        try:
                            pv_val = fetch_pv_by_id(token, field_name, int(item['id']))
                            pv_maps[int(item['id'])] = pv_val
                        except:
                            pv_val = str(item['id'])
                    values.append(pv_val)
            return ", ".join(values)
        if isinstance(val, dict) and 'id' in val:
            pv_val = pv_maps.get(int(val['id']))
            if pv_val is None and token and field_name:
                try:
                    pv_val = fetch_pv_by_id(token, field_name, int(val['id']))
                    pv_maps[int(val['id'])] = pv_val
                except:
                    pv_val = str(val['id'])
            return pv_val
    except:
        pass

    return s

def transform_csv(input_csv, output_csv, req_id, event_label, pv_maps, token):
    grouped, all_fields = {}, set()

    with open(input_csv, encoding="utf-8") as f:
        for _ in range(7):
            next(f, None)
        reader = csv.DictReader(f)

        for row in reader:
            ch_log = row.get("Change Log", "")
            if not ch_log:
                continue

            key = (row.get("Timestamp", ""), row.get("User", ""), row.get("Operation", ""))

            if key not in grouped:
                grouped[key] = {}

            for c in split_changes(ch_log):
                if "=" not in c:
                    continue
                field, val = c.split("=", 1)
                field, val = field.strip(), val.strip()
                val = convert_id_to_pv(val, pv_maps, token=token, field_name=field)
                grouped[key][field] = val
                all_fields.add(field)

    unwanted_cols = ["preBarcodedTube", "fixative", "receiver", "source_file"]
    all_fields = sorted(f for f in all_fields if f not in unwanted_cols)

    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        header = ["Modified Date", "Modified By", "Operation", "Req ID", "Event Label"] + all_fields
        writer.writerow(header)

        for (date, user, op), fields in grouped.items():
            row = [date, user, op, req_id, event_label] + [fields.get(f, "") for f in all_fields]
            writer.writerow(row)

def download_csv(file_id, token, folder, req_id, event_label, pv_maps):
    resp = wait_for_file(file_id, token)
    zip_bytes = io.BytesIO(resp.content)
    with zipfile.ZipFile(zip_bytes, "r") as zf:
        csv_files = [f for f in zf.namelist() if f.endswith(".csv")]
        raw_path = os.path.join(folder, f"req_{req_id}_raw.csv")
        with zf.open(csv_files[0]) as src, open(raw_path, "wb") as out_f:
            out_f.write(src.read())

    wide_path = os.path.join(folder, f"req_{req_id}_wide.csv")
    transform_csv(raw_path, wide_path, req_id, event_label, pv_maps, token)
    os.remove(raw_path)

def merge_csvs(folder, output_file):
    csv_files = [f for f in os.listdir(folder) if f.endswith('_wide.csv')]
    merged_df = pd.DataFrame()
    for file in csv_files:
        file_path = os.path.join(folder, file)
        try:
            df = pd.read_csv(file_path, dtype=str)
            merged_df = pd.concat([merged_df, df], ignore_index=True)
        except Exception as e:
            print(f"Skipping {file}: {e}")
    merged_output = os.path.join(folder, output_file)
    merged_df.to_csv(merged_output, index=False)
    print(f"Merged {len(csv_files)} files into: {merged_output}")

def main():
    cp_id = input("Enter CP ID: ").strip()
    token = get_token()
    events = get_cp_events(cp_id, token)
    if not events:
        print("No events found.")
        return

    pv_attributes = ["anatomic_site", "specimen_type"]
    pv_maps = {}
    for attr in pv_attributes:
        pv_maps.update(fetch_pvs(token, attr))

    folder = f"specimen_req_audits_cp_{cp_id}"
    os.makedirs(folder, exist_ok=True)

    for e in events:
        reqs = get_specimen_requirements(cp_id, e["label"], token)
        flat_reqs = flatten_requirements(reqs)

        for r in flat_reqs:
            try:
                file_id = export_specimen_req_audit(r["id"], token)
                if file_id:
                    download_csv(file_id, token, folder, r["id"], e["label"], pv_maps)
            except:
                pass

    merge_csvs(folder, f"cp_{cp_id}_merged_specimen_req_audit_final.csv")

if __name__ == "__main__":
    main()
