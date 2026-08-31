# AGENTS.md — this repo's documentation lives in its GitHub wiki

Documentation for this repo is published in its **GitHub wiki**:
<https://github.com/OWNER/REPO/wiki>. That wiki is the source of truth — it is where the
docs are written *and* where they are read. The League Robotics docs hub
(<https://league-robotics.github.io/>) links to it; the hub holds no copy and never
writes back here.

> Replace `OWNER/REPO` above with this repo's path on github.com.

## What to do

When you learn something a future agent will need, write it into the wiki. The wiki is
an ordinary git repo:

```sh
git clone https://github.com/OWNER/REPO.wiki.git /tmp/wiki
cd /tmp/wiki
# edit *.md
git add -A && git commit -m "docs: …" && git push
```

- Each top-level `*.md` is one wiki page, named after the file (`fleet-daemon.md` →
  `…/wiki/fleet-daemon`). Start it with an `# H1` title and a `> one-line blurb`.
- **No YAML front matter.** GitHub renders wiki pages verbatim, so front matter shows up
  as visible junk. Machine-readable extras go in an HTML comment instead:
  `<!-- meta: {"order":10,"tags":["…"],"updated":"YYYY-MM-DD"} -->`.
- Keep `Home.md` as the index: one line per page with its blurb, plus open tasks and
  things to remember, so the next agent finds them fast. It is where the hub's card
  lands, and **nothing generates it — you maintain it by hand.**
- Bump `updated` whenever you revise a page.
- Wiki edits auto-ping the hub to refresh its listing (see
  [`.github/workflows/notify-docs-hub.yml`](.github/workflows/notify-docs-hub.yml)).

## How to understand what to do

The complete contract — page format, the notify workflow, how to register — is the
authoritative spec at **<https://league-robotics.github.io/publishing/>**. Start there if
anything here is unclear.
