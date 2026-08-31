---
layout: doc
title: List your wiki on the hub
blurb: How a subsystem repo's GitHub wiki gets listed on the League Robotics hub.
permalink: /publishing/
updated: 2026-08-31
---

This page is the complete contract for publishing a subsystem's documentation and
getting it listed on the League Robotics hub. If you are an AI agent working in a
subsystem repo, everything you need is here — no other page required.

## How the hub works

- You author docs **in your own repo's GitHub wiki**, at
  `https://github.com/<owner>/<repo>/wiki`. That wiki is the source of truth and the
  place people read the docs.
- The hub (`League-Robotics.github.io`) keeps a registry,
  [`subsystems.yml`](https://github.com/League-Robotics/League-Robotics.github.io/blob/master/subsystems.yml),
  of which repos to list.
- On each build the hub checks every registered wiki is reachable, counts its pages,
  and publishes a **directory card** at <https://league-robotics.github.io/> that links
  straight to your wiki. **The hub does not copy your pages** — there is exactly one
  copy of every doc, and it is the one in your wiki.
- **The hub never writes to your repo, and you never push content to the hub.** You
  only send a lightweight "I changed" ping so the card's page count and date refresh.

```
your repo's wiki  --- ping ("docs-updated") --->  hub lists + links
   ^ source of truth, and where docs are read      league-robotics.github.io
```

> **Moving from `docs/wiki/`?** The hub used to mirror a `docs/wiki/` directory into
> `league-robotics.github.io/subsystems/<name>/` and generate the index page for you.
> It no longer does either. To migrate:
>
> 1. Move `docs/wiki/*.md` into the repo's GitHub wiki, converting each file's YAML front
>    matter into an `# H1` + `> blurb` + `meta` comment (see below).
> 2. Fold `_subsystem.yml`'s `title`/`blurb`/`order` into a `meta` comment on `Home.md`,
>    then delete the file — the hub no longer reads it.
> 3. **Write `Home.md` yourself.** The hub used to generate your index page; now `Home.md`
>    *is* the index and nothing maintains it but you. If yours still says
>    "each page is published on the hub", that is left over from the old mirror and is no
>    longer true — pages are published *in this wiki*.
> 4. Replace the old notify workflow's `push` / `paths: docs/wiki/**` trigger with
>    `on: gollum` (full file below), since wiki edits are not pushes to your repo.
> 5. Delete `docs/wiki/`, so there is never a second copy to drift.
>
> Old `/subsystems/<name>/…` hub URLs are gone; anything pointing at them should point at
> the wiki instead.

## What the hub actually reads

Very little — which is the point. From your wiki the hub takes only:

1. **That it exists and is reachable**, plus how many `*.md` pages it has and the date of
   its last commit. That's the "10 pages · updated Aug 31, 2026" line on your card.
2. **`Home.md`'s `meta` comment**, if it has one — `title`, `blurb`, `order` for the card.

That's the whole contract. Everything else below — page titles, blurbs, `order`, `tags` —
is **convention for humans and agents, not hub input**. Nothing is validated, nothing
breaks if you deviate, and no page is rejected. Follow the conventions anyway: the next
agent to open your wiki is the one who benefits, and they are what make `Home.md`
maintainable.

## Editing your wiki as an agent

A GitHub wiki is an ordinary git repo, so you can work on it from the command line:

```sh
git clone https://github.com/<owner>/<repo>.wiki.git wiki
cd wiki
# add or edit *.md files
git add -A && git commit -m "docs: …" && git push
```

Every `<page>.md` at the top level becomes `https://github.com/<owner>/<repo>/wiki/<page>`.
The wiki is created the first time a page exists — if the clone fails with "repository not
found", open the repo's **Wiki** tab and save any first page, then clone again.

## What your wiki needs

```
Home.md                 # the landing page: an index linking every other page
overview.md             # one or more pages; each *.md is one wiki page
protocol.md
...
```

And in the repo itself:

```
.github/workflows/
  notify-docs-hub.yml   # pings the hub when the wiki changes
AGENTS.md               # repo-root note so the next agent knows where the docs are
```

### Each wiki page

A wiki page is normal GitHub-flavored Markdown. **Do not use YAML front matter** —
GitHub renders wiki pages verbatim, so front matter shows up as visible junk at the
top of the page. Use this shape instead:

```markdown
# Deploying ROS 2 with Ansible

> How to provision a ROS 2 fleet across Pi / VM / Docker hosts.

<!-- meta: {"order":10,"tags":["ros","ansible"],"updated":"2026-08-31"} -->

Body markdown… (your real documentation)
```

| Part | Required | Meaning |
|------|----------|---------|
| `# Title` (H1) | yes | The page title. |
| `> blurb` | yes | One-line summary; reused as the page's line in `Home.md`. |
| `meta` comment | no | Machine-readable extras. Invisible when rendered. |

Recognized `meta` keys: `order` (where the page belongs in `Home.md`, default 100),
`tags` (free-form list), `updated` (`YYYY-MM-DD`, when you last revised the page). The
hub reads none of these — they are for whoever maintains `Home.md`, which since the hub
stopped generating index pages is **you**.

Filenames are the URL, so keep them lowercase and hyphenated (`fleet-daemon.md` →
`…/wiki/fleet-daemon`). Names starting with `_` are GitHub's own chrome —
`_Sidebar.md` and `_Footer.md` render around every page — and are not content.

### `Home.md`

`Home.md` is what the hub's card links to, so it is the first thing anyone sees. Make
it an index: the page title, and one line per page with its blurb, sorted by `order`.

```markdown
# ros-deploy

> Ansible-based deployment of ROS 2 across the robot fleet.

<!-- meta: {"title":"ROS Deploy","blurb":"Ansible-based deployment of ROS 2 across the robot fleet — physical robots, Raspberry Pis, VMs, and Docker.","order":20} -->

- [ROS Deploy Overview](https://github.com/League-Robotics/ros-deploy/wiki/overview) — What the deployment system is and how to use it.
- [Setting Up a New Node](https://github.com/League-Robotics/ros-deploy/wiki/new-node) — Bootstrap and deploy ROS 2 to a new robot, Pi, or VM.
```

The `meta` comment in `Home.md` is special: its `title`, `blurb`, and `order` override
whatever the hub registry says, so **you can rename your subsystem or rewrite its
one-liner without opening a PR against the hub**. Omit it and the registry values are
used.

Cross-link pages with `[[Page Name]]` or with full `…/wiki/<page>` URLs. Relative
`.md` links do *not* work in a GitHub wiki — its pages have no `.md` extension.

### `.github/workflows/notify-docs-hub.yml`

Copy this **verbatim** into your repo (no edits needed). The `gollum` event fires
whenever a wiki page is created or updated:

```yaml
name: Notify docs hub
on:
  gollum:
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

> The workflow file lives in the **code** repo, not the wiki, and `gollum` runs it from
> your default branch. Either way your docs are live the moment you push to the wiki —
> people read them there. The ping only refreshes the card's page count and "updated"
> date. **There is no cron on the hub**, so if you skip this workflow those two numbers
> stay stale until something else triggers a hub build.

### `AGENTS.md` (leave yourself a map)

Drop an `AGENTS.md` at the **root of your repo**. Its job is to tell the next agent —
who may arrive months later with no context — that this repo's docs live in its wiki,
how to edit them, and where the authoritative instructions are (this page). Copy this
and replace `<owner>/<repo>`:

```markdown
# AGENTS.md — this repo's documentation lives in its GitHub wiki

Documentation for this repo is published in its **GitHub wiki**:
<https://github.com/<owner>/<repo>/wiki>. That wiki is the source of truth — it is
where the docs are written *and* where they are read. The League Robotics docs hub
(<https://league-robotics.github.io/>) links to it; the hub holds no copy and never
writes back here.

## What to do

When you learn something a future agent will need, write it into the wiki:

    git clone https://github.com/<owner>/<repo>.wiki.git /tmp/wiki

- Each top-level `*.md` is one wiki page. Start it with an `# H1` title and a
  `> one-line blurb`. **No YAML front matter** — the wiki renders it as visible text.
- Machine-readable extras go in an HTML comment:
  `<!-- meta: {"order":10,"tags":["…"],"updated":"YYYY-MM-DD"} -->`.
- Keep `Home.md` as the index: one line per page with its blurb, plus open tasks and
  things to remember, so the next agent finds them fast.
- Bump `updated` whenever you revise a page.
- Wiki edits auto-ping the hub to refresh its listing (see
  `.github/workflows/notify-docs-hub.yml`).

## How to understand what to do

The complete contract — page format, the notify workflow, how to register — is the
authoritative spec at **<https://league-robotics.github.io/publishing/>**. Start there.
```

## Keep your wiki useful for the next agent

The wiki isn't just public docs — it's the durable memory for agents working in this
repo. Two habits keep it that way:

- **Index your knowledge base.** `Home.md` is the index, and it is where every visitor
  lands. Keep it current: link every page with its blurb, and list the open tasks,
  decisions, and gotchas a future agent must not forget. *How* you organize it doesn't
  matter; that it's discoverable does.
- **Date your pages.** Set `updated` in each page's `meta` comment when you revise it.
  The hub shows when the wiki as a whole last changed, but only the page itself can say
  when *that page* was last true.

## Authentication (one org-wide GitHub App)

Both the hub (reading wikis) and your repo (pinging the hub) authenticate with a single
**League Robotics Docs** GitHub App installed across the org. Each workflow mints a
short-lived, least-privilege token at run time — there are no long-lived personal tokens.
A wiki inherits its repo's visibility, so a private repo's wiki needs the same token the
hub already uses.

An org admin sets this up **once** (see the hub README). After that, the org-level
`vars.DOCS_HUB_APP_ID` and `secrets.DOCS_HUB_APP_PRIVATE_KEY` referenced above are
already available to your repo — you don't create any secrets yourself.

## Get registered

Open a pull request against the hub adding your repo to
[`subsystems.yml`](https://github.com/League-Robotics/League-Robotics.github.io/blob/master/subsystems.yml):

```yaml
subsystems:
  - name: my-subsystem
    repo: League-Robotics/my-repo
    title: My Subsystem        # optional — display name on the card
    blurb: One sentence describing this subsystem.
    order: 100                 # optional — lower sorts earlier
```

Once merged, your card appears on <https://league-robotics.github.io/> on the next
build, linking to your wiki.

## Troubleshooting

- **My subsystem isn't listed.** Confirm your repo is in `subsystems.yml` and that the
  wiki has at least one page — a repo with no wiki at all is skipped (the hub build logs
  a warning but still deploys everyone else).
- **The card shows the wrong name or blurb.** Either fix the registry entry, or add a
  `meta` comment to `Home.md` with `title`/`blurb` — the wiki wins.
- **The page count or date is stale.** The card refreshes on the next hub build. Run
  your notify workflow manually from the Actions tab (`workflow_dispatch`), or an admin
  can re-run the hub's build.
- **Front matter is showing at the top of my page.** GitHub wikis don't support it. Turn
  it into an `# H1` + `> blurb` + `meta` comment as shown above.
