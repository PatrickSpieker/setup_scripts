---
name: spec-it
description: Grill the user one question at a time to extract a complete implementation plan into the conversation context, update CONTEXT.md / ADRs as terms and decisions crystallise, then ship the resulting plan as a PR off main. Use after exploration when the user has an idea but not a written-down spec yet.
---

# Spec It

Pull a full implementation plan out of the user's head and into the conversation, then ship it as a GitHub PR. Combines the grilling discipline of the old `grill-with-docs` skill with the PR-as-plan shipping flow of the old `ship-plan` skill.

## Pipeline this fits into

```
/explore-repo  →  /spec-it  →  PR (plan in description, ready for implementation)
```

The skill trusts the user — no check that exploration has happened. If the user invokes it cold, the grilling will surface what's missing.

## What it does

1. **Grills.** One question at a time, walks the design tree, resolves dependencies before moving on, recommends an answer for each question, cross-references the code when claims are made.
2. **Updates docs inline.** As domain terms resolve, edits `CONTEXT.md`. As irreversible decisions crystallise, sparingly offers ADRs in `docs/adr/`.
3. **Writes up the plan.** When the user signals done, synthesises the conversation into a 3-section plan (The What / The How / Testing).
4. **Ships.** Branches off main as `spec/<slug>`, empty marker commit `plan: <slug>`, one commit per doc file changed during grilling, push, open PR with the plan as the description.

## Hard rules

- **One question at a time.** Wait for the user's answer before moving on. No batched questionnaires.
- **Recommend an answer for every question.** Never ask "what do you want?" without a proposal. The grill exists to surface decisions, not to make the user write a spec from scratch.
- **Resolve dependencies before moving on.** If question B's answer depends on A, resolve A first. Walk the tree depth-first.
- **Cross-reference the code.** When the user makes a claim about how the system works, verify it before letting it shape the plan. If the code disagrees, surface the contradiction inline.
- **Branch off main, never push to main.** Always a fresh `spec/<slug>` branch from `origin/main` (or whatever the repo's default branch is).
- **Don't invent the plan.** If the user says "ship it" within the first couple of turns and the conversation has nothing concrete in it, refuse — the skill needs a real spec to ship.

## During grilling

### Cross-reference with code

When the user states how something works, check whether the code agrees. If you find a contradiction, surface it: _"Your code cancels entire Orders, but you just said partial cancellation is possible — which is right?"_

### Sharpen fuzzy language

When the user uses vague or overloaded terms, propose a precise canonical term. _"You're saying 'account' — do you mean the Customer or the User? Those are different things."_

### Challenge against the glossary

When the user uses a term that conflicts with `CONTEXT.md`, call it out immediately. _"Your glossary defines 'cancellation' as X, but you seem to mean Y — which is it?"_

### Discuss concrete scenarios

Stress-test domain relationships with specific scenarios. Invent edge cases that force the user to be precise about boundaries.

### Update CONTEXT.md inline

When a term is resolved, update `CONTEXT.md` right then — don't batch. See [CONTEXT-FORMAT.md](./CONTEXT-FORMAT.md). If `CONTEXT.md` doesn't exist, create it lazily on the first resolved term. If `CONTEXT-MAP.md` exists at the repo root, update the right context file (see [DOMAIN-AWARENESS.md](./DOMAIN-AWARENESS.md)).

Don't couple `CONTEXT.md` to implementation details. Only terms meaningful to domain experts.

### Offer ADRs sparingly

Only offer to write an ADR when **all three** are true:

1. **Hard to reverse** — the cost of changing your mind later is meaningful.
2. **Surprising without context** — a future reader will wonder _"why did they do it this way?"_
3. **The result of a real trade-off** — there were genuine alternatives and a specific reason for the choice.

If any of the three is missing, skip. See [ADR-FORMAT.md](./ADR-FORMAT.md).

## Termination

Grilling ends when the user signals it: _"that's enough,"_ _"ship it,"_ _"we're done,"_ _"go,"_ etc. Don't propose ending it yourself — keep going until the user calls it. (If the user signals done before any real grilling has happened, refuse and ask for a starting point.)

## Plan write-up

After the user signals done, synthesise the conversation into a markdown plan with **exactly these three sections**:

```markdown
## The What

The APIs, the interfaces. Function signatures, route shapes, data types, message
formats — the contract a consumer of this work would see. No implementation detail.

## The How

Quick notes on the implementation decisions made during grilling. Why this storage
choice, why this concurrency pattern, why this error model. Bullet-point or short
prose; this section is a reference, not a tutorial.

## Testing

Test approach: unit vs integration boundaries, what the test fixtures look like,
specific edge cases the grilling surfaced that need explicit coverage.
```

Don't pad. Each section should earn its space.

## Slug + title

Agent reads the just-written plan and derives:

- **Title**: short imperative phrase capturing the plan's intent (e.g. `Background indexing for the search service`).
- **Slug**: kebab-case, lowercase, alphanumeric + dashes only, ≤ 50 chars. Derived from the title.

```bash
slug=$(echo "$title" \
  | tr '[:upper:]' '[:lower:]' \
  | sed 's/[^a-z0-9]/-/g; s/-\+/-/g; s/^-//; s/-$//' \
  | cut -c1-50 | sed 's/-$//')
```

No confirm step — the grilling itself was the confirmation.

## Ship

### 1. Pre-flight

```bash
git rev-parse --is-inside-work-tree >/dev/null || { echo "Not in a git repo"; exit 1; }
git fetch origin >/dev/null
default_branch=$(gh repo view --json defaultBranchRef -q .defaultBranchRef.name)
branch="spec/$slug"
git rev-parse --verify "$branch" 2>/dev/null && { echo "Branch $branch exists; pick a different slug."; exit 1; }
```

**Moat SSH preflight** (mirrors `/gh-ship`):

```bash
ssh -T git@github.com 2>&1
```

- `Hi <user>!` → SSH works, proceed.
- `Permission denied (publickey)` → stop, tell the user:
  > `git push` will fail — the `ssh:github.com` grant's SSH agent has no keys loaded.
  > On your host machine, run `ssh-add` (load your key), then restart the Moat run.

  Do **not** switch remotes to HTTPS, unset insteadOf rules, or push via the GitHub API.

### 2. Stash doc changes, branch, commit, restore

The grilling will typically have left `CONTEXT.md` and zero or more ADR files modified in the working tree. Move them onto the new branch as separate commits, with the empty marker commit anchoring the branch.

```bash
# Stash any modified/new doc files so we can branch off clean main.
git stash push -u -- CONTEXT.md docs/adr/*.md src/*/CONTEXT.md src/*/docs/adr/*.md 2>/dev/null
# (refine the stash glob to match the repo's actual layout — single- or multi-context)

git checkout -b "$branch" "origin/$default_branch"
git commit --allow-empty -m "plan: $slug"

# Restore doc changes if any were stashed.
git stash list | grep -q . && git stash pop || true

# Commit each doc file separately so reviewers see one decision per commit.
for f in $(git status --porcelain | awk '/^.M|^A |^\?\?/ {print $2}'); do
  case "$f" in
    *CONTEXT.md)        msg="docs(context): update glossary for $slug" ;;
    *docs/adr/*.md)     msg="docs(adr): $(basename "$f" .md | sed 's/^[0-9]*-//')" ;;
    *)                  continue ;;
  esac
  git add "$f"
  git commit -m "$msg"
done
```

### 3. Push

```bash
gh auth setup-git 2>/dev/null || true
git push -u origin "$branch"
```

### 4. Open the PR

```bash
gh pr create \
  --base "$default_branch" \
  --title "$title" \
  --body-file - <<'EOF'
<the plan from "Plan write-up" above, verbatim — The What / The How / Testing>
EOF
```

Print the PR URL. Implementation commits land on the same branch later; the PR description (the plan) stays as the historical record of intent. If the plan changes during implementation, edit the PR description with `gh pr edit --body-file`.

## Edge cases

- **User invokes spec-it with no idea yet:** start by asking _"What's the rough goal?"_ — don't refuse. The skill's job is to extract intent, including the first formulation of it.
- **User signals done after one or two questions:** refuse and explain — the plan would be too thin to be useful in a PR. Push back: _"What about the X dimension?"_
- **Slug collision (`spec/<slug>` exists locally or remotely):** stop and ask for a new slug. Don't silently append `-2`.
- **Working tree dirty before grilling starts:** OK if the dirty files are unrelated. The skill will only stash/move CONTEXT.md and ADR files. If unrelated changes are large, warn but proceed.
- **No `origin` remote:** stop — `gh pr create` would fail anyway.
- **Default branch isn't `main`:** the script reads it from `gh repo view`; works for `master` or anything else.
- **Repo has no `CONTEXT.md` or `docs/adr/`:** create them lazily on the first resolved term / accepted ADR. Don't pre-create empty files.
- **Repo uses `CONTEXT-MAP.md` (multi-context):** see [DOMAIN-AWARENESS.md](./DOMAIN-AWARENESS.md). Infer which bounded context the topic belongs to; if unclear, ask.

## Moat

The `ssh:github.com` grant proxies the host's SSH agent into the container — private keys never enter the container. The system git config rewrites HTTPS GitHub URLs to SSH, so all git transport goes through SSH. `gh` subcommands use the `github` grant's API access. See `/gh-ship` for the full SSH-failure protocol.

Read if present: `AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING.md`.
