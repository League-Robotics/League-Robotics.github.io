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

- You author docs **in your repo's GitHub wiki** (`{repo}/wiki`). The wiki is the source of truth.
- The hub (`League-Robotics.github.io`) keeps a registry, [`subsystems.yml`](https://github.com/League-Robotics/League-Robotics.github.io/blob/master/subsystems.yml), of which repos to publish.
- On each build, the hub **clones** every registered repo's wiki, renders the docs,
  and publishes them at `https://league-robotics.github.io/subsystems/<name>/`.
- **The hub never writes to your repo, and you never push content to the hub.** You ping the
  hub to trigger a rebuild when content changes.
- `docs/wiki/_subsystem.yml` (the only file kept in the repo) holds subsystem metadata
  (title, blurb, order). The hub reads this via raw URL on each build.

```
your wiki ({repo}.wiki) --- docs are authored here ---> hub clones + renders + publishes
       ^ source of truth                         league-robotics.github.io

docs/wiki/_subsystem.yml --- metadata (title, blurb) ---> hub reads via raw URL
```

## What your repo needs

```
docs/wiki/
  _subsystem.yml          # subsystem metadata (title, blurb, order) — THE ONLY FILE HERE
.github/workflows/
  notify-docs-hub.yml     # pings the hub when _subsystem.yml changes
AGENTS.md                 # repo-root note so the next agent knows the wiki publishes here
```

The actual documentation lives in the **GitHub wiki** — cloneable at
`https://github.com/<owner>/<repo>.wiki.git`. Each `.md` file in the wiki is one
published page.

### `docs/wiki/_subsystem.yml`

This is the **only file** that stays in `docs/wiki/`. It holds subsystem metadata:

```yaml
name: my-subsystem        # stable key; match your registry entry
title: My Subsystem       # display name on the hub
blurb: One sentence describing this subsystem.
order: 100                # optional — lower sorts earlier on the home page
```

### Wiki pages (each `{page}.md`)

Every wiki page is normal Markdown with a front-matter header. All pages at the wiki
root are published. GitHub's auto-created `Home.md` is ignored.

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

This workflow pings the hub when `_subsystem.yml` changes. Copy it **verbatim**
(no edits needed — it figures out your repo name automatically):

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

**When wiki content changes** (new pages, edits), trigger a rebuild manually:
Go to the hub's [Actions tab](https://github.com/League-Robotics/League-Robotics.github.io/actions)
→ "Publish docs" → "Run workflow".

### `AGENTS.md` (leave yourself a map)

Copy this into the root of your repo (replace `<name>` and `<org>/<repo>`):

```markdown
# AGENTS.md — this repo publishes docs to the League Robotics hub

Documentation for this repo lives in the **GitHub wiki**:
<https://github.com/<org>/<repo>/wiki>

The League Robotics docs hub *clones the wiki* and publishes it at
<https://league-robotics.github.io/subsystems/<name>/>. The hub never writes back here —
edit wiki pages directly.

## What to do

When you learn something a future agent will need, edit or add a page in the wiki:

- Each wiki `*.md` page is one published page and needs `title:` and `blurb:` front matter.
- `docs/wiki/_subsystem.yml` (the ONLY file here) holds this subsystem's `name`/`title`/`blurb`.
  Changes to it auto-ping the hub.
- Add an `updated:` date to a page's front matter when you change it.
- After editing wiki pages, manually trigger a rebuild from the hub's Actions tab.

## How to understand what to do

The complete contract — file formats, the notify workflow, how to register — is the
authoritative spec at **<https://league-robotics.github.io/publishing/>**. Start there.
```

## Keep your wiki useful for the next agent

The wiki isn't just public docs — it's the durable memory for agents working in this repo.
Two habits keep it that way:

- **Index your knowledge base.** As soon as you have more than a handful of pages — design
  notes, decisions, open tasks, gotchas a future agent must not forget — the hub's generated
  landing page links them all. *How* you organize the pages in the wiki doesn't matter;
  that they're discoverable does.
- **Date your pages.** Set `updated:` (or `date:`) in each page's front matter — see the
  field table above.

## Authentication (one org-wide GitHub App)

The hub authenticates with a single **League Robotics Docs** GitHub App installed across
the org. Each workflow mints a short-lived, least-privilege token at run time — there are
no long-lived personal tokens.

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
```

Once merged, your wiki pages appear at
`https://league-robotics.github.io/subsystems/my-subsystem/` on the next build.

## Troubleshooting

- **My docs aren't showing up.** Confirm your repo is in `subsystems.yml`, the `branch`
  matches, `docs/wiki/_subsystem.yml` exists, and your wiki has `.md` pages.
- **A page is missing.** Check that the wiki page ends in `.md` and has valid front
  matter with `title`/`blurb`. The auto-created `Home.md` page is not published.
- **The hub didn't rebuild.** Trigger it manually from the hub's [Actions tab](https://github.com/League-Robotics/League-Robotics.github.io/actions).