---
layout: doc
title: Publish your docs to the hub
blurb: How a subsystem repo gets its documentation onto the League Robotics hub.
permalink: /publishing/
---

This page is the complete contract for publishing a subsystem's documentation to the
League Robotics hub. If you are an AI agent working in a subsystem repo, everything you
need is here — no other page required.

## How the hub works

- You author docs **in your own repo**, under `docs/wiki/`. Your repo is the source of truth.
- The hub (`League-Robotics.github.io`) keeps a registry, [`subsystems.yml`](https://github.com/League-Robotics/League-Robotics.github.io/blob/master/subsystems.yml), of which repos to publish.
- On each build, the hub **pulls** every registered repo's `docs/wiki/`, renders the docs,
  and publishes them at `https://league-robotics.github.io/subsystems/<name>/`.
- **The hub never writes to your repo, and you never push content to the hub.** You only
  send a lightweight "I changed" ping that triggers a rebuild.

```
your repo (docs/wiki/) --- ping ("docs-updated") ---> hub pulls + renders + publishes
        ^ source of truth                                     league-robotics.github.io
```

## What your repo needs

```
docs/wiki/
  _subsystem.yml          # subsystem metadata (title, blurb)
  index.md                # the map: links key docs + lists open tasks (see "Keep your wiki useful")
  overview.md             # one or more docs; each *.md becomes one page
  ...
.github/workflows/
  notify-docs-hub.yml     # pings the hub when docs/wiki/ changes
AGENTS.md                 # repo-root note so the next agent knows the wiki publishes here
```

### `docs/wiki/_subsystem.yml`

```yaml
name: my-subsystem        # stable key; match your registry entry
title: My Subsystem       # display name on the hub
blurb: One sentence describing this subsystem.
order: 100                # optional — lower sorts earlier on the home page
```

### Each `docs/wiki/*.md`

Every doc is normal Markdown with a front-matter header. Files whose names start with
`_` are ignored (that's how `_subsystem.yml` stays out of the doc list).

```markdown
---
title: Deploying ROS 2 with Ansible
blurb: How to provision a ROS 2 fleet across Pi / VM / Docker hosts.
order: 10            # optional — sort order within the subsystem
slug: deploy-ros     # optional — stable URL id; defaults to the filename
updated: 2026-06-13  # optional — source date; shown in the page footer
tags: [ros, ansible] # optional
---
Body markdown… (your real documentation)
```

| Field     | Required | Meaning                                                        |
|-----------|----------|----------------------------------------------------------------|
| `title`   | yes      | Heading and link text on the hub.                              |
| `blurb`   | yes      | One-line summary shown in the doc list.                        |
| `order`   | no       | Sort position within the subsystem (default 100).             |
| `slug`    | no       | Stable id → `/subsystems/<name>/<slug>/` (default: filename). |
| `updated` | no       | Source date (`YYYY-MM-DD`); surfaced in the page footer. `date` also works. |
| `tags`    | no       | Free-form list, carried through to the page.                   |

Every rendered page already shows when the hub last generated it in the footer; `updated`
adds the date *you* last touched the source.

### `.github/workflows/notify-docs-hub.yml`

Copy this **verbatim** (no edits needed — it figures out your repo name automatically):

```yaml
name: Notify docs hub
on:
  push:
    branches: [main]
    paths: ["docs/wiki/**"]
  workflow_dispatch:
jobs:
  notify:
    runs-on: ubuntu-latest
    steps:
      - name: Get app token
        id: app-token
        uses: actions/create-github-app-token@v1
        with:
          app-id: ${{ vars.DOCS_HUB_APP_ID }}
          private-key: ${{ secrets.DOCS_HUB_APP_PRIVATE_KEY }}
          owner: League-Robotics
          repositories: League-Robotics.github.io
      - name: Ping the hub to rebuild
        env:
          HUB_TOKEN: ${{ steps.app-token.outputs.token }}
        run: |
          curl -sSf -X POST \
            -H "Authorization: Bearer $HUB_TOKEN" \
            -H "Accept: application/vnd.github+json" \
            https://api.github.com/repos/League-Robotics/League-Robotics.github.io/dispatches \
            -d '{"event_type":"docs-updated","client_payload":{"repo":"${{ github.repository }}"}}'
```

> If your default branch isn't `main`, change `branches: [main]` accordingly.

### `AGENTS.md` (leave yourself a map)

Once the wiki is set up, drop an `AGENTS.md` at the **root of your repo**. Its job is to
tell the next agent — who may arrive months later with no context — what `docs/wiki/` is,
that this repo's docs are published to the hub, and where the authoritative instructions
live (this page). Copy this and replace `<name>`:

```markdown
# AGENTS.md — this repo publishes docs to the League Robotics hub

Documentation for this repo lives under `docs/wiki/`. Those files are the **source of
truth**; the League Robotics docs hub *pulls* them and publishes them at
<https://league-robotics.github.io/subsystems/<name>/>. The hub never writes back here —
edit docs in this repo only.

## What to do

When you learn something a future agent will need, write it into `docs/wiki/`:

- Each `docs/wiki/*.md` is one published page and needs `title:` and `blurb:` front
  matter. Files starting with `_` are not published.
- `docs/wiki/_subsystem.yml` holds this subsystem's `name` / `title` / `blurb`.
- Keep `docs/wiki/index.md` as the map: link the key docs and list open tasks / things to
  remember, so the next agent finds them fast.
- Add an `updated:` date to a doc's front matter when you change it.
- Changes under `docs/wiki/**` auto-ping the hub to rebuild (see
  `.github/workflows/notify-docs-hub.yml`).

## How to understand what to do

The complete contract — file formats, the notify workflow, how to register — is the
authoritative spec at **<https://league-robotics.github.io/publishing/>**. Start there.
```

## Keep your wiki useful for the next agent

The wiki isn't just public docs — it's the durable memory for agents working in this repo.
Two habits keep it that way:

- **Index your knowledge base.** As soon as you have more than a handful of docs — design
  notes, decisions, open tasks, gotchas a future agent must not forget — add a top-level
  `docs/wiki/index.md` with `order: 0` that links the important pages and lists the
  outstanding work. It sorts first, so it's the obvious entry point. *How* you organize it
  doesn't matter; that it's discoverable does.
- **Date your pages.** Make it clear when each page was written or published. The hub
  stamps every rendered page with the date it was generated (in the footer). To also show
  when *you* last revised the source, set `updated:` (or `date:`) in the doc's front
  matter — see the field table above.

## Authentication (one org-wide GitHub App)

Both the hub (pulling repos) and your repo (pinging the hub) authenticate with a single
**League Robotics Docs** GitHub App installed across the org. Each workflow mints a
short-lived, least-privilege token at run time — there are no long-lived personal tokens.

An org admin sets this up **once** (see the hub README). After that, the org-level
`vars.DOCS_HUB_APP_ID` and `secrets.DOCS_HUB_APP_PRIVATE_KEY` referenced above are already
available to your repo — you don't create any secrets yourself.

## Get registered

Open a pull request against the hub adding your repo to
[`subsystems.yml`](https://github.com/League-Robotics/League-Robotics.github.io/blob/master/subsystems.yml):

```yaml
subsystems:
  - name: my-subsystem
    repo: League-Robotics/my-repo
    branch: main
    docs_path: docs/wiki     # optional, this is the default
```

Once merged, your docs appear at `https://league-robotics.github.io/subsystems/my-subsystem/`
on the next build (your ping triggers one automatically).

## Troubleshooting

- **My docs aren't showing up.** Confirm your repo is in `subsystems.yml`, the `branch`
  matches, and `docs/wiki/_subsystem.yml` exists. A subsystem with no `docs/wiki/` is
  skipped (the hub build logs a warning but still deploys everyone else).
- **A page is missing.** Check that the file ends in `.md`, doesn't start with `_`, and has
  valid front matter with `title`/`blurb`.
- **The hub didn't rebuild after I pushed.** The notify workflow only fires on changes under
  `docs/wiki/**`. Run it manually from the Actions tab (`workflow_dispatch`), or an admin can
  re-run the hub's build manually.
