---
name: render-llms-full
description: Load context on Render (cloud platform — web services, static sites, workers, cron jobs, Postgres, Blueprints, Docker) from a bundled llms.txt reference. Use when deploying to Render, authoring render.yaml Blueprints, configuring build/deploy pipelines, or integrating the Render API.
---

# Render — Full Docs (render-llms-full)

Load Render abstractions relevant to the current task. Reference is ~805KB with 220 H1 pages — **do not read linearly**. Navigate by service type or feature.

## Reference

- `references/render-llms-full.txt` — single-file export from render.com/docs/llms-full.txt. Each `# ` at column 0 is a new doc page.

## When to use

- Deploying an app to Render (web service, static site, background worker, cron job, private service)
- Authoring or debugging `render.yaml` Blueprints
- Configuring build commands, start commands, env vars, health checks, auto-deploy
- Setting up Render Postgres, Redis (Key Value), or persistent disks
- Using Docker on Render or multi-service architectures
- Preview environments, deploy hooks, or CI integration (GitHub Actions)
- Integrating the Render API or managing via the CLI

## Workflow

1. **Classify the task** into one of Render's buckets:
   - Deploy flow (first deploy, free tier, coding-agent usage)
   - Service type (web, static, private, worker, cron)
   - Infrastructure (Postgres, Key Value, disks, networking, regions)
   - Build/deploy pipeline (buildpacks, Docker, hooks, previews)
   - Platform features (scaling, metrics, logging, RBAC, SSO, API)
2. **Grep by keyword.** Search `references/render-llms-full.txt` for the exact feature (e.g., `render.yaml`, `healthCheckPath`, `preDeployCommand`, `IPAllowList`, `autoscaling`, `Deploy Hook`).
3. **Locate the H1 page.** Match against section titles like `# Web Services`, `# Static Sites`, `# Background Workers`, `# Cron Jobs`, `# Multi-Service Architectures on Render`, `# Deploying on Render`, `# Docker on Render`, `# Preview Environments`, `# Service Previews`, `# Build Pipeline`, `# Deploy Hooks`, `# Supported Languages`.
4. **Pull YAML/command examples.** The docs include complete `render.yaml` snippets and CLI examples — prefer copying those over paraphrasing.
5. **Flag free-tier vs. paid differences** when they affect the task (spin-down, region availability, disk support).
6. **Summarize what you loaded** before proposing changes.

## Common grep anchors

- Blueprint: `render.yaml`, `services:`, `type: web`, `type: worker`, `type: cron`, `envVarGroups`, `databases:`
- Build/deploy: `buildCommand`, `startCommand`, `rootDir`, `preDeployCommand`, `autoDeploy`, `healthCheckPath`
- Infrastructure: `disk:`, `plan:`, `region:`, `numInstances`, `scaling`
- Integrations: `Deploy Hook`, `Service Previews`, `Preview Environments`, `GitHub Actions`
- Languages/runtime: `# Supported Languages`, `Docker on Render`

## Key H1 sections (for orientation)

Your First Render Deploy · Deploy for Free · Using Render with Coding Agents · Render Service Types · Static Sites · Web Services · Private Services · Background Workers · Cron Jobs · Multi-Service Architectures · Deploying on Render · Supported Languages · Build Pipeline · Deploy Hooks · Service Previews · Preview Environments · Docker on Render
