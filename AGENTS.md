# AGENTS.md — publishing docs to the League Robotics hub

This repo (`League-Robotics.github.io`) is the **docs hub**. It pulls documentation from
each subsystem repo and publishes it at <https://league-robotics.github.io/>.

## If you are an agent working in a SUBSYSTEM repo

Goal: get this repo's docs onto the hub. Full spec (self-contained):
<https://league-robotics.github.io/publishing/>

Do exactly this:

1. Create `docs/wiki/_subsystem.yml` with `name`, `title`, `blurb`.
2. Create one or more `docs/wiki/<name>.md` files, each with front matter `title:` and
   `blurb:` followed by the documentation body. Files starting with `_` are ignored.
3. Add `.github/workflows/notify-docs-hub.yml` — copy it verbatim from the spec above
   (or from `examples/subsystem-template/` in the hub repo). No edits needed.
4. Open a PR against `League-Robotics.github.io` adding this repo to `subsystems.yml`.

**Do not** copy anything into the hub repo other than the `subsystems.yml` entry — the
hub pulls from your repo. Your `docs/wiki/` is the source of truth.

Paste-able instruction for a remote agent:

> Publish this repo's documentation to the League Robotics hub by following the spec at
> https://league-robotics.github.io/publishing/. Create `docs/wiki/` with a `_subsystem.yml`
> (name, title, blurb) and one or more `*.md` docs that each have `title:` and `blurb:` front
> matter, then add the `notify-docs-hub.yml` workflow shown there. Open a PR against
> League-Robotics.github.io adding this repo to `subsystems.yml`. Do not copy anything into
> the hub repo — it pulls from here.

## If you are an agent working in THIS hub repo

- Registry: [`subsystems.yml`](subsystems.yml) — the list of repos to pull.
- Collector: [`scripts/collect.py`](scripts/collect.py) — clones each repo, mirrors
  `docs/wiki/` into `subsystems/<name>/`, writes `_data/subsystems.yml`. Its output is
  gitignored and regenerated on every build.
- Build/deploy: [`.github/workflows/build-deploy.yml`](.github/workflows/build-deploy.yml).
- Architecture & rationale: [`docs/implementation-plan.md`](docs/implementation-plan.md).
