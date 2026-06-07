#!/usr/bin/env python3
"""Pull each registered subsystem's docs/wiki/ and stage it for the Jekyll build.

The hub owns the registry (subsystems.yml). For every entry we shallow-clone the
repo, read its docs/wiki/_subsystem.yml plus the front matter of each docs/wiki/*.md,
mirror the doc bodies into subsystems/<name>/ (with Jekyll front matter injected),
and write _data/subsystems.yml for the home page.

Everything this script writes is gitignored — it is regenerated on every build.

A subsystem that is missing or malformed is logged and skipped; one bad repo must
not break the whole hub. The script exits non-zero only on an unrecoverable error
(e.g. it cannot read subsystems.yml itself).

Auth: set DOCS_PULL_TOKEN to a token with read access to the subsystem repos
(needed only for private repos). It works with a PAT or a GitHub App installation
token interchangeably. Public repos clone anonymously when the var is empty.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import frontmatter
import yaml

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "subsystems.yml"
TMP = ROOT / ".collect-tmp"
OUT_DIR = ROOT / "subsystems"
DATA_DIR = ROOT / "_data"
DATA_FILE = DATA_DIR / "subsystems.yml"

DEFAULT_BRANCH = "main"
DEFAULT_DOCS_PATH = "docs/wiki"


def log(msg: str) -> None:
    print(f"[collect] {msg}", flush=True)


def warn(msg: str) -> None:
    print(f"[collect] WARNING: {msg}", file=sys.stderr, flush=True)


def clone(repo: str, branch: str, dest: Path, token: str) -> None:
    """Shallow-clone owner/repo@branch into dest."""
    if token:
        url = f"https://x-access-token:{token}@github.com/{repo}.git"
    else:
        url = f"https://github.com/{repo}.git"
    # Never echo the token; pass the URL as a single arg, not via the shell.
    subprocess.run(
        ["git", "clone", "--depth", "1", "--branch", branch, url, str(dest)],
        check=True,
        capture_output=True,
        text=True,
    )


def slugify(value: str) -> str:
    out = "".join(c if c.isalnum() else "-" for c in value.lower())
    while "--" in out:
        out = out.replace("--", "-")
    return out.strip("-") or "doc"


def write_with_front_matter(path: Path, meta: dict, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fm = yaml.safe_dump(meta, sort_keys=False, allow_unicode=True).strip()
    path.write_text(f"---\n{fm}\n---\n{body}", encoding="utf-8")


def collect_subsystem(entry: dict, token: str) -> dict | None:
    """Clone one subsystem, mirror its docs, return its home-page summary."""
    name = entry.get("name")
    repo = entry.get("repo")
    if not name or not repo:
        warn(f"registry entry missing name/repo: {entry!r} — skipping")
        return None

    branch = entry.get("branch", DEFAULT_BRANCH)
    docs_path = entry.get("docs_path", DEFAULT_DOCS_PATH)
    repo_url = f"https://github.com/{repo}"
    clone_dir = TMP / name

    log(f"{name}: cloning {repo}@{branch}")
    try:
        clone(repo, branch, clone_dir, token)
    except subprocess.CalledProcessError as e:
        warn(f"{name}: clone failed ({e.stderr.strip().splitlines()[-1:] or e}) — skipping")
        return None

    wiki = clone_dir / docs_path
    if not wiki.is_dir():
        warn(f"{name}: no {docs_path}/ in {repo} — skipping")
        return None

    # Subsystem-level metadata (display title/blurb/order). The registry owns
    # *where* the repo is; _subsystem.yml owns *what it's called*.
    meta_file = wiki / "_subsystem.yml"
    sub_meta = {}
    if meta_file.is_file():
        try:
            sub_meta = yaml.safe_load(meta_file.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as e:
            warn(f"{name}: bad _subsystem.yml ({e}) — using defaults")
    else:
        warn(f"{name}: no _subsystem.yml — using defaults")

    title = sub_meta.get("title", name)
    blurb = sub_meta.get("blurb", "")
    order = sub_meta.get("order", 100)

    # Collect docs.
    docs = []
    for md in sorted(wiki.glob("*.md")):
        if md.name.startswith("_"):
            continue
        try:
            post = frontmatter.load(md)
        except Exception as e:  # noqa: BLE001 - frontmatter raises various types
            warn(f"{name}/{md.name}: unreadable front matter ({e}) — skipping doc")
            continue

        doc_title = post.get("title") or md.stem
        doc_blurb = post.get("blurb", "")
        doc_order = post.get("order", 100)
        slug = slugify(str(post.get("slug") or md.stem))
        url = f"/subsystems/{name}/{slug}/"
        source_url = f"{repo_url}/blob/{branch}/{docs_path}/{md.name}"

        write_with_front_matter(
            OUT_DIR / name / f"{slug}.md",
            {
                "layout": "doc",
                "title": doc_title,
                "blurb": doc_blurb,
                "subsystem": name,
                "permalink": url,
                "source_url": source_url,
                "tags": post.get("tags", []),
            },
            post.content,
        )
        docs.append(
            {
                "title": doc_title,
                "blurb": doc_blurb,
                "order": doc_order,
                "url": url,
                "source_url": source_url,
            }
        )

    docs.sort(key=lambda d: (d["order"], d["title"].lower()))
    log(f"{name}: {len(docs)} doc(s)")

    # Subsystem index page.
    write_with_front_matter(
        OUT_DIR / name / "index.md",
        {
            "layout": "subsystem",
            "permalink": f"/subsystems/{name}/",
            "name": name,
            "title": title,
            "blurb": blurb,
            "repo_url": repo_url,
            "docs": docs,
        },
        "",
    )

    return {"name": name, "title": title, "blurb": blurb, "order": order, "url": f"/subsystems/{name}/"}


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

    # Fresh start so removed/renamed subsystems don't linger.
    for d in (TMP, OUT_DIR):
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

    log(f"published {len(summaries)} subsystem(s) of {len(entries)} registered")
    return 0


if __name__ == "__main__":
    sys.exit(main())
