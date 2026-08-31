# League-Robotics.github.io

The documentation **hub** for the League Robotics program, published at
<https://league-robotics.github.io/>.

Each subsystem authors its docs in **its own repo's GitHub wiki**, and that wiki is where
the docs are read. This hub keeps a registry of those repos
([`subsystems.yml`](subsystems.yml)), checks each wiki on every build, and publishes a
**directory** — one card per subsystem, linking straight to its wiki. The hub keeps no copy
of any doc. Subsystems never push content here; they only ping the hub to refresh the
listing.

- **Maintain a subsystem repo?** See <https://league-robotics.github.io/publishing/>
  (or [`AGENTS.md`](AGENTS.md)) for the wiki page format and the workflow to add.
- **Architecture & design notes:** [`docs/implementation-plan.md`](docs/implementation-plan.md).

## Repo layout

```
subsystems.yml                 # registry: which wikis to list, and their card text
scripts/collect.py             # checks each repo's wiki → _data/subsystems.yml
_config.yml, Gemfile           # Jekyll site config
index.html, _layouts/, assets/ # site templates and styling
publishing/index.md            # the /publishing/ guide for subsystem authors
examples/subsystem-template/   # copy-paste files for a new subsystem repo
.github/workflows/build-deploy.yml  # check → jekyll build → deploy to Pages
```

Generated content (`_data/subsystems.yml`) is produced by the collector at build time and is
**gitignored** — never committed. `subsystems/` is a leftover from the old mirroring
collector; `collect.py` deletes it on every run.

## Add a subsystem (maintainer)

Append an entry to [`subsystems.yml`](subsystems.yml) and merge:

```yaml
subsystems:
  - name: ros-deploy
    repo: League-Robotics/ros-deploy
    title: ROS Deploy       # optional — display name on the card
    blurb: One sentence describing this subsystem.
    order: 20               # optional — lower sorts earlier
```

The repo's wiki (`https://github.com/<repo>/wiki`) is the docs source; there is no branch
or path to configure. A wiki can override `title` / `blurb` / `order` itself with a
`<!-- meta: {...} -->` comment in its `Home.md`.

## One-time setup: enable GitHub Pages

The site is published by the `build-deploy.yml` workflow (not the legacy "deploy from a
branch" mode), so Pages must be told to use Actions as its source:

1. Repo → **Settings → Pages**.
2. Under **Build and deployment → Source**, choose **GitHub Actions**. (There is no
   branch/folder to pick — the workflow uploads the built site directly.)
3. Make sure the repo is **public** (org `*.github.io` sites need a public repo unless your
   org plan allows private Pages).
4. Trigger the first deploy: push to the default branch, or run **Actions → Build & deploy
   docs hub → Run workflow** (`workflow_dispatch`).
5. The first run auto-creates a `github-pages` environment and publishes to
   `https://league-robotics.github.io/`. The deployed URL also appears on the workflow run.

> This must be set to **GitHub Actions** before the first run — otherwise the `deploy`
> job fails with a Pages-not-enabled error. The workflow already has the required
> `pages: write` and `id-token: write` permissions.

> **Custom domain (optional):** set it under Settings → Pages → Custom domain, and add a
> `CNAME` file at the repo root. Not needed for the default `league-robotics.github.io`.

## One-time setup: the GitHub App

Authentication for both directions (the hub pulling repos, and subsystems pinging the hub)
uses a single org-wide GitHub App, so there are no long-lived personal access tokens.

1. **Create the app** (org → Settings → Developer settings → GitHub Apps → New).
   - Repository permissions: **Contents: Read and write**, **Metadata: Read-only**.
     (Read is needed to clone subsystem wikis — a wiki inherits its repo's visibility;
     write is needed so a subsystem can trigger this repo's `repository_dispatch`.)
   - Subscribe to events: none required.
2. **Install** it on the League-Robotics org, **All repositories**.
3. **Generate a private key** and note the **App ID**.
4. Add **org-level** values (Org → Settings → Secrets and variables → Actions):
   - Variable `DOCS_HUB_APP_ID` = the App ID.
   - Secret `DOCS_HUB_APP_PRIVATE_KEY` = the private key (full `.pem` contents).
   Make both available to all repositories (or at least the hub + subsystem repos).

The workflows mint short-lived, least-privilege installation tokens from this app at run
time via [`actions/create-github-app-token`](https://github.com/actions/create-github-app-token).

> If every subsystem repo is **public**, the hub can clone their wikis anonymously: you may drop the
> app-token step from `build-deploy.yml`. The app is still required for the subsystem-side
> notify workflow (cross-repo `repository_dispatch` needs an authenticated token).

## Local development

```bash
pip install -r scripts/requirements.txt
DOCS_PULL_TOKEN= python scripts/collect.py   # checks public wikis in subsystems.yml
bundle install
bundle exec jekyll serve                      # http://localhost:4000
```

Set `DOCS_PULL_TOKEN` to a token with read access if any registered repo is private.

## How a build works

1. Triggered by a subsystem's `repository_dispatch` (`docs-updated`), a manual run, or a
   push to this repo.
2. `scripts/collect.py` shallow-clones each registered repo's wiki, confirms it is
   reachable, reads any `Home.md` overrides, counts its pages, and writes
   `_data/subsystems.yml`.
3. Jekyll builds the site; `actions/deploy-pages` publishes it.
