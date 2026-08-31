# CLAUDE.md

Project guidance for Claude Code. For the docs-publishing contract (how subsystem
repos get onto the hub), see [AGENTS.md](AGENTS.md) and `publishing/index.md`.

## Building locally

This is a Jekyll site whose `Gemfile.lock` is pinned to bundler 4.0.3 / Ruby 4.x.
macOS's system Ruby (2.6, bundler 1.17) can't run it and will fail with
`Could not find 'bundler' (4.0.3)`. Put Homebrew's Ruby ahead of the system one first:

```sh
export PATH="/opt/homebrew/opt/ruby@4.0/bin:$PATH"
bundle exec jekyll build      # or: bundle exec jekyll serve
```

## How a build works

The hub is a **directory**, not a mirror: every subsystem's docs live in that repo's
GitHub wiki and are read there. `scripts/collect.py` shallow-clones each
`<repo>.wiki.git` from `subsystems.yml` to confirm it's reachable, reads an optional
`<!-- meta: {...} -->` override in `Home.md`, counts pages, and writes
`_data/subsystems.yml`. Jekyll renders one page: a card grid linking straight to
`github.com/<repo>/wiki`. No doc content is ever copied into this repo.

Everything the collector writes (`_data/subsystems.yml`, `.collect-tmp/`, plus `_site/`)
is gitignored and regenerated on every build — never commit it. `subsystems/` is a
leftover from the old mirroring collector; `collect.py` deletes it on every run. The real
CI build/deploy is `.github/workflows/build-deploy.yml`; `master` is the deploy branch.
