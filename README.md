<div align="center">

# Skill History

**The wayback machine for Agent Skills.**

[![Live site](https://img.shields.io/badge/live_site-ohwald.github.io%2Fskill--history-7aa2f7)](https://ohwald.github.io/skill-history/)
[![Skills tracked](https://img.shields.io/badge/skills-1%2C170%2B_%C2%B7_24_sources-bb9af7)](https://ohwald.github.io/skill-history/)
[![Freshness](https://img.shields.io/badge/snapshot-rebuilt_daily-9ece6a)](https://ohwald.github.io/skill-history/)
![Python](https://img.shields.io/badge/python-3.11%2B-565f89)

[🚀 Open the live site](https://ohwald.github.io/skill-history/) · [简体中文](README.zh-CN.md)

<img src="design-preview/hero.png" alt="Skill History in version mode: the commit timeline on top, two commits of the same skill side by side below" width="980">

*Version mode — `api-and-interface-design` @ 0.6.10 vs @ 0.6.12, picked on the commit timeline above.*

</div>

## What is this?

**Agent Skills** are how coding agents carry reusable context — a `SKILL.md` plus scripts and references, loaded on demand by Claude Code, Codex, Cursor and friends. Skills are versioned like code, but until now there was no way to see how they actually change.

Skill History is a read-only window into that ecosystem:

- **Read any two skills side by side** — a real diff editor with shared structure TOC, not two scrollbars. 1,170+ skills indexed across 24 sources, from [anthropics/skills](https://github.com/anthropics/skills) to community collections.
- **Replay a skill's history** — every skill is a commit timeline with upstream tag markers; drag the dual handles to any two points and see exactly what changed between versions.
- **Judge a skill before you adopt it** — per-skill context cost (tokens), line counts, install counts, stars, category, license, and an "also seen in" list of mirrors.
- **Watch the ecosystem move** — all sources are re-captured into a fresh public snapshot every day, so the site tracks the ecosystem, not a one-off export.

License-aware by design: permissive-licensed skills are shown in full; proprietary or undeclared ones degrade to metadata + source link, and the original text is never reproduced.

Pure Python-stdlib pipeline + a zero-build single-file frontend (vanilla JS + Monaco via CDN). No runtime dependencies.

## Features

- **Side-by-side comparison** — Monaco diff editor (falls back to plain columns when the CDN is unreachable), A/B identity colors running through slots and columns
- **Version comparison** — every slot is a *skill @ time point*: pick any commit (with upstream tag annotations) per side; two slots on the same skill automatically become a version diff with a clickable commit timeline
- **Structured view** — content is segmented by the official SKILL.md convention (YAML frontmatter + heading hierarchy, code fences kept intact) with a structure TOC that jumps both columns; a raw-diff toggle is one click away
- **License-aware** — permissive-licensed skills are shown in full; proprietary/undeclared ones are *degraded* (metadata + source link only, original text never reproduced)
- **Curated sources** — 24 sources incl. [anthropics/skills](https://github.com/anthropics/skills), [obra/superpowers](https://github.com/obra/superpowers), [mattpocock/skills](https://github.com/mattpocock/skills), wshobson/agents, firebase/agent-skills, prisma/skills, supabase/agent-skills …(extend via config)
- **6 editor themes** — Tokyo Night (default), Catppuccin Mocha, One Dark Pro, GitHub Light, One Light, Solarized Light; plus a 中文/English bilingual UI

## Quick start

```bash
# fetch all content sources (single-branch, full history)
python3 -m pipeline.collect

# build (version axis + optional networked aux data)
python3 -m pipeline.build --real --out site --fetch-aux

# preview
python3 -m http.server 8765 -d site
```

No-network demo mode:

```bash
python3 -m pipeline.build --fixtures fixtures --out site
```

Requires Python ≥ 3.11 (stdlib only) and `git`.

## Tests

```bash
python3 -m pytest -q
```

The pipeline is the only formal test seam: frontmatter parsing, license triage, canonical dedup, version-axis extraction, and manifest validation are covered end-to-end (including a daily-update loop test against a simulated upstream). The frontend is zero-build vanilla JS and is accepted manually against `design-preview/`.

## Architecture

```
pipeline/
├── collect.py    # clone/fetch sources + aux data (marketplace categories, skills.sh installs, stars)
├── parse.py      # SKILL.md frontmatter parsing + license triage
├── manifest.py   # collection walk + canonical dedup ("also seen") + content fingerprints
├── versions.py   # version axis: per-path commit history (date + short sha, tag annotations)
├── validate.py   # build-time manifest validation (build fails loudly)
└── build.py      # single-file site assembly (inline manifest, per-fingerprint bodies, 6-theme CSS)
template/          # index.html + app.js (picker / compare / degraded / version-mode states)
design-preview/    # rendered design references, theme screenshots, themes.json (color tokens)
```

Data flow: `collect → parse → license triage → canonical dedup → version axis → validate → single-file site`. Bodies are served per content fingerprint so switching comparisons only fetches what changed.

## Themes

`design-preview/themes.json` is the single source of truth for color tokens; the build inlines all six presets as CSS variables and the site ships a switcher. Adding a preset = adding an entry there.

## Deployment

- **Capture** (`.github/workflows/capture.yml`, daily 02:23 UTC): quality gate → re-collect → rebuild → commit `site/`
- **Pages** (`.github/workflows/pages.yml`): deploys the committed `site/` to GitHub Pages on push / capture completion

## Contributing

Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) and are written in English:

```
<type>(<optional scope>): <summary in imperative mood>
```

Types: `feat` `fix` `docs` `refactor` `test` `build` `ci` `chore`. Examples: `feat(picker): filter skills by source`, `fix(build): fail on leftover template placeholders`.
