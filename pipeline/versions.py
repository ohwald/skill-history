"""Version axis: extract the commit history of a single SKILL.md from its source repo (timepoint = date + short sha).

Note: `git log -- path` cannot be used here — path simplification silently drops commits that did not touch the path
(including empty commits carrying tags), losing their tag semantics. We take the full log and filter by path ourselves.
"""

import subprocess

from .manifest import fingerprint


def _git(repo, *args):
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True)
    return r.stdout


def load_tags(repo):
    """Returns {sha: [tag, …]}; annotated tags also map to the tagged commit (peeled)."""
    tags = {}
    out = _git(repo, "for-each-ref", "refs/tags",
               "--format=%(refname:short)%09%(objectname)%09%(*objectname)")
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        name, sha = parts[0], parts[1].strip()
        peeled = parts[2].strip() if len(parts) > 2 else ""
        for s in filter(None, (sha, peeled)):
            tags.setdefault(s, []).append(name)
    return tags


def _log_entries(repo):
    """All commits, newest → oldest: [(sha, date, [touched paths])], including empty commits.
    Commit header lines contain a tab (sha\\tdate), file lines do not; that is the discriminator."""
    out = _git(repo, "log", "--format=%H%x09%ad", "--date=short", "--name-only")
    entries, cur = [], None
    for line in out.splitlines():
        if not line.strip():
            continue
        if "\t" in line:
            if cur:
                entries.append(cur)
            sha, _, date = line.partition("\t")
            cur = {"sha": sha, "date": date, "files": []}
        elif cur is not None:
            cur["files"].append(line.strip())
    if cur:
        entries.append(cur)
    return entries


def extract_versions(repo, rel_path, tags=None, max_versions=60):
    """Returns the timepoint list of one SKILL.md (old → new); adjacent commits with identical content fingerprints are deduped;
    tags from skipped commits ride along onto the nearest kept timepoint."""
    tags = tags if tags is not None else load_tags(repo)
    newest_first, last_fp, pending = [], None, set()
    for e in _log_entries(repo):
        commit_tags = tags.get(e["sha"], [])
        touches = rel_path in e["files"]
        if not touches:
            pending.update(commit_tags)
            continue
        try:
            content = _git(repo, "show", f'{e["sha"]}:{rel_path}')
        except subprocess.CalledProcessError:
            pending.update(commit_tags)
            continue
        fp = fingerprint(content)
        if fp == last_fp:
            pending.update(commit_tags)
            continue
        last_fp = fp
        newest_first.append({"sha": e["sha"][:10], "date": e["date"], "fp": fp,
                             "lines": content.count("\n") + 1,
                             "tags": sorted(set(commit_tags) | pending)})
        pending = set()
        if len(newest_first) >= max_versions:
            break
    return list(reversed(newest_first))
