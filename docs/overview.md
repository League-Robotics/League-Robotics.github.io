# Overview: League-Robotics docs hub

> **This supersedes the original push-model draft.** The system is **central-pull**: this
> repo (the hub) owns a registry and pulls each subsystem's docs. The detailed, executable
> design is in [implementation-plan.md](implementation-plan.md); the author-facing contract
> is published at <https://league-robotics.github.io/publishing/>.

## What this is

The `League-Robotics` org has many subsystem repos (`ros-deploy`, `Romi`, `nezha`, …) with
no single place to discover or read their docs. This repo, `League-Robotics.github.io`, is a
Jekyll **documentation hub** served at <https://league-robotics.github.io/>. We do **not**
use the GitHub wiki feature.

## How it works (central-pull, full-mirror)

- Authoring stays in each subsystem repo, under `docs/wiki/` (the source of truth).
- The hub keeps a hand-edited registry, [`../subsystems.yml`](../subsystems.yml), of which
  repos to publish.
- On each build, the hub **pulls** every registered repo's `docs/wiki/`, mirrors the doc
  bodies, and renders them under one domain at `/subsystems/<name>/`.
- Subsystems never push content to the hub. They only send a `repository_dispatch` ping
  (`docs-updated`) that triggers a rebuild. The hub does the entire rebuild itself.

```
subsystem repo (docs/wiki/) --- ping ---> hub: pull all repos → render → deploy Pages
        ^ source of truth                          league-robotics.github.io
```

## Key decisions

- **Full-mirror** — docs render on the hub (each page also links back to its source repo).
- **Dispatch-only** — rebuilds on a subsystem ping, manual run, or push to the hub. No cron.
- **Hand-edited `subsystems.yml`** — onboarding a repo is a PR adding one entry.
- **Python collector** — `scripts/collect.py` (PyYAML + python-frontmatter).
- **One org-wide GitHub App** for auth (no long-lived PATs); workflows mint short-lived tokens.

See [implementation-plan.md](implementation-plan.md) for the full file list, the collector
behavior, the workflows, and end-to-end verification steps.
