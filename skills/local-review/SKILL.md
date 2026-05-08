---
name: local-review
description: Address inline `//r <thought>` review comments left in the working tree. Pairs with `/vscode-review` — open changed files, leave `//r` markers as you read, then run this skill to have Claude apply the requested changes and remove the markers (or push back inline as `//c <reply>` when something needs discussion). Use after a local review pass and before committing.
---

# Local Review

Process inline review markers a user has left in the working tree. Apply the request and remove the marker, or push back as `//c` when something needs discussion. Then report what happened.

## Marker conventions

- **`//r <thought>`** — review request. Use the variant that matches the file's comment style:
  - `//r` (or `// r`) — C-style comment languages: JS, TS, Go, Rust, Java, Swift, C/C++, Scala, Kotlin, Dart.
  - `#r` (or `# r`) — `#`-comment languages: Python, shell, YAML, TOML, Ruby, Make.
  - `<!--r ... -->` (or `<!-- r ... -->`) — HTML, Markdown, XML.
- **`//c <reply>`** — *your* (Claude's) pushback. Use the matching prefix family. Means "didn't apply this as written; here's why."

A marker should be on its own line, directly above (or below) the code it refers to. Trailing-on-a-code-line markers are tolerated but discouraged because removing them is messier.

## Workflow

1. **Find every `r` marker.**
   ```bash
   rg --vimgrep '(^|\s)(//|#|<!--)\s*r\s' .
   ```
   Output is `file:line:col:content`. If exit code is 1 (no matches), stop and tell the user there's nothing to address.

2. **Process each marker, in file order, top-to-bottom within a file.**
   For each marker:
   - Read at least 30 lines of surrounding context (more if the request references something further away).
   - Interpret the request from the comment text after the `r`.
   - Decide:
     - **Apply** when the request is clear, scoped, and you can carry it out without breaking invariants or unrelated code.
       - Make the requested code change.
       - **Remove the marker.** If the marker is on its own line, delete the entire line. If it trails a line of code, strip just the comment portion (and any trailing whitespace) from the line.
     - **Push back** when the request is unclear, conflicts with surrounding structure, or you have a concrete objection (correctness, scope creep, contradicts another marker, etc.).
       - Replace the leading `r` in the marker with `c` and rewrite the comment text as a one-line reply explaining why. Keep the same comment style (`//c`, `#c`, `<!--c ... -->`).
       - Do **not** make code changes for that marker.
   - One `Edit` call per marker is fine — keep changes localized and reviewable.

3. **Verify.** Re-run the find command from step 1. There must be **zero `r` markers left** — only `c` replies remain. If any `r` is still there, you missed it; process it and re-verify.

4. **Report in chat.** Two short sections, then stop:
   - **Applied** — bullet per addressed marker, formatted `file:line — what changed`.
   - **Pushed back** — bullet per `//c` reply, formatted `file:line — one-sentence reason`.
   - If you applied a best-guess interpretation of an ambiguous request, surface that in the Applied bullet so the user can correct.

## Scope and rules

- **Search the whole working tree**, not just changed files. The user may leave a marker in an adjacent area they noticed during review.
- **Don't stage, commit, or push.** This skill mutates the working tree only. The user re-runs `/vscode-review` to inspect the result and decides when to commit.
- **Leave existing `//c <reply>` lines alone.** Those are previous pushbacks. The user iterates by editing surrounding code, or by replacing `c` with `r` to ask for another pass.
- **No surprise cleanup.** Don't refactor, rename, or fix unrelated issues "while you're here" — only what the markers explicitly ask for. If you notice something worth flagging, mention it in the chat report instead of touching the code.
- **Don't touch markers in committed code from before the branch started** unless the user asks. Heuristic: if `git blame` shows the marker line predates `git merge-base main HEAD`, treat it as out-of-scope and surface it in the chat report.

## Typical flow

```
/vscode-review            # open changed files
# user reads, sprinkles `//r ...` markers
/local-review             # this skill — applies and replies
/vscode-review            # see the result; sprinkle more markers if needed
/local-review             # iterate
/gh-ship                  # commit + PR when satisfied
```
