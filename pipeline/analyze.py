"""Static analysis of skill fit and context cost.

Two public metrics (both **static estimates**, not model-measured):
- context_cost: resident tokens (frontmatter name+description, the progressive-disclosure resident part) + trigger tokens (body) + attached file count
- compat: harness binding (proprietary frontmatter fields) + instruction style leaning (procedural ⇄ principled)
"""

import os
import re

# Proprietary frontmatter fields of specific harnesses like Claude Code (outside the agentskills.io spec).
HARNESS_FIELDS = {
    "disable-model-invocation": "Claude Code",
    "argument-hint": "Claude Code",
    "allowed-tools": "Claude Code(实验性)",
    "user-invocable": "Claude Code",
    "model": "Claude Code",
    "context": "Claude Code",
    "agent": "Claude Code",
    "requires": "第三方集成声明",
}

# Official spec: name+description required, missing license degrades; presence of these fields means "within spec".
SPEC_FIELDS = {"name", "description", "license", "compatibility", "metadata"}

PROC = re.compile(
    r"^\s*(?:\d+[.)]|[-*+])\s+", re.M)                 # ordered/unordered step items
IMPER = re.compile(
    r"\b(?:never|always|must|do not|don't|avoid|before you|first|then|stop|check|ensure|run|write|test)\b", re.I)
PRIN = re.compile(
    r"\b(?:prefer|consider|aim|balance|in general|generally|ideally|typically|when in doubt)\b", re.I)


def _tokens(text):
    return max(1, (len(text or "") + 3) // 4)


def analyze_context_cost(raw_text, skill_dir=None):
    """context_cost: resident (frontmatter) + trigger (body) + files (attached file count)."""
    m = re.match(r"\A---\s*\n(.*?)\n---\s*\n?", raw_text, re.S)
    fm_block = m.group(1) if m else ""
    body = raw_text[m.end():] if m else raw_text
    resident = 0
    for line in fm_block.splitlines():
        key = line.split(":", 1)[0].strip().lower()
        if key in ("name", "description"):
            resident += _tokens(line)
    files = 0
    if skill_dir and os.path.isdir(skill_dir):
        for root, _dirs, fs in os.walk(skill_dir):
            for f in fs:
                if f != "SKILL.md" and not f.startswith("."):
                    files += 1
    return {
        "resident": resident,
        "trigger": _tokens(body),
        "files": files,
    }


def analyze_compat(meta, body):
    """compat: harness binding + style leaning (heuristics with thresholds).

    binding: portable (spec fields only) / claude-code (proprietary fields present)
    style:   procedural (imperative steps dominate) / principled (trade-off statements dominate) / mixed
    """
    harness = sorted({HARNESS_FIELDS[k] for k in meta if k in HARNESS_FIELDS})
    binding = "claude-code" if harness else "portable"
    steps = len(PROC.findall(body))
    imper = len(IMPER.findall(body))
    prin = len(PRIN.findall(body))
    proc_score = min(steps, 40) + imper          # cap step items so long documents don't drown the signal
    prin_score = prin * 3                        # trade-off statements are the stronger style signal
    if proc_score + prin_score < 10:
        style = "mixed"
    elif prin_score >= 12 and prin_score >= proc_score:
        style = "principled"      # trade-off statements must be dense (≥4) and dominant
    else:
        style = "procedural"      # ecosystem reality: imperative dominates, mixed included
    if proc_score + prin_score < 10:
        style = "mixed"
    unknown = sorted(k for k in meta if k not in SPEC_FIELDS and k not in HARNESS_FIELDS)
    return {
        "binding": binding,
        "harness_fields": harness,
        "style": style,
        "unknown_fields": unknown,
    }
