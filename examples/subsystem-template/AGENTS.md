# AGENTS.md — this repo publishes docs to the League Robotics hub

Documentation for this repo lives under [`docs/wiki/`](docs/wiki/). Those files are the
**source of truth**; the League Robotics docs hub *pulls* them and publishes them at
<https://league-robotics.github.io/subsystems/my-subsystem/>. The hub never writes back
here — edit docs in this repo only.

> Replace `my-subsystem` above with this repo's subsystem `name` (the one in
> `docs/wiki/_subsystem.yml`).

## What to do

When you learn something a future agent will need, write it into `docs/wiki/`:

- Each `docs/wiki/*.md` is one published page and needs `title:` and `blurb:` front
  matter. Files starting with `_` are not published.
- `docs/wiki/_subsystem.yml` holds this subsystem's `name` / `title` / `blurb`.
- Keep [`docs/wiki/index.md`](docs/wiki/index.md) as the map: link the key docs and list
  open tasks / things to remember, so the next agent finds them fast.
- Add an `updated:` date to a doc's front matter when you change it.
- Changes under `docs/wiki/**` auto-ping the hub to rebuild (see
  `.github/workflows/notify-docs-hub.yml`).

## How to understand what to do

The complete contract — file formats, the notify workflow, how to register — is the
authoritative spec at **<https://league-robotics.github.io/publishing/>**. Start there if
anything here is unclear.
