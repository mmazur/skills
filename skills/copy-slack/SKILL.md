---
name: copy-slack
description: Reformat the last assistant output to Slack mrkdwn and copy it to the clipboard.
user_invocable: true
agent_invocable: false
---

# copy-slack

Take your most recent assistant output and convert it from GitHub-flavored Markdown to Slack mrkdwn, then copy it to clipboard using the appropriate tool.

## Conversion rules

Apply these transformations:

| GFM | Slack mrkdwn |
|---|---|
| `**bold**` or `__bold__` | `*bold*` |
| `*italic*` or `_italic_` | `_italic_` |
| `~~strike~~` | `~strike~` |
| `# Heading` (any level) | `*Heading*` (bold line) |
| `[text](url)` | `<url\|text>` |
| `![alt](url)` | `<url\|alt>` |
| `` `inline code` `` | `` `inline code` `` (unchanged) |
| Fenced code blocks (``` ... ```) | ``` ... ``` (unchanged) |
| `> blockquote` | `> blockquote` (unchanged) |
| `- item` or `* item` | `• item` |
| `1. item` | `1. item` (unchanged) |
| Horizontal rules (`---`, `***`, `___`) | remove entirely |

## Steps

1. Retrieve the last assistant message text from this conversation.
2. Apply the conversion rules above. Process fenced code blocks first and leave their contents untouched. Then apply the remaining transformations to the rest of the text.
3. Copy the converted text to clipboard:
   - On linux pipe it to wl-copy, and if it fails, try xclip.
   - On macos use pbcopy.
   - On windows use clip.exe.
4. Confirm to the user that the text has been copied.
