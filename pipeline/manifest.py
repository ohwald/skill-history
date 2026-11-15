"""Manifest assembly: walk sources → parse & triage → same-name dedup (canonical wins + "also seen")."""

import hashlib
import os

from . import config
from .analyze import analyze_compat, analyze_context_cost
from .parse import classify_license, parse_frontmatter  # noqa: F401 (re-export)


def fingerprint(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def approx_tokens(text):
    return max(1, len(text) // 4)


# ---- Picker metadata: domain tags + suite membership ----
TAG_RULES = [
    ("design", ("design", "ui", "frontend", "css", "typography", "brand", "aesthetic", "figma")),
    ("frontend", ("frontend", "react", "vue", "web", "component")),
    ("backend", ("api", "backend", "server", "database", "sql")),
    ("devops", ("deploy", "ci", "k8s", "kubernetes", "docker", "cloud", "infra", "terraform", "vercel", "firebase", "aws", "azure")),
    ("testing", ("test", "tdd", "debug", "qa")),
    ("writing", ("writing", "doc", "blog", "content", "diagram", "docx", "pdf", "pptx", "xlsx")),
    ("ai", ("llm", "prompt", "model", "agent", "mcp", "cuda", "nemo", "inference")),
    ("marketing", ("marketing", "growth", "seo", "gtm", "pricing", "sales")),
    ("data", ("data", "analytics", "chart", "viz", "pandas")),
    ("research", ("research", "paper", "science", "bio", "chem", "physics")),
    ("security", ("security", "auth", "vuln", "crypto")),
    ("pm", ("product", "roadmap", "spec", "planning", "okr")),
]

def derive_tags(name, desc, category, source_id):
    tags = set()
    text = (name + " " + (desc or "")).lower()
    for tag, kws in TAG_RULES:
        if any(k in text for k in kws):
            tags.add(tag)
    if category:
        tags.add(category.lower())
    if source_id in ("anthropics", "openai", "azure", "nvidia", "vercel", "firebase", "prisma",
                     "supabase", "stitch", "google"):
        tags.add("official")
    return sorted(tags)

def derive_set(source, rel_path):
    """Suite membership: one set per repo by default; nested repos split down to package level (wshobson's plugins/<pkg>/, phuryn's pm-*)."""
    sid = source["id"]
    repo = source["repo"].removeprefix("https://github.com/")
    pkg = None
    import re as _re
    m = _re.search(r"(?:plugins|packages)/([^/]+)/", rel_path)
    if m:
        pkg = m.group(1)
    else:
        m2 = _re.match(r"([a-z0-9-]+?)(?:-skills)?/skills/", rel_path)
        if m2 and sid in ("pm-skills",) and m2.group(1).startswith("pm-"):
            pkg = m2.group(1)
    if pkg:
        return {"id": f"{sid}/{pkg}", "label": f"{repo.split('/')[-1]} · {pkg}", "repo": repo}
    return {"id": sid, "label": repo.split("/")[-1], "repo": repo}


def collect_source_entries(source, repo_dir):
    """Walk one source repo and emit raw entries. The repo-level LICENSE is the license fallback."""
    base = os.path.join(repo_dir, source["subdir"])
    entries = []
    if not os.path.isdir(base):
        return entries
    repo_license = ""
    for lic_name in ("LICENSE", "LICENSE.txt", "LICENSE.md"):
        lic_path = os.path.join(repo_dir, lic_name)
        if os.path.isfile(lic_path):
            with open(lic_path, encoding="utf-8", errors="replace") as f:
                repo_license = f.read()
            break
    for root, _dirs, files in os.walk(base):
        if "SKILL.md" not in files:
            continue
        rel = os.path.relpath(root, repo_dir).replace(os.sep, "/")
        if any(ex in rel + "/" for ex in source["exclude"]):
            continue
        path = os.path.join(root, "SKILL.md")
        with open(path, encoding="utf-8", errors="replace") as f:
            text = f.read()
        meta, _body = parse_frontmatter(text)
        body = text  # keep the full raw text (frontmatter included): the frontend segments it by the official structure
        lic_text = ""
        for lic_name in ("LICENSE.txt", "LICENSE"):
            lic_path = os.path.join(root, lic_name)
            if os.path.isfile(lic_path):
                with open(lic_path, encoding="utf-8", errors="replace") as f:
                    lic_text = f.read()
                break
        if not lic_text:
            lic_text = repo_license
        status, lic_label = classify_license(meta.get("license"), lic_text)
        name = meta.get("name") or os.path.basename(root)
        cost = analyze_context_cost(text, root)
        compat = analyze_compat(meta, text)
        tags = derive_tags(name, meta.get("description", ""), None, source["id"])
        sk_set = derive_set(source, rel)
        head = ""
        try:
            from .versions import _git
            head = _git(repo_dir, "rev-parse", "HEAD").strip()[:12]
        except Exception:
            head = ""
        files = []
        for froot, _fd, ffiles in os.walk(root):
            for fname in ffiles:
                if fname == "SKILL.md" or fname.startswith("."):
                    continue
                fpath = os.path.join(froot, fname)
                frel = os.path.relpath(fpath, root).replace(os.sep, "/")
                try:
                    fsha = hashlib.sha256(open(fpath, "rb").read()).hexdigest()[:16]
                except OSError:
                    continue
                files.append({"path": frel, "size": os.path.getsize(fpath), "sha": fsha})
        files.sort(key=lambda x: x["path"])
        entries.append({
            "head": head,
            "files": files,
            "tags": tags,
            "set": sk_set,
            "context_cost": cost,
            "compat": compat,
            "source_id": source["id"],
            "priority": source["priority"],
            "repo": source["repo"].removeprefix("https://github.com/"),
            "name": name,
            "desc": meta.get("description", ""),
            "license": lic_label,
            "license_status": status,
            "body": body,
            "rel_dir": rel,
            "rel_path": rel + "/SKILL.md",
            "url": f"{source['repo']}/tree/main/{rel}",
            "repo_dir": str(repo_dir),
        })
    return entries


def assemble(entries, aux=None, bodies=None):
    """Same-name dedup: identical content fingerprints → the canonical source keeps the entry, others log "also seen";
    different content → treated as distinct skills; non-canonical copies get a --<source_id> suffix.
    Pass a mutable dict as bodies to collect {fingerprint: text} for all kept bodies (version bodies are added by the caller)."""
    aux = aux or {}
    stars = aux.get("stars", {})
    installs = aux.get("installs", {})
    categories = aux.get("categories", {})
    by_name = {}
    for e in sorted(entries, key=lambda x: x["priority"]):
        by_name.setdefault(e["name"], []).append(e)
    skills, used_ids = [], set()
    for name, group in sorted(by_name.items()):
        canonical = group[0]
        fp = fingerprint(canonical["body"])
        same = [e for e in group[1:] if fingerprint(e["body"]) == fp]
        diff = [e for e in group[1:] if fingerprint(e["body"]) != fp]
        sid = name
        while sid in used_ids:
            sid += "-x"
        used_ids.add(sid)
        also_seen = [e["repo"] for e in same]
        if bodies is not None:
            bodies[fp] = canonical["body"]
        skills.append({
            "id": sid, "name": name, "desc": canonical["desc"],
            "source": canonical["repo"], "source_id": canonical["source_id"],
            "license": canonical["license"], "license_status": canonical["license_status"],
            "stars": stars.get(canonical["repo"]), "installs": installs.get(name),
            "category": categories.get(name),
            "lines": canonical["body"].count("\n") + 1,
            "tokens": approx_tokens(canonical["body"]),
            "fp": fp, "also_seen": also_seen, "url": canonical["url"],
            "context_cost": canonical["context_cost"], "compat": canonical["compat"],
            "head": canonical.get("head", ""), "files": canonical.get("files", []),
            "tags": canonical.get("tags", []), "set": canonical.get("set"),
            "rel_path": canonical["rel_path"], "versions": [], "_repo_dir": canonical.get("repo_dir"),
        })
        for e in diff:
            sid2 = f"{name}--{e['source_id']}"
            while sid2 in used_ids:
                sid2 += "-x"
            used_ids.add(sid2)
            fp2 = fingerprint(e["body"])
            if bodies is not None:
                bodies[fp2] = e["body"]
            skills.append({
                "id": sid2, "name": name, "desc": e["desc"],
                "source": e["repo"], "source_id": e["source_id"],
                "license": e["license"], "license_status": e["license_status"],
                "stars": stars.get(e["repo"]), "installs": installs.get(name),
                "category": categories.get(name),
                "lines": e["body"].count("\n") + 1,
                "tokens": approx_tokens(e["body"]),
                "fp": fp2, "also_seen": [], "url": e["url"],
                "context_cost": e["context_cost"], "compat": e["compat"],
                "head": e.get("head", ""), "files": e.get("files", []),
                "tags": e.get("tags", []), "set": e.get("set"),
                "rel_path": e["rel_path"], "versions": [], "_repo_dir": e.get("repo_dir"),
            })
    for s in skills:
        if s.get("category"):
            s["tags"] = sorted(set((s.get("tags") or []) + [s["category"].lower()]))
    # Name conflicts: same-name different-content entries annotate each other (installing both overwrites one, platforms should warn).
    by_name2 = {}
    for s in skills:
        by_name2.setdefault(s["name"], []).append(s)
    for group in by_name2.values():
        ids = [s["id"] for s in group]
        for s in group:
            s["name_conflicts"] = [i for i in ids if i != s["id"]]
    skills.sort(key=lambda s: (s["source_id"], s["name"]))
    return skills
