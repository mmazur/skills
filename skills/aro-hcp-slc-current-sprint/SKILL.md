---
name: aro-hcp-slc-current-sprint
description: Fetch the current active Service Lifecycle Team sprint from Jira for the AROSLSRE project. Use this skill whenever the user asks about the current sprint, active sprint, what sprint we're in, or sprint dates. Also use when any other operation needs to know the current sprint (e.g., creating cards, assigning to current sprint).
---

# Fetching the Current Sprint

The sprint data in this Jira instance requires specific knowledge to fetch efficiently. Follow these steps exactly to get the current sprint in a single call.

## The One-Shot Recipe

Call `mcp__atlassian__searchJiraIssuesUsingJql` with these exact parameters:

- **cloudId**: `redhat.atlassian.net`
- **jql**: `project = AROSLSRE AND sprint in openSprints() AND sprint not in futureSprints()`
- **fields**: `["summary", "customfield_10020"]`
- **maxResults**: `1`

The sprint information is in `customfield_10020` (not a standard field like `sprint`). It returns an array of sprint objects. The active one looks like:

```json
{
  "id": 64473,
  "name": "ARO HCP - SL - Sprint 288",
  "state": "active",
  "boardId": 11286,
  "startDate": "2026-03-16T10:26:43.834Z",
  "endDate": "2026-03-30T10:26:33.000Z"
}
```

## Why this works

- `openSprints()` returns sprints that are currently active.
- Adding `NOT in futureSprints()` excludes planned-but-not-started sprints, leaving only the truly active one.
- We only need 1 result since we just need any issue in the active sprint to read the sprint metadata from `customfield_10020`.

## What NOT to do

- Do not call `getAccessibleAtlassianResources` first. The cloudId is always `redhat.atlassian.net`.
- Do not request the field as `sprint` — it won't return sprint details. The custom field `customfield_10020` is where Jira Next-Gen / Software stores sprint data.
- Do not use `searchAtlassian` (Rovo search) for this — it searches content, not sprint metadata.

## Presenting the result

Report the sprint name, ID, start date, and end date. The sprint ID is needed for subsequent operations (e.g., assigning issues to the sprint). The sprint naming convention is `ARO HCP - SL - Sprint <number>`.
