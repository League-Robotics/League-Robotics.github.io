#!/usr/bin/env python3
"""Verify each registered subsystem's GitHub wiki and write the hub's directory data.

Documentation is published in each subsystem repo's **GitHub wiki** and is read
there. The hub no longer copies doc bodies — it is a directory. For every entry in
subsystems.yml this script shallow-clones `<repo>.wiki.git` to confirm the wiki
exists and is reachable, reads an optional `<!-- meta: {...} -->` block in `Home.md`
for display metadata, counts the pages, and notes when the wiki last changed. The
result is `_data/subsystems.yml`, which `_layouts/home.html` renders as cards
linking straight to `https://github.com/<owner>/<repo>/wiki`.

Display title/blurb/order come from the registry entry; a `Home.md` meta block
overrides them, so a subsystem can rename itself without a hub PR.

Everything this script writes is gitignored — it is regenerated on every build.

A subsystem whose wiki is missing or unreachable is logged and skipped; one bad
repo must not break the whole hub. The script exits non-zero only on an
unrecoverable error (e.g. it cannot read subsystems.yml itself).

Auth: set DOCS_PULL_TOKEN to a token with read access to the subsystem repos
(needed only for private repos — a repo's wiki inherits its visibility). It works
with a PAT or a GitHub App installation token interchangeably. Public repos clone
anonymously when the var is empty.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent

REGISTRY = ROOT / "subsystems.yml"
TMP = ROOT / ".collect-tmp"
DATA_DIR = ROOT / "_data"
DATA_FILE = DATA_DIR / "subsystems.yml"
#: Written by the old mirror-the-docs collector. Removed on every run so a stale
#: copy in someone's working tree never gets published.
LEGACY_MIRROR = ROOT / "subsystems"

#: `<!-- meta: {...} -->` — the wiki's stand-in for front matter. GitHub renders a
#: wiki page verbatim, so YAML front matter would show up as text; metadata rides
#: in an HTML comment instead. Subsystem pages already use this for order/tags.
META = re.compile(r"<!--\s*meta:\s*(?P<json>\{.*?\})\s*-->", re.DOTALL)

#: The wiki's landing page. GitHub always names it this, and it is the page a
#: card's link lands on.
HOME_PAGE = "Home.md"
DEFAULT_ORDER = 100
#: Metadata a Home.md may override. Anything else in its meta block is ignored.
OVERRIDABLE = ("title", "blurb", "order")


def log(msg: str) -> None:
    print(f"[collect] {msg}", flush=True)


def warn(msg: str) -> None:
    print(f"[collect] WARNING: {msg}", file=sys.stderr, flush=True)


def clone_wiki(repo: str, dest: Path, token: str) -> None:
    """Shallow-clone owner/repo's wiki into dest.

    A GitHub wiki is its own git repo at `<repo>.wiki.git`, with its own default
    branch — so, unlike the code repo, we never pin a branch here.
    """
    if token:
        url = f"https://x-access-token:{token}@github.com/{repo}.wiki.git"
    else:
        url = f"https://github.com/{repo}.wiki.git"
    # Never echo the token; pass the URL as a single arg, not via the shell.
    subprocess.run(
        ["git", "clone", "--depth", "1", url, str(dest)],
        check=True,
        capture_output=True,
        text=True,
    )


def home_meta(wiki: Path, name: str) -> dict:
    """Read Home.md's `<!-- meta: {...} -->` overrides, if it has any."""
    home = wiki / HOME_PAGE
    if not home.is_file():
        return {}
    match = META.search(home.read_text(encoding="utf-8"))
    if not match:
        return {}
    try:
        meta = json.loads(match["json"])
    except json.JSONDecodeError as e:
        warn(f"{name}: bad meta block in {HOME_PAGE} ({e}) — using registry values")
        return {}
    if not isinstance(meta, dict):
        warn(f"{name}: meta block in {HOME_PAGE} is not an object — ignoring")
        return {}
    return {k: v for k, v in meta.items() if k in OVERRIDABLE}


def page_count(wiki: Path) -> int:
    """Published pages in the wiki: every *.md except Home and GitHub's own
    `_Sidebar` / `_Footer` chrome."""
    return sum(
        1
        for md in wiki.glob("*.md")
        if md.name != HOME_PAGE and not md.name.startswith("_")
    )


def last_changed(wiki: Path) -> str:
    """Date of the wiki's most recent edit, as YYYY-MM-DD ("" if unavailable)."""
    result = subprocess.run(
        ["git", "-C", str(wiki), "log", "-1", "--format=%cs"],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def collect_subsystem(entry: dict, token: str) -> dict | None:
    """Check one subsystem's wiki and return its directory-card summary."""
    name = entry.get("name")
    repo = entry.get("repo")
    if not name or not repo:
        warn(f"registry entry missing name/repo: {entry!r} — skipping")
        return None

    clone_dir = TMP / name
    log(f"{name}: checking wiki for {repo}")
    try:
        clone_wiki(repo, clone_dir, token)
    except subprocess.CalledProcessError as e:
        detail = (e.stderr or "").strip().splitlines()[-1:] or [str(e)]
        warn(f"{name}: wiki unreachable ({detail[0]}) — skipping. "
             f"Create the first page at https://github.com/{repo}/wiki")
        return None

    pages = page_count(clone_dir)
    if not (clone_dir / HOME_PAGE).is_file():
        warn(f"{name}: wiki has no {HOME_PAGE} — the hub link will land on an empty page")
    if pages == 0:
        warn(f"{name}: wiki has no pages besides {HOME_PAGE}")

    summary = {
        "name": name,
        "title": entry.get("title") or name,
        "blurb": entry.get("blurb", ""),
        "order": entry.get("order", DEFAULT_ORDER),
        "wiki_url": f"https://github.com/{repo}/wiki",
        "repo_url": f"https://github.com/{repo}",
        "pages": pages,
    }
    summary.update(home_meta(clone_dir, name))

    updated = last_changed(clone_dir)
    if updated:
        summary["updated"] = updated

    log(f"{name}: {pages} page(s), last edited {updated or 'unknown'}")
    return summary


def main() -> int:
    if not REGISTRY.is_file():
        warn(f"registry not found: {REGISTRY}")
        return 1
    try:
        registry = yaml.safe_load(REGISTRY.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        warn(f"cannot parse {REGISTRY.name}: {e}")
        return 1

    entries = registry.get("subsystems") or []
    token = os.environ.get("DOCS_PULL_TOKEN", "").strip()
    if not token:
        log("DOCS_PULL_TOKEN not set — cloning anonymously (public repos only)")

    # Fresh start so removed subsystems, and the old mirrored docs, don't linger.
    for d in (TMP, LEGACY_MIRROR):
        if d.exists():
            shutil.rmtree(d)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    summaries = []
    for entry in entries:
        summary = collect_subsystem(entry, token)
        if summary:
            summaries.append(summary)

    summaries.sort(key=lambda s: (s["order"], s["title"].lower()))
    DATA_FILE.write_text(
        yaml.safe_dump(summaries, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )

    if TMP.exists():
        shutil.rmtree(TMP)

    log(f"listed {len(summaries)} subsystem(s) of {len(entries)} registered")
    return 0


if __name__ == "__main__":
    sys.exit(main())
