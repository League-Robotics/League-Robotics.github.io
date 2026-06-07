# Plan: League-Robotics docs hub (central-pull, full-mirror) + agent-facing publishing spec

## Context

The `League-Robotics` org has many subsystem repos (`ros-deploy`, `Romi`, `nezha`, …).
There is no single place to discover what each is or read its docs. This repo —
`League-Robotics.github.io` — is the **index/hub**: an org Pages site served at
`https://league-robotics.github.io/`.

The earlier plan in [docs/overview.md](docs/overview.md) had each subrepo *push*
metadata into the hub. We are **inverting that**: the hub owns a registry of subrepos
and does the whole rebuild itself — it **pulls** each subrepo's `docs/wiki/`, mirrors
the bodies, and publishes. Subrepos only **ping** the hub ("I changed"); they never
push content.

The headline deliverable is **published, self-describing documentation**: a remote AI
agent given only the URL `https://league-robotics.github.io/publishing/` must be able to
discover exactly how to structure its repo and which GitHub Action to add so its docs
appear on the hub. No back-and-forth required.

### Locked decisions (confirmed with user)
1. **Full-mirror** — collector copies markdown bodies into the hub; Jekyll renders them
   under one domain (each doc page also links back to its source repo).
2. **Dispatch-only** — subrepos send a `repository_dispatch` ping; the hub rebuilds on
   that (plus manual `workflow_dispatch` and push-to-hub). No cron.
3. **Hand-edited `subsystems.yml`** — one registry file in the hub; adding a subsystem is
   a PR editing it.
4. **Python collector** — `scripts/collect.py` (PyYAML + python-frontmatter).

> Note: this repo's default branch is currently **`master`**. All workflow `branches:`
> and dispatch URLs below assume `master`; flip to `main` if the branch is renamed.

## Architecture

```
 subsystem repo (ros-deploy)                 hub repo (League-Robotics.github.io)
 ┌─────────────────────────┐                 ┌──────────────────────────────────────┐
 │ docs/wiki/              │   repository_   │ subsystems.yml  (hand-edited registry) │
 │   _subsystem.yml        │   dispatch ping │ scripts/collect.py                     │
 │   *.md (front matter)   │ ───────────────►│   ├─ clone each registered repo        │
 │ .github/workflows/      │  "docs-updated" │   ├─ read _subsystem.yml + *.md fm     │
 │   notify-docs-hub.yml   │                 │   ├─ mirror bodies → subsystems/<n>/   │
 └─────────────────────────┘                 │   └─ write _data/subsystems.yml        │
        ▲ author docs here                    │ jekyll build → upload-pages → deploy   │
        │ (source of truth)                    └──────────────────────────────────────┘
        └─ hub never writes back                         published at league-robotics.github.io
```

Collector output (`subsystems/**`, `_data/subsystems.yml`) is **generated at build time
inside the Action and gitignored** — it never lands in the repo, keeping the hub clean.

## Files to create — hub repo

**Site scaffolding**
- `_config.yml` — title, `url`, `baseurl: ""`, `exclude: [examples/, scripts/, docs/, README.md, vendor/]`, minimal plugins.
- `Gemfile` — `jekyll` (+ `webrick`); pin via `Gemfile.lock` after first `bundle`.
- `index.html` — `layout: home`; iterates `site.data.subsystems`.
- `_layouts/default.html` — HTML skeleton, nav, footer, CSS link.
- `_layouts/home.html` — intro + grid of subsystem cards (sorted by `order`, then `title`).
- `_layouts/subsystem.html` — subsystem title/blurb + list of `page.docs` (each links to its hub page) + "source repo" link.
- `_layouts/doc.html` — `page.title`, blurb, "View source on GitHub" link, then `{{ content }}`.
- `assets/css/style.css` — small, dependency-free styling.
- `.gitignore` — `_site/`, `.bundle/`, `vendor/`, `subsystems/`, `_data/subsystems.yml`, `.collect-tmp/`.

**Registry + collector**
- `subsystems.yml` — the registry (hand-edited). Shape:
  ```yaml
  # Subsystem repos whose docs/wiki/ the hub pulls and renders.
  subsystems:
    - name: ros-deploy            # stable key → /subsystems/ros-deploy/
      repo: League-Robotics/ros-deploy
      branch: main                # branch to pull from
      docs_path: docs/wiki        # optional, default docs/wiki
    - name: romi
      repo: League-Robotics/Romi
      branch: main
  ```
- `scripts/collect.py` — for each registry entry:
  1. Shallow-clone `https://<token?>@github.com/<repo>.git` at `branch` into `.collect-tmp/<name>` (token only needed for private repos — see Tokens).
  2. Read `<docs_path>/_subsystem.yml` (title, blurb, order). Missing/invalid → **log a clear warning and skip that subsystem** (one bad repo must not fail the whole hub build).
  3. For each `<docs_path>/*.md` not starting with `_`: parse front matter (`python-frontmatter`); derive `slug` (front-matter `slug` else filename stem); collect `title`, `blurb`, `order`, `tags`.
  4. Write the body to `subsystems/<name>/<slug>.md` with injected Jekyll front matter: `layout: doc`, `title`, `blurb`, `subsystem`, `permalink: /subsystems/<name>/<slug>/`, `source_url: https://github.com/<repo>/blob/<branch>/<docs_path>/<file>`.
  5. Write `subsystems/<name>/index.md` (`layout: subsystem`, `permalink: /subsystems/<name>/`, `name`, `title`, `blurb`, `repo_url`, and `docs:` list sorted by `order` then `title`, each `{title, blurb, url, source_url}`).
  6. Append a summary `{name, title, blurb, order, url: /subsystems/<name>/}` to the home-page list.
  - After all entries: write `_data/subsystems.yml` (sorted list) for the home page; clean up `.collect-tmp/`.
- `scripts/requirements.txt` — `PyYAML`, `python-frontmatter`.

**Workflow**
- `.github/workflows/build-deploy.yml` — single pull→build→deploy job.
  Triggers: `repository_dispatch: {types: [docs-updated]}`, `workflow_dispatch`, `push: {branches: [master]}`.
  Steps: checkout → setup-python → `pip install -r scripts/requirements.txt` →
  `python scripts/collect.py` (env `DOCS_PULL_TOKEN`) → `ruby/setup-ruby` (bundler-cache) →
  `bundle exec jekyll build` → `actions/upload-pages-artifact` → `actions/deploy-pages`.
  `permissions: {contents: read, pages: write, id-token: write}`, `concurrency: {group: pages}`.

## Files to create — agent-facing published documentation (the core deliverable)

- `publishing/index.md` (`permalink: /publishing/`) — the **canonical, self-contained guide**.
  Sections: (a) how the hub works (pull model, you author in your own repo), (b) the
  contract — required files & directory layout, (c) field reference for `_subsystem.yml`
  and per-doc front matter, (d) the **exact notify workflow to copy** (inline YAML),
  (e) how to get registered (PR adding an entry to `subsystems.yml`), (f) the token your
  repo needs, (g) troubleshooting ("my docs aren't showing up"). Written so an agent
  fetching this one URL has everything.
- `AGENTS.md` (repo root) — short machine-oriented contract: the paste-able instruction
  (below), the required file list, and a link to `/publishing/`.
- `examples/subsystem-template/docs/wiki/_subsystem.yml` — copy-paste example.
- `examples/subsystem-template/docs/wiki/overview.md` — example doc with front matter.
- `examples/subsystem-template/.github/workflows/notify-docs-hub.yml` — the notify workflow template.
  (`examples/` is `exclude:`d from the Jekyll build so the YAML isn't processed.)
- Update `README.md` — what the hub is, link to `/publishing/`, and **maintainer** steps
  (how to add a repo to `subsystems.yml`, how to set the `DOCS_PULL_TOKEN` secret).
- Update [docs/overview.md](docs/overview.md) — revise to describe the final pull/full-mirror
  architecture (supersedes the original push-model draft) so the repo's own notes stay consistent.

### The subrepo contract (what we tell remote agents)

A subsystem repo needs exactly:
```
docs/wiki/
  _subsystem.yml          # name, title, blurb, order?
  <doc>.md                # front matter: title, blurb, order?, slug?, tags?
.github/workflows/
  notify-docs-hub.yml     # pings the hub on docs change
```

`docs/wiki/_subsystem.yml`:
```yaml
name: ros-deploy
title: ROS Deploy
blurb: Ansible deployment of ROS 2 across the robot fleet.
order: 20            # optional — position on the hub home page
```

Per-doc front matter:
```yaml
---
title: Deploying ROS 2 with Ansible
blurb: How to provision a ROS 2 fleet across Pi / VM / Docker hosts.
order: 10            # optional
slug: deploy-ros     # optional — stable id; default = filename
tags: [ros, ansible] # optional
---
Body markdown… (the real documentation; source of truth)
```

`notify-docs-hub.yml` (subrepo side — copy verbatim, change nothing):
```yaml
name: Notify docs hub
on:
  push:
    branches: [main]
    paths: ['docs/wiki/**']
  workflow_dispatch:
jobs:
  notify:
    runs-on: ubuntu-latest
    steps:
      - name: Ping the hub to rebuild
        env:
          HUB_TOKEN: ${{ secrets.DOCS_HUB_DISPATCH_TOKEN }}
        run: |
          curl -sSf -X POST \
            -H "Authorization: Bearer $HUB_TOKEN" \
            -H "Accept: application/vnd.github+json" \
            https://api.github.com/repos/League-Robotics/League-Robotics.github.io/dispatches \
            -d '{"event_type":"docs-updated","client_payload":{"repo":"${{ github.repository }}"}}'
```

### The paste-able instruction for remote agents (goes in AGENTS.md / handed to agents)

> To publish this repo's documentation to the League Robotics hub, follow the spec at
> https://league-robotics.github.io/publishing/. In short: create `docs/wiki/` with a
> `_subsystem.yml` (name, title, blurb) and one or more `*.md` docs that each have
> `title:` and `blurb:` front matter, then add the `notify-docs-hub.yml` workflow shown
> there. Open a PR against League-Robotics.github.io adding this repo to `subsystems.yml`.
> Do not copy anything into the hub repo — it pulls from here.

## Authentication — one org-wide GitHub App (documented in README + /publishing/)
A single **League Robotics Docs** GitHub App, installed org-wide, replaces all PATs.
Permissions: **Contents: Read & write**, **Metadata: Read**. Org-level
`vars.DOCS_HUB_APP_ID` + `secrets.DOCS_HUB_APP_PRIVATE_KEY` are shared to all repos.
Each workflow mints a short-lived, least-privilege installation token at run time via
`actions/create-github-app-token`:
- **Hub** (`build-deploy.yml`): `owner`-scoped read token → `collect.py` clones subsystem
  repos (env `DOCS_PULL_TOKEN`). Drop this step if all subrepos are public.
- **Subrepo** (`notify-docs-hub.yml`): token scoped to the hub repo only → `curl` the
  hub's `repository_dispatch`. (`GITHUB_TOKEN` can't dispatch cross-repo, so this is required.)
One-time app setup lives in the README.

## Verification (end-to-end)
1. **Hub renders before any automation.** Add a temporary entry to `subsystems.yml` for a
   public repo (or a local `.collect-tmp` fixture), run `python scripts/collect.py` then
   `bundle exec jekyll serve` locally; confirm home → subsystem → doc pages render with
   working "source" links. Then remove the fixture.
2. **Real pull.** Add `docs/wiki/` + `notify-docs-hub.yml` to `ros-deploy`; set the secrets;
   push a doc change; confirm the ping fires `build-deploy.yml`, the collector pulls, and the
   doc appears at `league-robotics.github.io/subsystems/ros-deploy/<slug>/`.
3. **Edit propagates.** Change a doc's `blurb` in `ros-deploy`, push; confirm the hub updates.
4. **Onboard a second repo** (`Romi`) via the PR-to-`subsystems.yml` step only; confirm it
   appears with no other hub edits.
5. **Resilience.** Point a registry entry at a repo with no `docs/wiki/`; confirm the build
   logs a warning and still deploys the other subsystems.

## Out of scope (by design)
- No GitHub wiki feature; no hand-maintained index (titles/blurbs come from front matter).
- No cron rebuild (dispatch-only); no auto-discovery of org repos (registry is explicit).
- No subrepo-push of content (hub pulls); collector output is never committed.
