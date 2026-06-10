# Build Workflow

Follow this framework for any non-trivial build task (≥3 files changed, new feature, or multi-workstream work).
Skip for quick bug fixes, one-liners, or throwaway scripts.

---

## Phase 0: Intake

Before writing any code, ask or confirm:
1. **What are we building?** (specific: "API endpoint", "React component", "data pipeline")
2. **What does success look like?** (concrete: what it does, shows, or produces when done)
3. **What exists already?** (relevant files, APIs, schemas, patterns to follow)
4. **Hard constraints?** (language, framework, existing interfaces to preserve)
5. **Priority?** (ship fast vs. production quality)
6. **GitHub or local?** — if GitHub: `gh repo create joeyfoley/<slug> --private`, init git, push initial commit, create `main` as default branch. If local-only: `git init`, no remote.

---

## Phase 1: Spec Discovery (before planning)

Spawn an Explore agent before committing to any plan. Its mandate is not general exploration — it has a specific checklist:

1. **Prior art across joeyfoley repos** — run `gh repo list joeyfoley --limit 50 --json name,description` then check repos with related names or descriptions for existing solutions. Don't rebuild what already exists. If found, note the repo, relevant files, and what can be reused or referenced.
2. **Architecture pattern in use** — microservices or monolithic? How are existing modules separated? Match this. Do not build monolithic where microservices exist.
3. **Parallelization patterns** — how does the codebase handle concurrent work? (async/await, workers, queues, threading). New work should follow the same model and run in parallel where possible.
4. **New methods being applied** — what libraries, patterns, or abstractions are actively being adopted? Don't reinvent what's already being introduced.
5. **Safety patterns** — how are auth, secrets, and external inputs handled? These must be followed exactly. Speed never overrides safety.
6. **Ownership boundaries** — which modules own which concerns? Don't bleed across them.

The Explore agent must return a **findings summary** with these six sections explicitly addressed. Phase 2 does not start until that summary exists. The Architect synthesizes it into the task decomposition — findings that contradict the plan invalidate the plan.

Use the `Plan` subagent for architecture questions that require reasoning across the findings (not just lookup).

---

## Phase 2: Plan (get approval before executing)

Decompose into tasks. Each task must have:
- **Clear deliverable**: a specific file, function, or deployed artifact
- **Ownership scope**: which files it creates or modifies (no overlap with other tasks)
- **Dependencies**: which tasks must complete first
- **Test criteria**: ≥2 numbered atomic conditions, e.g.:
  `"1. POST /auth returns 401 when token absent; 2. No credentials appear in logs"`

Present the plan. Do NOT proceed to Phase 3 until the user confirms.

---

## Phase 3: Execute (Workers)

- Spawn workers with the `general-purpose` subagent for implementation tasks
- Use `Explore` subagent for read-only research tasks
- Workers commit to branches; they do NOT merge to main
- Drain each batch fully before spawning the next

**Domain hints to inject into every worker prompt:**
- React/TypeScript: key prop on lists, loading+error states on async components, no hardcoded env values
- Python API: validate at system boundaries only, timeout on all external calls, no secrets in logs
- Generic: no hardcoded credentials, handle null/empty inputs, log errors with context

---

## Phase 4: Security Gate

**Multi-agent builds only** (agent-architect mode with parallel workers). Run `/security-review` after each worker batch — workers are headless, you can't trust what they wrote.

**Solo sequential work**: skip per-task gates. Run `/security-review` once at the end, only if the change touches auth, credentials, external inputs, or shared interfaces. Otherwise `/code-review` at ship time is sufficient.

Verdicts:
- **APPROVED** → proceed to Phase 5
- **APPROVED WITH CONDITIONS** → create follow-up tasks, proceed
- **REJECTED** → fix first (max 2 retries before escalating to user)

---

## Phase 5: Verify

After security approval, verify against the test criteria from Phase 2.

**For UI/app changes:** use the `verify` skill (behavioral, runtime observation).

**For everything else:** spawn a spec-blind general-purpose agent using this exact prompt template:

```
You are a spec-blind tester. You have not seen this implementation before.

Your only context is the test criteria below. Read them carefully, then read
the code at the paths listed, then verdict each criterion independently.

TEST CRITERIA:
<paste numbered criteria from Phase 2 plan — nothing else>

FILES TO INSPECT:
<list file paths the worker modified — no summaries, no context>

INSTRUCTIONS:
1. Read every criterion before opening any file.
2. For each criterion: find the code path that would satisfy or violate it.
   Quote the relevant lines. Do not infer intent from variable names alone.
3. Verdict each criterion: PASS | FAIL | CANNOT_DETERMINE
4. Final verdict: PASS (all criteria pass) | PASS_WITH_WARNINGS | FAIL

Do not read any other context from this conversation. Do not ask clarifying
questions. If a criterion is untestable from code alone, mark CANNOT_DETERMINE
and explain what runtime check would be needed.
```

Verdicts:
- **PASS** → mark task COMPLETE
- **PASS_WITH_WARNINGS** → note warnings, mark COMPLETE
- **FAIL** → fix and re-run (max 2 retries, then escalate using the format below)
- **CANNOT_DETERMINE** → use `verify` skill to check at runtime

---

## Escalation Format

Use this any time max retries are exceeded, a blocker can't be resolved, or context has been lost and I'm at risk of going in circles. Do not improvise — stop and surface:

```
ESCALATION: <task or phase name>

What was attempted:
- <attempt 1: what I did and what happened>
- <attempt 2: what I changed and what happened>

What's blocked:
<one sentence — the specific thing that isn't working>

Options:
A. <option> — <tradeoff>
B. <option> — <tradeoff>
C. <option> — <tradeoff>

Recommendation: <A/B/C> because <reason>

Files relevant to this decision:
<list paths>
```

This format exists because I lose context on long builds and start looping. When in doubt, escalate early rather than retry blindly.

---

## Phase 6: Ship

1. Confirm all tasks complete: `grep -c "| DONE |" .agent-project/manifest.log`
2. **If GitHub repo:**
   - Open a PR for each worker branch: `gh pr create --title "[DONE] <task>" --body "<test criteria + findings>"`
   - Merge squash: `gh pr merge --squash --delete-branch`
   - Tag the release: `git tag v<semver> -m "<goal> — shipped" && git push origin v<semver>`
   - Verify: `gh release create v<semver> --generate-notes`
3. **If local-only:**
   - Merge branches: `git merge --squash <branch> && git commit -m "[DONE] <task>"`
   - Tag: `git tag v<semver> -m "<goal> — shipped"`
4. Write a one-paragraph design-doc entry: decisions made, deviations, trade-offs
5. Drift check: re-read the Phase 2 approved plan, flag anything the implementation diverged from

---

## Agent Role → Model Map

| Role | Agent type | Model |
|------|------------|-------|
| Architect / planning | `Plan` | Opus (default for complex reasoning) |
| Researcher / discovery | `Explore` | Sonnet |
| Worker / implementation | `general-purpose` | Sonnet |
| Security review | `general-purpose` | Sonnet |
| Tester / verification | `general-purpose` | Sonnet |

Upgrade to Opus when: worker touches shared interfaces, auth logic, or cross-team contracts.

---

## State Tracking

- Use `TaskCreate` / `TaskUpdate` to track tasks during a session
- For multi-agent builds, maintain `.agent-project/manifest.log` (git-tracked)
- Commit at every phase transition: `git commit -m "log: PHASE_COMPLETE"`
- Git commit message conventions:
  - `[WORKER] <task>: <STEP> — <summary>`
  - `[DONE] <task> — <summary>`
  - `ESCALATION: <task> — <summary>`

---

## When to Use Multi-Agent vs Solo

| Situation | Approach |
|-----------|----------|
| < 3 tasks, single file area | Solo (no subagents) |
| 3–10 tasks, 1–2 domains | Solo with TaskCreate tracking |
| ≥5 tasks, 2+ independent domains | Spawn parallel workers via Agent tool |
| Full-stack (UI + API + DB) | Multi-team: spawn Explore researchers first, then workers |
