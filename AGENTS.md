# AGENTS.md — listing a subsystem's docs on the League Robotics hub

This repo (`League-Robotics.github.io`) is the **docs hub**: a directory of the League
Robotics subsystems, published at <https://league-robotics.github.io/>. Each subsystem's
documentation lives in **that repo's own GitHub wiki** and is read there — the hub links
to it and holds no copy.

## If you are an agent working in a SUBSYSTEM repo

Goal: get this repo's wiki listed on the hub. Full spec (self-contained):
<https://league-robotics.github.io/publishing/>

Do exactly this:

1. Write your docs into the repo's **GitHub wiki** — a separate git repo at
   `https://github.com/<owner>/<repo>.wiki.git`. Each top-level `*.md` is one page.
   Start every page with an `# H1` title and a `> one-line blurb`; put extras in an
   HTML comment (`<!-- meta: {"order":10,"tags":[…],"updated":"YYYY-MM-DD"} -->`).
   **No YAML front matter** — the wiki renders it as visible text.
2. Make `Home.md` the index: one line per page with its blurb. It's where the hub's card
   lands. An optional `meta` comment there with `title`/`blurb`/`order` overrides the
   hub registry.
3. Add `.github/workflows/notify-docs-hub.yml` to the **code** repo — copy it verbatim
   from the spec above (or from `examples/subsystem-template/` in the hub repo). It
   triggers on `gollum` (wiki edits). No edits needed.
4. Open a PR against `League-Robotics.github.io` adding this repo to `subsystems.yml`.
5. **Leave yourself a map.** Create (or update) an `AGENTS.md` at the root of *your* repo
   so the next agent immediately knows the docs are in the wiki, how to clone and edit
   it, and that the spec at <https://league-robotics.github.io/publishing/> is
   authoritative. Copy `examples/subsystem-template/AGENTS.md` from the hub and fill in
   your repo's path.

**Do not** copy anything into the hub repo other than the `subsystems.yml` entry — and
do not keep a second copy of the docs in `docs/wiki/`. The wiki is the only copy.

### Keep the wiki useful for the next agent

- **Index your knowledge base.** `Home.md` is the index and the page everyone lands on.
  Link every page with its blurb, and list the decisions, gotchas, and open tasks a
  future agent must not forget. (How you organize it doesn't matter; that it's
  discoverable does.)
- **Stamp the date.** Set `updated` in each page's `meta` comment when you revise it.
  The hub's card shows when the wiki as a whole last changed, but only the page can say
  when *that page* was last true.

Paste-able instruction for a remote agent:

> Publish this repo's documentation to its GitHub wiki and list it on the League Robotics
> hub, following the spec at https://league-robotics.github.io/publishing/. Clone
> `https://github.com/<owner>/<repo>.wiki.git`, write one `*.md` per page — each starting
> with an `# H1` title and a `> blurb`, no YAML front matter — and make `Home.md` the
> index. Add the `notify-docs-hub.yml` workflow (triggers on `gollum`) to the code repo.
> Open a PR against League-Robotics.github.io adding this repo to `subsystems.yml`. Then
> drop an `AGENTS.md` at the repo root (template in the spec) so the next agent knows the
> docs are in the wiki. Do not copy anything into the hub repo, and don't leave a second
> copy of the docs under `docs/`.

## If you are an agent working in THIS hub repo

- Registry: [`subsystems.yml`](subsystems.yml) — the subsystems to list, and the source
  of each card's title/blurb/order (a wiki's `Home.md` `meta` comment overrides it).
- Collector: [`scripts/collect.py`](scripts/collect.py) — shallow-clones each
  `<repo>.wiki.git` to confirm it's reachable, reads the `Home.md` overrides, counts
  pages, and writes `_data/subsystems.yml`. Its output is gitignored and regenerated on
  every build. It copies no doc content.
- Build/deploy: [`.github/workflows/build-deploy.yml`](.github/workflows/build-deploy.yml).
- Architecture & rationale: [`docs/implementation-plan.md`](docs/implementation-plan.md).
