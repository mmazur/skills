---
name: pr-babysit
description: >-
  Monitor a pushed PR's CI jobs on a cron. Auto-fix code failures,
  retest transient job failures, and report when all jobs are green or
  retries are exhausted. Use when user says "babysit this PR" or asks to watch CI.
user_invocable: true
agent_invocable: true
---

# pr-babysit

Continuously monitor a PR's CI pipeline, fix what you can, retest transient
failures, and report back when everything is resolved.

## 1. Determine the PR

Resolve the target PR in this order:

1. If the user passed a PR URL or number as an argument, use that.
2. Otherwise run `gh pr view --json number,url,headRefName` from the current
   branch. If no PR is associated, tell the user and stop.

Store the **PR number**, **repo** (owner/name), and **head branch** for later use.

## 2. Start the cron loop

Create a **durable** cron job that fires every 15 minutes using `CronCreate`:

Inform the user that babysitting has started and that results will appear
inline.

## 3. On each cron tick — check CI status

Run:

```bash
gh pr checks <number> --repo <owner/repo> --json name,state,description,detailsUrl
```

Classify every check into one of these buckets:

| State        | Bucket       |
|--------------|--------------|
| SUCCESS / NEUTRAL / SKIPPED | **green** |
| PENDING / QUEUED / IN_PROGRESS / EXPECTED | **in-flight** |
| FAILURE / ERROR / CANCELLED / ACTION_REQUIRED / TIMED_OUT / STALE | **red** |

If everything is green or in-flight (no red), skip to **step 6** (exit
conditions). Otherwise proceed to investigate each red job.

## 4. Investigate a red job

For each red job, open its details URL with `WebFetch`/`web_fetch` (or `gh api`) to read
the build log. Determine which category the failure falls into:

### 4a. Code defect in the PR

The log points to a compile error, test failure, linter violation, or similar
issue **caused by code in this PR**.

**Action:**

1. Check out the head branch and pull latest (if needed)
2. Identify the commit that introduced the breakage.
3. Fix the issue.
4. Amend the fix onto the commit that introduced the problem:
   - If the breaking change is the **latest** commit, use
     `git add <files> && git commit --amend --no-edit && git push --force-with-lease`.
   - If it is an **older** commit, use interactive-rebase fixup
     (`git commit --fixup=<sha>`, then
     `git rebase --autosquash <base>`,
     then `git push --force-with-lease`).
   
   Always use `--force-with-lease` (never bare `--force`).
5. Record that a fix was pushed so the next tick can verify the re-run.

### 4b. Transient / infrastructure failure

The log shows a flaky test, network timeout, image-pull error, cloud quota
issue, or other failure **not caused by code in this PR**.

**Action — retest the job (once):**

First check the internal retry ledger (see step 5). If this job has **not**
been retried yet:

- **Prow / OpenShift CI job** (indicators: the openshift-ci bot posted
  comments, the job name matches a Prow naming pattern like
  `pull-ci-*` or `e2e-*`, or the details URL points to
  `prow.ci.openshift.org` / `deck-internal-ci.apps.*`):
  Post a PR comment to retest all failed jobs:

  ```bash
  gh pr comment <number> --repo <owner/repo> --body '/retest'
  ```

  If only specific jobs need retesting:

  ```bash
  gh pr comment <number> --repo <owner/repo> --body '/test <job-name>'
  ```

- **GitHub Actions job:**

  ```bash
  gh run rerun <run-id> --repo <owner/repo> --failed
  ```

- **Other CI system:** If no rerun mechanism is available, note it in the
  summary and move on.

Mark the job as retried in the ledger.

### 4c. Unknown / unclear failure

Cannot confidently classify the failure.

**Action:** Do **not** attempt any fix or retest. Record the job for the final
summary and flag it for the user's attention.

## 5. Check for review comments

On each tick, fetch PR review comments and issue comments posted since the last
tick (or since babysitting started, on the first tick):

```bash
gh api repos/<owner>/<repo>/pulls/<number>/comments --json id,body,user,path,line,createdAt,updatedAt
gh api repos/<owner>/<repo>/pulls/<number>/reviews --json id,body,user,state,createdAt
gh api repos/<owner>/<repo>/issues/<number>/comments --json id,body,user,createdAt
```

Track the timestamp of the last seen comment to avoid reporting the same
comment twice.

### What to look for

- **Automated reviewers** (CodeRabbit, Copilot, SonarCloud, Codecov, etc.) —
  identified by bot user type or known bot usernames. Summarize their
  suggestions grouped by file/concern.
- **Human reviewers** — summarize their feedback, requested changes, and
  questions.

### What to report

For each new comment or review, tell the user:

1. **Who** left the comment (human name or bot name).
2. **Where** — file and line, or "general" for PR-level comments.
3. **What** they suggest — a one-line summary of the comment.
4. **Actionability** — your assessment of what can be done:
   - If it's a straightforward fix you can make (typo, naming, missing null
     check), say so and offer to fix it.
   - If it requires a design decision or the user's judgment, flag it as
     needing the user's input.
   - If it's informational only (e.g., Codecov coverage report), just
     summarize the key numbers.

**Do not auto-fix review comments** — only report them with your assessment.
Wait for the user to approve before making changes based on review feedback.

### Responding to review comments

When a fix for a review comment has already been pushed (either as part of a
code-defect fix or a prior user-approved change):

1. **Reply** to the review comment thread explaining what was done.
2. **Resolve** the conversation thread via the GraphQL API:

   ```bash
   gh api graphql -f query='mutation { resolveReviewThread(input: {threadId: "<THREAD_ID>"}) { thread { isResolved } } }'
   ```

3. To get thread IDs, query the PR's review threads:

   ```bash
   gh api graphql -f query='query {
     repository(owner: "<owner>", name: "<repo>") {
       pullRequest(number: <number>) {
         reviewThreads(first: 50) {
           nodes { id isResolved comments(first: 1) { nodes { body author { login } } } }
         }
       }
     }
   }'
   ```

When a review comment is intentionally **not** addressed (e.g. disagreed with
the suggestion), reply explaining why but do **not** resolve the thread — leave
it for the reviewer.

### Tracking seen reviews

Track **review IDs** (not just timestamps) across ticks to avoid missing or
re-reporting reviews. When a new review appears (ID not in the seen set),
process all its comments. The cron prompt must carry the set of seen review
IDs forward between ticks.

## 6. Retry ledger (CI jobs)

Maintain an in-memory mapping of `job-name -> retried: bool` across ticks.
Rules:

- A job gets **at most one** automatic retest attempt.
- After the retry, if the job fails again on a subsequent tick, move it to the
  **"gave up"** list and stop acting on it.
- If the user gives explicit instructions to retry again (e.g., via a message),
  reset that job's counter.

## 7. Exit conditions

At the end of each tick, evaluate:

| Condition | Action |
|-----------|--------|
| All checks are **green** | Exit: delete the cron job, write a success summary |
| All red checks have been **retried once and failed again** or are **code issues already fixed** and now pending re-run | Continue watching |
| All remaining red checks are in the **gave-up** list (retry exhausted, unclear) and nothing is in-flight | Exit: delete the cron job, write a summary with the unresolved jobs |

When exiting remove the cron job.

## 8. Summary format

When the cron loop exits, post a summary to the user:

```
## PR Babysit Summary — #<number>

**Status:** All green | Partial — action needed

### Fixes pushed
- <commit-sha-short>: <one-line description of fix>

### Retested (transient failures)
- <job-name>: retested → passed | retested → still failing

### Review comments
- <reviewer>: <file:line> — <one-line summary> (actionable / needs your input / info only)

### Needs attention
- <job-name>: <reason / link to log>

Babysitting ended. Cron job removed.
```

## What NOT to do

- **Do not create superflous commits.** Fixes must be amended/squashed onto the
  commit that introduced the breakage.
- **Do not retest a job more than once** unless the user explicitly asks.
- **Do not retest a job that failed due to a code defect** — fix the code
  instead.
- **Do not push without `--force-with-lease`** when amending/rebasing.
- **Do not keep the cron running** after all checks are resolved or retries
  are exhausted.
- **Do not silently swallow errors.** If something unexpected happens, include
  it in the summary.
