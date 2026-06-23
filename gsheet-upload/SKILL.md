---
name: gsheet-upload
description: Upload a CSV / TSV file to Google Drive as a Google Sheet.
user_invocable: true
agent_invocable: true
---

# gsheet-upload

Upload a local CSV (or TSV) file to Google Drive, converting it to a Google Sheet.

## Arguments

The user provides a relative file path as the argument. If no argument is given, ask for it.

## Steps

1. Verify the file exists and has a `.csv` or `.tsv` extension.
2. Choose a good spreadsheet title: derive a human-friendly title from the filename (strip extension, replace hyphens/underscores with spaces, title-case).
3. Determine the upload content type: `text/csv` for `.csv` files, `text/tab-separated-values` for `.tsv` files.
4. Run:
   ```
   gws drive files create \
     --upload <FILE_PATH> \
     --upload-content-type <CONTENT_TYPE> \
     --json '{"name":"<TITLE>","mimeType":"application/vnd.google-apps.spreadsheet"}' \
     --format json
   ```
5. On failure, show the error.
6. On success, parse the JSON output and report the file name, Google Drive file ID, and a link: `https://docs.google.com/spreadsheets/d/<ID>`
7. Share the spreadsheet with Red Hat (view access):
   ```
   gws drive permissions create \
     --params '{"fileId": "<ID>"}' \
     --json '{"role": "reader", "type": "domain", "domain": "redhat.com", "allowFileDiscovery": false}'
   ```
