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

`scripts/collect.py` clones every repo in `subsystems.yml`, mirrors each repo's
`docs/wiki/` into `subsystems/<name>/`, and writes `_data/subsystems.yml`. Jekyll then
renders the site. Everything the collector writes (`subsystems/`, `_data/subsystems.yml`,
`_site/`) is gitignored and regenerated on every build — never commit it. The real CI
build/deploy is `.github/workflows/build-deploy.yml`; `master` is the deploy branch.
