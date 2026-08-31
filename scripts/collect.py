#!/usr/bin/env python3
"""Pull each registered subsystem's GitHub wiki and stage it for the Jekyll build.

The hub owns the registry (subsystems.yml). For every entry we:
  1. Read _subsystem.yml from the main repo's docs/wiki/ (via raw URL)
  2. Clone the repo's wiki (*.wiki.git) — wikis are flat repos with .md pages
  3. Parse front matter and mirror doc bodies into subsystems/<name>/
  4. Write _data/subsystems.yml for the home page

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
import urllib.request
from pathlib import Path

import frontmatter
import json
import yaml

# Matches inline link/image targets — `](target)` or `](target "title")` — and
# reference-style definitions — `[label]: target`. Group "t" is the target.
_INLINE_LINK = re.compile(r"(?P<pre>\]\()(?P<t>[^)\s]+)(?P<post>(?:\s+\"[^\"]*\")?\))")
_REF_LINK = re.compile(r"(?P<pre>^[ \t]*\[[^\]]+\]:[ \t]*)(?P<t>\S+)", re.MULTILINE)
# Extracts hidden metadata: <!-- meta: {"order":10,...} -->
_META_COMMENT = re.compile(r'<!--\s*meta:\s*(\{.*?\})\s*-->', re.DOTALL)

ROOT = Path(__file__).resolve().parent.parent
#: Slug owned by the generated subsystem landing page; a doc may not use it.
RESERVED_SLUG = "index"
#: What a doc claiming RESERVED_SLUG is published as instead.
FALLBACK_SLUG = "start-here"

REGISTRY = ROOT / "subsystems.yml"
TMP = ROOT / ".collect-tmp"
OUT_DIR = ROOT / "subsystems"
DATA_DIR = ROOT / "_data"
DATA_FILE = DATA_DIR / "subsystems.yml"

DEFAULT_BRANCH = "main"


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


def wiki_page_name(filename: str) -> str:
    """Convert a wiki .md filename to its GitHub wiki page URL name.

    GitHub wikis derive page names from filenames by dropping .md and
    replacing hyphens/underscores with spaces. The URL uses the same
    name with spaces replaced by hyphens.
    """
    stem = Path(filename).stem
    name = stem.replace("-", " ").replace("_", " ")
    url_name = name.replace(" ", "-")
    return url_name


def fetch_subsystem_yml(repo: str, branch: str, token: str) -> dict:
    """Fetch _subsystem.yml from the main repo's docs/wiki/ via raw URL.

    _subsystem.yml stays in the main repo (docs/wiki/). Read it via HTTP.
    Returns parsed dict or empty dict on failure.
    """
    url = f"https://raw.githubusercontent.com/{repo}/{branch}/docs/wiki/_subsystem.yml"
    req = urllib.request.Request(url)
    if token:
        req.add_header("Authorization", f"Bearer {token}")

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status == 200:
                return yaml.safe_load(resp.read().decode("utf-8")) or {}
    except Exception as e:
        warn(f"cannot fetch _subsystem.yml from {repo}: {e}")

    return {}


def rewrite_links(body: str, slug_by_file: dict, name: str, repo_url: str) -> str:
    """Fix relative *.md links so they resolve on the hub.

    Authors cross-link docs with flat filenames (e.g. `](administration.md)`).
    Under our directory-style permalinks those would 404. A link to another doc
    in the same wiki becomes its hub permalink; any other relative `.md` link
    becomes a GitHub wiki URL so it still resolves. Absolute URLs and anchors
    are left alone.
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
        page = wiki_page_name(posixpath.basename(path))
        return f"{repo_url}/wiki/{page}" + (sep + frag if sep else "")

    body = _INLINE_LINK.sub(lambda m: m["pre"] + resolve(m["t"]) + m["post"], body)
    body = _REF_LINK.sub(lambda m: m["pre"] + resolve(m["t"]), body)
    return body


def write_with_front_matter(path: Path, meta: dict, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fm = yaml.safe_dump(meta, sort_keys=False, allow_unicode=True).strip()
    path.write_text(f"---\n{fm}\n---\n{body}", encoding="utf-8")


def parse_page(md: Path) -> dict:
    """Parse a wiki page, supporting both YAML frontmatter and markdown-header formats.

    Returns a dict with 'title', 'blurb', 'order', 'slug', 'tags', 'updated',
    'content' (body to render), and 'stem' (filename without .md).
    """
    text = md.read_text(encoding="utf-8")

    # Try frontmatter first (backward compat with old YAML pages)
    try:
        post = frontmatter.loads(text)
        if post.metadata:
            return {
                "title": post.metadata.get("title") or md.stem,
                "blurb": post.metadata.get("blurb", ""),
                "order": post.metadata.get("order", 100),
                "slug": post.metadata.get("slug", ""),
                "tags": post.metadata.get("tags", []),
                "updated": str(post.metadata.get("updated") or post.metadata.get("date") or ""),
                "content": post.content,
                "stem": md.stem,
            }
    except Exception:
        pass

    # New format: # Title, > Blurb, <!-- meta: {...} -->, body
    meta = {"title": md.stem, "blurb": "", "order": 100, "tags": [], "updated": ""}
    lines = text.split("\n")
    body_start = 0

    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith("# ") and not meta.get("title_set"):
            meta["title"] = s[2:].strip()
            meta["title_set"] = True
            body_start = i + 1
        elif s.startswith("> ") and not meta.get("blurb"):
            meta["blurb"] = s[2:].strip()
            body_start = i + 1
        elif not s:
            body_start = max(body_start, i + 1)
            continue
        else:
            # Hit non-header content
            break

    # Extract hidden metadata comment
    remaining = "\n".join(lines[body_start:])
    m = _META_COMMENT.search(remaining)
    if m:
        try:
            hidden = json.loads(m.group(1))
            meta["order"] = hidden.get("order", meta["order"])
            meta["slug"] = hidden.get("slug", "")
            meta["tags"] = hidden.get("tags", [])
            meta["updated"] = str(hidden.get("updated", ""))
            # Remove the comment from body
            remaining = _META_COMMENT.sub("", remaining, count=1).lstrip()
        except json.JSONDecodeError:
            pass

    return {
        "title": meta["title"],
        "blurb": meta.get("blurb", ""),
        "order": meta["order"],
        "slug": meta.get("slug", ""),
        "tags": meta["tags"],
        "updated": meta["updated"],
        "content": remaining,
        "stem": md.stem,
    }


def collect_subsystem(entry: dict, token: str) -> dict | None:
    """Clone one subsystem's wiki, mirror its docs, return its home-page summary."""
    name = entry.get("name")
    repo = entry.get("repo")
    if not name or not repo:
        warn(f"registry entry missing name/repo: {entry!r} — skipping")
        return None

    branch = entry.get("branch", DEFAULT_BRANCH)
    repo_url = f"https://github.com/{repo}"

    # Fetch _subsystem.yml from the main repo (still lives in docs/wiki/)
    log(f"{name}: fetching _subsystem.yml from {repo}@{branch}")
    sub_meta = fetch_subsystem_yml(repo, branch, token)

    title = sub_meta.get("title", name)
    blurb = sub_meta.get("blurb", "")
    order = sub_meta.get("order", 100)

    # Clone the wiki repo. Wiki repos always live at {repo}.wiki.git
    # and use 'master' as their default branch.
    wiki_repo = f"{repo}.wiki"
    clone_dir = TMP / name
    log(f"{name}: cloning wiki {wiki_repo}")
    try:
        clone(wiki_repo, "master", clone_dir, token)
    except subprocess.CalledProcessError as e:
        warn(f"{name}: wiki clone failed ({e.stderr.strip().splitlines()[-1:] or e}) — skipping")
        return None

    # Wiki repos are flat — all .md files at the root.
    # Filter out the Home.md that GitHub auto-creates (it's just a stub).
    wiki_files = sorted(clone_dir.glob("*.md"))
    if not wiki_files:
        warn(f"{name}: no .md files in wiki — skipping")
        return None

    # Pass 1: parse every doc and compute its slug
    parsed = []
    for md in wiki_files:
        if md.name == "Home.md":
            continue
        try:
            data = parse_page(md)
        except Exception as e:
            warn(f"{name}/{md.name}: unreadable ({e}) — skipping doc")
            continue
        slug = slugify(str(data.get("slug") or data["stem"]))
        if slug == RESERVED_SLUG:
            slug = FALLBACK_SLUG
            warn(f"{name}: {md.name} claims the reserved '{RESERVED_SLUG}' slug "
                 f"(the generated landing page owns it) -- publishing it as "
                 f"'{slug}' instead")
        parsed.append((md, data, slug))

    slug_by_file = {md.name: slug for md, _, slug in parsed}

    # Pass 2: rewrite intra-wiki links and write each doc.
    docs = []
    for md, data, slug in parsed:
        doc_title = data.get("title") or md.stem
        doc_blurb = data.get("blurb", "")
        doc_order = data.get("order", 100)
        doc_updated = data.get("updated", "")
        url = f"/subsystems/{name}/{slug}/"
        source_url = f"{repo_url}/wiki/{wiki_page_name(md.name)}/_edit"
        body = rewrite_links(data.get("content", ""), slug_by_file, name, repo_url)

        doc_meta = {
            "layout": "doc",
            "title": doc_title,
            "blurb": doc_blurb,
            "subsystem": name,
            "permalink": url,
            "source_url": source_url,
            "tags": data.get("tags", []),
        }
        if doc_updated:
            doc_meta["updated"] = str(doc_updated)
        write_with_front_matter(OUT_DIR / name / f"{slug}.md", doc_meta, body)
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
            "wiki_url": f"{repo_url}/wiki",
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
        "wiki_url": f"{repo_url}/wiki",
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