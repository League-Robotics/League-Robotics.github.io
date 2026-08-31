# Overview: League-Robotics docs hub

> **Current architecture.** The hub is a **directory of GitHub wikis**. It supersedes both
> the original push-model draft and the central-pull *full-mirror* design described in
> [implementation-plan.md](implementation-plan.md), which is kept only as history. The
> author-facing contract is published at <https://league-robotics.github.io/publishing/>.

## What this is

The `League-Robotics` org has many subsystem repos (`ros-deploy`, `aprilcam`, `mbdeploy`, …)
with no single place to discover them. This repo, `League-Robotics.github.io`, is a small
Jekyll site served at <https://league-robotics.github.io/> that lists them all and links to
each one's documentation.

## How it works (directory of wikis)

- Authoring **and reading** happen in each subsystem repo's **GitHub wiki**
  (`https://github.com/<owner>/<repo>/wiki`). There is exactly one copy of every doc.
- The hub keeps a hand-edited registry, [`../subsystems.yml`](../subsystems.yml), of which
  repos to list, along with each card's `title` / `blurb` / `order`.
- On each build, `scripts/collect.py` shallow-clones every registered `<repo>.wiki.git`,
  confirms it exists and is reachable, reads an optional `<!-- meta: {...} -->` override in
  `Home.md`, counts its pages, and records the wiki's last-edit date. The result is
  `_data/subsystems.yml`.
- Jekyll renders two pages: the directory (`/`) and the publishing contract
  (`/publishing/`). No doc content is copied into this repo.
- Subsystems never push content to the hub. Their `gollum`-triggered workflow sends a
  `repository_dispatch` ping (`docs-updated`) so the card's page count and date refresh.

```
subsystem repo's wiki  --- ping --->  hub: check every wiki → render directory → deploy Pages
   ^ source of truth, and where              league-robotics.github.io
     the docs are actually read
```

## Key decisions

- **Link, don't mirror** — one copy of each doc, in the wiki. The hub can't go stale, wiki
  search and page history work normally, and agents can edit docs with a plain `git push`
  to `<repo>.wiki.git`.
- **No front matter in wiki pages** — GitHub renders a wiki page verbatim, so YAML front
  matter would be visible junk. Metadata rides in an HTML comment:
  `<!-- meta: {"order":10,"tags":[…],"updated":"YYYY-MM-DD"} -->`.
- **Registry owns card text, wiki can override** — `subsystems.yml` supplies
  `title`/`blurb`/`order`; a `meta` comment in `Home.md` wins, so a subsystem can rename
  itself without a hub PR.
- **Dispatch-only** — rebuilds on a subsystem ping, manual run, or push to the hub. No cron.
- **Hand-edited `subsystems.yml`** — onboarding a repo is a PR adding one entry.
- **Python collector** — `scripts/collect.py` (PyYAML only).
- **One org-wide GitHub App** for auth (no long-lived PATs); workflows mint short-lived
  tokens. A wiki inherits its repo's visibility, so a private repo's wiki needs the token.

## Consequences of the switch away from mirroring

- `/subsystems/<name>/` and `/subsystems/<name>/<slug>/` URLs **no longer exist**. Anything
  linking to them should point at the wiki instead.
- The collector no longer parses front matter, rewrites links, or writes page bodies —
  `python-frontmatter` is gone from `scripts/requirements.txt`, and `_layouts/subsystem.html`
  was deleted.
- `docs/wiki/` in a subsystem repo is obsolete. Move it into the wiki and delete it, so
  there is never a second copy to drift.
