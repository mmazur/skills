---
name: gdoc-upload
description: Upload a Markdown file to Google Drive as a Google Doc.
user_invocable: true
agent_invocable: true
---

# gdoc-upload

Upload a local Markdown file to Google Drive, converting it to a Google Doc.

## Arguments

The user provides a relative file path as the argument. If no argument is given, ask for it.

## Steps

1. Verify the file exists.
2. Choose a good document title: use the first `# heading` in the Markdown if one exists; if there is no heading, infer a title from the opening content of the document; as a last resort, derive a human-friendly title from the filename (strip extension, replace hyphens/underscores with spaces, title-case). Use this as `<FILENAME>` below.
3. Run:
   ```
   gws drive files create \
     --upload <FILE_PATH> \
     --upload-content-type text/markdown \
     --json '{"name":"<FILENAME>","mimeType":"application/vnd.google-apps.document"}' \
     --format json
   ```
   where `<FILENAME>` is the basename of the file (without directory).
3. On failure, show the error.
4. On success, parse the JSON output and report the file name, Google Drive file ID, and a link: `https://docs.google.com/document/d/<ID>`
5. Finally switch the document to pageless mode:
   ```
   gws docs documents batchUpdate \
     --params '{"documentId": "<ID>"}' \
     --json '{
       "requests": [
         {
           "updateDocumentStyle": {
             "documentStyle": {
               "documentFormat": {
                 "documentMode": "PAGELESS"
               }
             },
             "fields": "documentFormat.documentMode"
           }
         }
       ]
     }'
   ```
6. Share the document with Red Hat (view access):
   ```
   gws drive permissions create \
     --params '{"fileId": "<ID>"}' \
     --json '{"role": "reader", "type": "domain", "domain": "redhat.com", "allowFileDiscovery": false}'
   ```
