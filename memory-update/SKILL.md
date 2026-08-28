---
name: memory-update
description: Review the current session and propose durable updates to Basic Memory.
argument-hint: "[hints about what is important to retain]"
disable-model-invocation: true
---

# Memory Update

Run this workflow only when the user explicitly invokes the skill.

Treat `$ARGUMENTS` as the user's priority hints. Review the current
conversation and identify information that is likely to remain useful in
future sessions:

- accepted decisions and their rationale
- durable requirements, preferences, and constraints
- verified commands and operational procedures
- architectural, implementation, or debugging discoveries
- unresolved questions and explicitly agreed next steps

Do not retain:

- secrets, credentials, tokens, or sensitive personal data
- routine conversational details
- temporary command output
- speculative conclusions that were not accepted
- information already represented accurately in Basic Memory

## Proposal

Before changing Basic Memory:

1. Use `search_notes` to find related existing notes.
2. Read relevant matches with `read_note`.
3. Prefer updating an existing note over creating a duplicate.
4. Present the proposed additions, edits, or deletions to the user.
5. Briefly explain why each proposed item merits long-term retention.
6. Wait for explicit approval.

Do not call `write_note`, `edit_note`, `move_note`, or `delete_note` before the
user approves the proposal.

## Apply

After approval:

1. Apply only the approved changes.
2. Preserve the user's wording where it affects meaning.
3. Include the user's priority hints where relevant.
4. Use concise structure, useful tags, observations, and relations.
5. Report exactly which notes were created, changed, moved, or deleted.
