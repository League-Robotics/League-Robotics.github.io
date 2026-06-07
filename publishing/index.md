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
  overview.md             # one or more docs; each *.md becomes one page
  ...
.github/workflows/
  notify-docs-hub.yml     # pings the hub when docs/wiki/ changes
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
tags: [ros, ansible] # optional
---
Body markdown… (your real documentation)
```

| Field   | Required | Meaning                                                        |
|---------|----------|----------------------------------------------------------------|
| `title` | yes      | Heading and link text on the hub.                              |
| `blurb` | yes      | One-line summary shown in the doc list.                        |
| `order` | no       | Sort position within the subsystem (default 100).             |
| `slug`  | no       | Stable id → `/subsystems/<name>/<slug>/` (default: filename). |
| `tags`  | no       | Free-form list, carried through to the page.                   |

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
