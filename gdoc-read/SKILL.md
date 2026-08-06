---
name: gdoc-read
description: Read a Google Doc or Google Sheet by URL (docs.google.com/) or ID and return its content.
user_invocable: true
agent_invocable: true
---

# gdoc-read

Read the content of a Google Doc or Google Sheet and return it in a useful format.

## Arguments

The user provides one of:

- A Google Docs URL like `https://docs.google.com/document/d/<ID>/edit?tab=<TAB_ID>`
- A Google Sheets URL like `https://docs.google.com/spreadsheets/d/<ID>/edit?gid=<GID>#gid=<GID>`
- A bare document/spreadsheet ID, optionally with a type hint ("doc" or "sheet")

Optional extra arguments:
- For docs: a tab ID (e.g. `t.9pduozosqbj2`) or tab name
- For sheets: a sheet name, sheet GID, or a cell range (e.g. `A1:D10`, `Sheet1!A1:D10`)

## Steps

### 1. Parse the input

Extract the document ID and type from the input:

- If the input contains `docs.google.com/document/d/`, it is a **doc**. Extract the ID from the path segment after `/d/`. If a `tab=` query parameter is present, note the tab ID.
- If the input contains `docs.google.com/spreadsheets/d/`, it is a **sheet**. Extract the ID from the path segment after `/d/`. If a `gid=` parameter is present (in query string or hash), note the GID.
- If the input is a bare ID (no URL), check if the user specified "doc" or "sheet". If unclear, assume **doc** and fall back to **sheet** on failure.
- Collect any additional arguments: tab ID/name for docs, sheet name/GID/range for sheets.

### 2a. Read a Google Doc

#### Create a unique working directory

```bash
GDOC_TMPDIR=$(mktemp -d /tmp/gdoc-read-XXXXXXXX)
```

Use `$GDOC_TMPDIR` for all temp files in this invocation.

#### Fetch the raw JSON

```bash
gws docs documents get \
  --params '{"documentId":"<ID>","includeTabsContent":true,"suggestionsViewMode":"PREVIEW_WITHOUT_SUGGESTIONS"}' \
  2>/dev/null > "$GDOC_TMPDIR/raw.json"
```

Check the file for errors (e.g. if it contains `"error"` at the top level). If it failed, report the error to the user.

#### Convert to Markdown

The conversion script lives at `scripts/gdoc2md.py`. Run:

```bash
python3 scripts/gdoc2md.py "$GDOC_TMPDIR/raw.json" --outdir "$GDOC_TMPDIR"
```

This prints a JSON summary to stdout listing tabs with their IDs, titles, and file paths, e.g.:

```json
{
  "document_id": "...",
  "title": "My Document",
  "tabs": [
    {"tab_id": "t.0", "title": "Tab 1", "file": "/tmp/gdoc-read/tab-1.md"},
    {"tab_id": "t.abc", "title": "Notes", "file": "/tmp/gdoc-read/notes.md"}
  ]
}
```

#### Read the right tab(s)

- If the user requested a specific tab (by ID or name from the URL or their message), read that tab's file.
- If no specific tab was requested and there is only one tab, read it.
- If no specific tab was requested and there are multiple tabs, show the user the tab list and ask which one(s) to read — unless the user indicated they want everything.

### 2b. Read a Google Sheet

#### If a specific sheet name and/or range is known

Use the `+read` helper:

```bash
gws sheets +read --spreadsheet <ID> --range "<RANGE>" 2>/dev/null
```

Where `<RANGE>` is:
- A sheet name: `SheetName` (reads the entire sheet)
- A sheet name with range: `SheetName!A1:D10`
- A bare range on the default sheet: `A1:D10`

The response is JSON with a `.values` array of arrays (rows of cells).

To present as CSV, pipe through jq:

```bash
gws sheets +read --spreadsheet <ID> --range "<RANGE>" 2>/dev/null | jq -r '.values[] | @csv'
```

#### If only a GID is known

First resolve it to a sheet name:

```bash
gws sheets spreadsheets get --params '{"spreadsheetId":"<ID>","fields":"sheets.properties"}' 2>/dev/null
```

Find the sheet whose `.properties.sheetId` matches the GID and use its `.properties.title` as the range in the `+read` call.

#### If no sheet is specified

Use the `spreadsheets get` call above to list sheets. If there is only one, read it. If there are multiple, show the user the list and ask which one to read.

### 3. Fallback

If the input was a bare ID assumed to be a doc and the `docs documents get` call fails, retry as a sheet using the sheet flow above.

### 4. Output

- For docs: the Markdown files are ready to read. Present the content to the user or use it for the task at hand.
- For sheets: present the data as CSV or a formatted table.
