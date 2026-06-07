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
import posixpath
import re
import shutil
import subprocess
import sys
from pathlib import Path

import frontmatter
import yaml

# Matches inline link/image targets — `](target)` or `](target "title")` — and
# reference-style definitions — `[label]: target`. Group "t" is the target.
_INLINE_LINK = re.compile(r"(?P<pre>\]\()(?P<t>[^)\s]+)(?P<post>(?:\s+\"[^\"]*\")?\))")
_REF_LINK = re.compile(r"(?P<pre>^[ \t]*\[[^\]]+\]:[ \t]*)(?P<t>\S+)", re.MULTILINE)

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


def rewrite_links(body: str, slug_by_file: dict, name: str, repo_url: str,
                  branch: str, docs_path: str) -> str:
    """Fix relative *.md links so they resolve on the hub.

    Authors cross-link docs with repo-relative paths (e.g. `](administration.md)`).
    Under our directory-style permalinks those 404. A link to another doc in the
    same wiki becomes its hub permalink; any other relative `.md` link becomes a
    GitHub source URL so it still resolves. Absolute URLs and anchors are left alone.
    """

    def resolve(target: str) -> str:
        if not target or target[0] in "#?" or "://" in target or target.startswith(("//", "mailto:")):
            return target
        path, sep, frag = target.partition("#")
        if not path.lower().endswith(".md"):
            return target
        sibling = slug_by_file.get(posixpath.basename(path))
        if sibling is not None and "/" not in path.strip("./"):
            return f"/subsystems/{name}/{sibling}/" + (sep + frag if sep else "")
        # Relative .md outside the wiki: point at the source repo, resolved
        # against the doc's directory (docs_path).
        resolved = posixpath.normpath(posixpath.join(docs_path, path))
        return f"{repo_url}/blob/{branch}/{resolved}" + (sep + frag if sep else "")

    body = _INLINE_LINK.sub(lambda m: m["pre"] + resolve(m["t"]) + m["post"], body)
    body = _REF_LINK.sub(lambda m: m["pre"] + resolve(m["t"]), body)
    return body


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

    # Pass 1: parse every doc and compute its slug, so we can resolve
    # cross-doc links before writing any bodies.
    parsed = []
    for md in sorted(wiki.glob("*.md")):
        if md.name.startswith("_"):
            continue
        try:
            post = frontmatter.load(md)
        except Exception as e:  # noqa: BLE001 - frontmatter raises various types
            warn(f"{name}/{md.name}: unreadable front matter ({e}) — skipping doc")
            continue
        parsed.append((md, post, slugify(str(post.get("slug") or md.stem))))

    slug_by_file = {md.name: slug for md, _, slug in parsed}

    # Pass 2: rewrite intra-wiki links and write each doc.
    docs = []
    for md, post, slug in parsed:
        doc_title = post.get("title") or md.stem
        doc_blurb = post.get("blurb", "")
        doc_order = post.get("order", 100)
        url = f"/subsystems/{name}/{slug}/"
        source_url = f"{repo_url}/blob/{branch}/{docs_path}/{md.name}"
        body = rewrite_links(post.content, slug_by_file, name, repo_url, branch, docs_path)

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
            body,
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

    return {
        "name": name,
        "title": title,
        "blurb": blurb,
        "order": order,
        "url": f"/subsystems/{name}/",
        "repo_url": repo_url,
    }


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
