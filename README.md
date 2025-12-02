Specimen Requirement Audit using CPID

This script downloads a Specimen requirement audit using CPID from OpenSpecimen, resolves Permissible Value (PV) IDs (such as specimen type and anatomic site), and produces a clean CSV output.

Introduction

The script performs the following tasks:

Authenticates with OpenSpecimen using the REST API.

Fetches PVs for:

specimen_type

anatomic_site

Downloads SR's Audit using CPID.

Extracts the CSV from the ZIP.

Replaces PV IDs with human-readable PV values.

Saves the final processed CSV.

Requirements

Python 3.x

requests

pandas

Install dependencies:

pip install requests pandas

How to Run

Download or save the script (e.g., sr_audit.py).

Open a terminal and navigate to the script location.

Run:

python3 sr_audit.py

Enter:

Enter CP ID

Output filename

A cleaned CSV will be generated with PV values instead of numerical IDs.

What the Script Does

Logs in and retrieves an API session token.

Downloads and extracts the SR Audit CSV.

Fetches PV values using the permissible value API.

Replaces PV IDs with their text values.

Saves the output in CSV

What I Learned

Using the OpenSpecimen REST API for authentication and data export.

Fetching and mapping PV values programmatically.

Handling ZIP files and CSV extraction in Python.

Cleaning and transforming data for readability.

Writing modular, reusable Python functions.
