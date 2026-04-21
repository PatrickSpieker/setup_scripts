---
name: firebase-basics
description: Firebase CLI setup and project management — install check, login, active project, create/init project, web SDK.
---

# Firebase Basics

Firebase CLI setup, auth, and project management.

## Prerequisites

- Node.js ≥ 20 (`node --version`).
- Always invoke the CLI via `npx -y firebase-tools@latest` — never the bare `firebase`. Pins to the latest release; avoids stale global installs.

```bash
npx -y firebase-tools@latest --version
```

Use `npx -y firebase-tools@latest <command> --help` to discover flags.

## Login

```bash
npx -y firebase-tools@latest login
```

- Headless / remote shell: add `--no-localhost`.
- Prints the signed-in user when already authenticated.

## Active project

```bash
npx -y firebase-tools@latest use
```

- Set/alias an existing project:
  ```bash
  npx -y firebase-tools@latest use --add <PROJECT_ID>
  ```
- Create a new one:
  ```bash
  npx -y firebase-tools@latest projects:create <project-id> --display-name "<display-name>"
  ```
  Project IDs: 6–30 chars, lowercase, digits and hyphens, globally unique.

## Initialize services in a repo

From the repo root (checks for existing `firebase.json` first):

```bash
npx -y firebase-tools@latest init
```

Interactive — pick features (Firestore, Functions, Hosting, etc.), associate a project, and write `firebase.json` + `.firebaserc`.

## Web SDK setup

See [references/web_setup.md](references/web_setup.md) for `apps:create`, `apps:sdkconfig`, and the canonical `firebase.js` init that other Firebase web skills import `app` from.
