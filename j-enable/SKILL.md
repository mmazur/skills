---
name: j-enable
description: Invoke only when the user explicitly runs /j-enable.
user_invocable: true
agent_invocable: false
---

# jira-enable

How to use RedHat's Jira using the `jira` cli command.

## Default project

Default to **AROSLSRE** for all new cards unless told otherwise.

## Piping

Prefer pipes over temp files. If a piped `jira` command appears to produce no
output, check that you're using `--plain` (and `--no-headers` where useful) —
the default interactive/table renderer doesn't pipe cleanly. Examples below
all use plain output so grep/awk work.

For multiline issue bodies, use `-b "$VAR"` with a shell variable — newlines
are preserved:

```bash
DESC=$(cat <<'EOF'
Line 1
Line 2
EOF
)
jira issue create -p AROSLSRE -t Task -s "Summary" -b "$DESC" ...
```

**Gotcha:** `\n` inside a quoted `-b "..."` literal is passed as the two
characters `\` and `n`, not a newline. Use a heredoc'd variable as above.

## Issue hygiene (required on every issue)

Every created/edited issue MUST have all of:

- **Priority** — never leave as "Undefined". Default to `Normal` if unspecified.
  Valid: `Minor`, `Normal`, `Major`, `Critical`, `Blocker`.
- **At least one component** — pick from the AROSLSRE component list below.
  Don't invent new ones.
- **At least one label** — reuse an existing label. Search the project before
  creating a new one (`jira issue list -p AROSLSRE --plain --columns LABELS`).
  Never create a near-duplicate (`oncall` vs `on-call`, `e2e` vs `e2e-test`).
  Don't create labels that will only ever apply to 1–2 issues.
- **Non-empty description**.
- **Parent epic** for every Story / Task / Bug. If no suitable epic exists in
  ARO or AROSLSRE, ASK the user — don't create an orphan.

### AROSLSRE components

| Component             | Use for                                                                  |
| --------------------- | ------------------------------------------------------------------------ |
| aro-hcp-ci            | Prow jobs, PR pipelines, CI stability, test infrastructure               |
| aro-hcp-docs          | Team docs, runbooks, onboarding guides, video catalog                    |
| aro-hcp-e2e           | E2E test failures, flakes, env issues, resource cleanup                  |
| aro-hcp-infra         | AKS clusters, nodepools, istio, region buildout, capacity                |
| aro-hcp-observability | Alerts, runbooks, Grafana, Kusto, logging, metrics                       |
| aro-hcp-oncall        | Oncall rotation work, interrupt bugs, cluster debugging, prod access     |
| aro-hcp-releases      | EV2 rollouts, stage/prod deployments, release process, image bumping     |
| aro-hcp-security      | CVEs, dependency bumps, FedRAMP/POAMs, image sourcing, vuln scanning     |
| aro-hcp-tooling       | Image updater, must-gather, CLI tools, PR lifecycle / agentic workflows  |

### Epic discipline

- **Always search existing epics before creating a new one:**
  ```bash
  jira issue list -p AROSLSRE -q 'issuetype = Epic AND status != Done' --plain
  ```
- Never create an empty epic — create or link at least one child issue.
- When in doubt, ask the user which epic to use.

### Stories vs Tasks

Break Stories into subtasks for concrete steps. Don't create a standalone
Task when the work belongs as a subtask under an existing Story.

**Creating a subtask:** use `-t Sub-task` and `-P <parent-key>` (parent is
required for sub-tasks, and points to the parent Story/Task, not an epic):

```bash
jira issue create -p AROSLSRE -t Sub-task -P AROSLSRE-961 \
  -s "Subtask summary" -y Normal -C aro-hcp-observability -l observability \
  -a "mmazur@redhat.com" -b "Description"
```

**Resolving an assignee:** if the user gives a partial name (e.g.
"Mariusz"), do NOT pass it straight to `-a` — display-name resolution is
fuzzy and can pick the wrong person. First find the exact account by
searching recent ARO / AROSLSRE issues:

```bash
jira issue list -p AROSLSRE -q 'assignee is not EMPTY' --plain --columns ASSIGNEE \
  | sort -u | grep -i "mariusz"
# then use the resolved email/username with -a, e.g. mmazur@redhat.com
```

If no match in AROSLSRE, repeat against `-p ARO`. Never wing it.

## Search before creating

Before creating ANY issue (epic, story, task, bug), search for existing open
cards that may already cover the planned work. Don't narrow prematurely.

**Rules:**
- Do NOT filter by assignee — the work may already be on someone else's plate.
  "My active card" in user shorthand usually means "a card I care about", not
  "a card assigned to me".
- Search summary AND description (`summary ~ "X" OR description ~ "X"`).
- Try multiple keywords / synonyms, not just the exact phrase. JQL `~` is
  fuzzy but won't catch synonyms.
- Search BOTH AROSLSRE and ARO (component `aro-hcp-service-lifecycle`).
- Include closed/done results, but filter by recency: only surface closed
  cards whose last activity was within the past four weeks
  (`updated >= -4w`). Older closed cards are noise — don't mention them.
- Show matches to the user and confirm before creating.

```bash
# Broad search across summary + description, open + recently-closed
jira issue list -p AROSLSRE \
  -q '(summary ~ "kw1" OR description ~ "kw1" OR summary ~ "kw2") AND (statusCategory != Done OR updated >= -4w)' \
  --plain --no-headers
```

## Creating issues

Minimum viable invocation (note: priority, component, label, parent epic
all required by hygiene rules above):

```bash
jira issue create -p AROSLSRE -t <type> -s "<summary>" -b "<description>" \
  -y Normal -C <component> -l <label> -P AROSLSRE-<epic>
```

Types: `Bug`, `Task`, `Story`, `Epic`.

Examples:

```bash
# Bug — explicit priority, component, label, parent epic
jira issue create -p AROSLSRE -t Bug -s "Fix login issue" \
  -y Major -C aro-hcp-oncall -l oncall -P AROSLSRE-456 \
  -b "Description"

# Task under a Story's parent epic
jira issue create -p AROSLSRE -t Task -s "Update onboarding doc" \
  -y Normal -C aro-hcp-docs -l docs -P AROSLSRE-456 \
  -b "Update the README"

# Story with assignee
jira issue create -p AROSLSRE -t Story -s "User can reset password" \
  -y Normal -C aro-hcp-tooling -l auth -P AROSLSRE-456 \
  -a "username" -b "As a user..."

# Multiline body via heredoc'd variable
DESC=$(cat <<'EOF'
Long description
spanning multiple lines
EOF
)
jira issue create -p AROSLSRE -t Task -s "Summary" \
  -y Normal -C aro-hcp-tooling -l tooling -P AROSLSRE-456 -b "$DESC"
```

### Useful flags
- `-t/--type`, `-s/--summary` (required), `-b/--body`
- `-y/--priority` (Minor, Normal, Major, Critical, Blocker — required)
- `-C/--component` (repeatable — required)
- `-l/--label` (repeatable — required)
- `-P/--parent` (parent epic — required for Story/Task/Bug)
- `-a/--assignee` (username, email, or display name)
- `--web` to open in browser after creation

**Tables in descriptions/comments:** Jira renders wiki-markup tables. Use
`||` for header cells and `|` for body cells, one row per line:

```
|| Header 1 || Header 2 || Header 3 ||
| cell a    | cell b    | cell c    |
| cell d    | cell e    | cell f    |
```

This renders as a styled Jira table (not just text). Works in both
descriptions (via `-b "$VAR"`) and comments.

## Epics

Epics need a custom `epic-name` field equal to the summary:

```bash
jira issue create -p AROSLSRE -t Epic -s "Velero image updating" \
  -b "Epic description" --custom "epic-name=Velero image updating"
```

Link an existing task to an epic (or reparent at any hierarchy level — `-P`
works on `edit` too):

```bash
jira issue edit AROSLSRE-123 -P AROSLSRE-456 --no-input
# or, equivalently, via custom field:
jira issue edit AROSLSRE-123 --custom "epic-link=AROSLSRE-456" --no-input
```

Create a task under an epic:

```bash
jira issue create -p AROSLSRE -P AROSLSRE-456 -t Task -s "Task summary" -b "Task description"
```

## Current user

```bash
jira me
```

Use the resulting email with `-a`.

## Moving issues

```bash
jira issue move AROSLSRE-123 "In Progress"
jira issue move AROSLSRE-123 "Done"
```

Note: `jira issue move` does NOT support `--no-input`.

**Editing descriptions:** use `-b "$VAR"` (same as create). Piping to
`jira issue edit --no-input` silently keeps the existing description — the
command reports success but ignores stdin.

```bash
DESC=$(cat /tmp/desc.txt); jira issue edit AROSLSRE-123 --no-input -b "$DESC"
```

**Before moving to "In Progress"**: the issue MUST have a sprint assigned —
otherwise it's invisible to boards and velocity tracking. Assign a sprint
first (see Sprints below).

**Before moving to "Done"/"Closed"**: confirm the work is actually complete.
Never bulk-close without explicit user confirmation.

## Sprints

List the active SL sprint (use `--plain` so the pipe works):

```bash
jira sprint list -p AROSLSRE --state active --plain --no-headers | grep SL
```

Only sprints containing `SL` belong to the Service Lifecycle team.

Add an issue to a sprint:

```bash
jira sprint add <SPRINT-ID> AROSLSRE-123
```

## Other

```bash
jira issue list -p AROSLSRE          # list project issues
jira open <issue-key>                # open in browser
```

## "My active card" workflow

When the user says "add my active card" (or similar), create a card with:

1. Project: AROSLSRE
2. Assignee: current user (from `jira me`)
3. Sprint: current active SL sprint
4. Status: moved to "In Progress" after creation
5. Remember to also pick a component and priority.

## Searching for "my" / team issues

Always query BOTH sources and combine results:

```bash
# 1. Dedicated project
jira issue list -p AROSLSRE

# 2. ARO project, Service Lifecycle component
jira issue list -p ARO -C aro-hcp-service-lifecycle
```
