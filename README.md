# Specimen Requirement Audit using CPID

This script downloads a Specimen Requirement (SR) audit using a Collection Protocol ID (CPID) from OpenSpecimen. It resolves Permissible Value (PV) IDs (such as specimen type and anatomic site) and produces a clean CSV output.

## Introduction

This script performs the following tasks:

- **Authenticates** with OpenSpecimen using the REST API  
- **Fetches PVs** for:
  - specimen_type  
  - anatomic_site  
- **Downloads SR audit** using the provided CPID  
- **Extracts the CSV** from the downloaded ZIP file  
- **Replaces PV IDs** with human-readable PV values  
- **Saves the final processed CSV**  

## Requirements

- Python 3.x  
- requests module  
- pandas module  

Install dependencies using:

```bash
pip install requests pandas
How to Run
Download or save the script (e.g., sr_audit.py).

Open a terminal and navigate to the script location.

Run the script with the command:

bash
Copy code
python3 sr_audit.py
When prompted, enter:

Collection Protocol ID (CPID)

Output filename

The script will generate a cleaned CSV with PV values instead of numerical IDs.

What the Script Does
Logs in and retrieves an API session token

Downloads and extracts the SR Audit CSV

Fetches PV values using the permissible value API

Replaces PV IDs with their text values

Saves the final CSV output

What I Learned
Using the OpenSpecimen REST API for authentication and data export

Fetching and mapping PV values programmatically

Handling ZIP files and CSV extraction in Python

Cleaning and transforming data for readability

Writing modular, reusable Python functions
