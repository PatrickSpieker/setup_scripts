---
name: obo
description: Focus a sprawling conversation down to the precise task by interrogating the user one question at a time ("obo" = one by one). Invoke mid-conversation after context, patterns, or options have piled up — it distills what's really being attempted, names the ambiguities, asks a capped set of one-at-a-time questions, then restates the tightened task before any work. Use when the user types "/obo", says "one by one", or wants to cut through a context dump and pin down exactly what to do.
---

# OBO (One By One)

A focusing tool for mid-conversation. When context has piled up and the thread has drifted into dumped patterns and half-baked options, `/obo` cuts back to the precise task — by asking one question at a time until the target is sharp.

The job is to *narrow*, not to explore. Resist adding scope. Every question should remove ambiguity about the one thing being attempted.

## Steps

1. **Distill, then confirm.** Before asking anything, restate the precise task in 1–2 sentences and name the key ambiguities or assumptions you're carrying. Ask the user to confirm or correct that framing. Do not move on until they do.

2. **Ask one at a time — capped.** Ask up to ~5 questions, one per turn, fewer if the task is already clear. Never batch. Each question must resolve a real ambiguity that changes what you'd do — skip any whose answer wouldn't.

3. **Mixed format, chosen per question.** When there's a clear decision space, give 2–4 numbered options with their trade-offs and state your lean (put the lean first). When the point is genuinely exploratory, ask open-ended.

4. **Wrap up.** Restate the now-tightened task plus the decisions the answers settled, then ask "good to proceed?" Do no work until the user says go.

## Rules

- Narrow, never widen. If you catch scope creeping in, name it and drop it.
- Stop early if the task is clear before hitting the cap — fewer questions is better.
- One question per turn, always.
- No work — edits, commands, files — until the final confirmation.
