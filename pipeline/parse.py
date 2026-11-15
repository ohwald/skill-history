"""SKILL.md frontmatter parsing and license triage. Tolerates unknown fields; malformed lines are skipped."""

import re

from . import config

FM_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.S)
KEY_RE = re.compile(r"[A-Za-z0-9_-]+")


def parse_frontmatter(text):
    """Returns (meta, body). Without frontmatter, meta is empty and body is the raw text; malformed lines are skipped."""
    m = FM_RE.match(text)
    if not m:
        return {}, text
    meta = {}
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, val = line.partition(":")
        key, val = key.strip(), val.strip()
        if not KEY_RE.fullmatch(key):
            continue
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        meta[key] = val
    return meta, text[m.end():]


def classify_license(fm_license, license_text):
    """License triage: returns (status, label).

    frontmatter license wins; mention of proprietary/commercial degrades immediately; a permissive match → full;
    写了 LICENSE.txt / 未知值 → 看 license_text(目录内 LICENSE 文件内容)的关键词;
    全无 → degraded(undisclosed)。
    """
    label = (fm_license or "").strip()
    key = label.lower()
    if label and any(k in key for k in ("proprietary", "commercial", "all rights reserved")):
        return "degraded", (label or "undisclosed")
    if label:
        for k in config.LENIENT_LICENSES:
            if k in key:
                return "full", label
        if license_text and any(k in license_text.lower() for k in config.LENIENT_REPO_KEYWORDS):
            return "full", label
        return "degraded", label
    if license_text:
        low = license_text.lower()
        if any(k in low for k in config.LENIENT_REPO_KEYWORDS):
            return "full", "repo LICENSE"
        return "degraded", "undisclosed"
    return "degraded", "undisclosed"
