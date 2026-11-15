"""Content sources and aux data config (adding a source only touches this file)."""

# Permissive licenses allow full-text reproduction (comparable in full); everything else (missing/custom) degrades.
LENIENT_LICENSES = {
    "mit", "isc", "unlicense", "0bsd", "cc-by-4.0", "cc0-1.0",
    "apache", "apache-2.0", "apache license 2.0", "apache license, version 2.0",
    "bsd", "bsd-2-clause", "bsd-3-clause", "bsd 2-clause", "bsd 3-clause",
}

# These keywords in a repo-level LICENSE file mark the repo as permissive.
LENIENT_REPO_KEYWORDS = ("apache license", "mit license", "bsd", "gnu lesser", "isc license")

# The three v1 sources (lower priority number wins as the canonical source).
SOURCES = [
    {
        "id": "anthropics",
        "repo": "https://github.com/anthropics/skills",
        "branch": "main",
        "subdir": "skills",
        "priority": 1,
        "exclude": [],
    },
    {
        "id": "superpowers",
        "repo": "https://github.com/obra/superpowers",
        "branch": "main",
        "subdir": "skills",
        "priority": 2,
        "exclude": [],
    },
    {
        "id": "mattpocock",
        "repo": "https://github.com/mattpocock/skills",
        "branch": "main",
        "subdir": "skills",
        "priority": 3,
        # Quality tiering: half-finished and abandoned directories are excluded (decisions #2/#4).
        "exclude": ["in-progress/", "deprecated/"],
    },
    {
        "id": "emilkowalski",
        "repo": "https://github.com/emilkowalski/skills",
        "branch": "main",
        "subdir": "skills",
        "priority": 4,
        "exclude": [],
    },
    # ---- 2026-10-04 source expansion (due diligence in issue #8 comments) ----
    {
        "id": "azure",
        "repo": "https://github.com/microsoft/azure-skills",
        "branch": "main",
        "subdir": "skills",
        "priority": 5,
        "exclude": [],
    },
    {
        "id": "wshobson",
        "repo": "https://github.com/wshobson/agents",
        "branch": "main",
        # Two nesting levels: plugins/<plugin>/skills/<skill>/
        "subdir": "plugins",
        "priority": 6,
        "exclude": [],
    },
    {
        "id": "kdense",
        "repo": "https://github.com/K-Dense-AI/scientific-agent-skills",
        "branch": "main",
        "subdir": "skills",
        "priority": 7,
        "exclude": ["tests/"],
    },
    {
        "id": "openai",
        "repo": "https://github.com/openai/skills",
        "branch": "main",
        "subdir": "skills",
        "priority": 8,
        # .system holds Codex built-in system skills; no repo-level license → all degrade
        "exclude": ["skills/.system/"],
    },
    {
        "id": "addyosmani",
        "repo": "https://github.com/addyosmani/agent-skills",
        "branch": "main",
        "subdir": "skills",
        "priority": 9,
        "exclude": [],
    },
    {
        "id": "prisma",
        "repo": "https://github.com/prisma/skills",
        # flat at the top level, no skills/ prefix
        "branch": "main",
        "subdir": ".",
        "priority": 10,
        "exclude": ["prisma-database-setup"],
    },
    {
        "id": "baoyu",
        "repo": "https://github.com/JimLiu/baoyu-skills",
        "branch": "main",
        "subdir": "skills",
        "priority": 11,
        # dangerous reverse-engineering API variant, compliance questionable
        "exclude": ["baoyu-danger-"],
    },
    {
        "id": "supabase",
        "repo": "https://github.com/supabase/agent-skills",
        "branch": "main",
        "subdir": "skills",
        "priority": 12,
        "exclude": [],
    },
    # ---- 2026-10-05 hub-discovery expansion (52 repos vetted, driven by stars/official/installs) ----
    {
        "id": "caveman",
        "repo": "https://github.com/JuliusBrussee/caveman",
        "branch": "main",
        "subdir": "skills",
        "priority": 13,
        "exclude": ["plugins/", "engine/", "dist/", "src/"],
    },
    {
        "id": "taste-skill",
        "repo": "https://github.com/Leonxlnx/taste-skill",
        "branch": "main",
        "subdir": "skills",
        "priority": 14,
        "exclude": ["research/"],
    },
    {
        "id": "understand-anything",
        "repo": "https://github.com/Egonex-AI/Understand-Anything",
        "branch": "main",
        "subdir": "understand-anything-plugin/skills",
        "priority": 15,
        "exclude": [],
    },
    {
        "id": "impeccable",
        "repo": "https://github.com/pbakaus/impeccable",
        "branch": "main",
        # one skill ×16 platform copies: canonical lives in .claude/skills/
        "subdir": ".claude/skills",
        "priority": 16,
        "exclude": [],
    },
    {
        "id": "humanizer",
        "repo": "https://github.com/blader/humanizer",
        "branch": "main",
        "subdir": ".",
        "priority": 17,
        "exclude": [],
    },
    {
        "id": "marketingskills",
        "repo": "https://github.com/coreyhaines31/marketingskills",
        "branch": "main",
        "subdir": "skills",
        "priority": 18,
        "exclude": [],
    },
    {
        "id": "pm-skills",
        "repo": "https://github.com/phuryn/pm-skills",
        "branch": "main",
        "subdir": "skills",
        "priority": 19,
        "exclude": [],
    },
    {
        "id": "jeffallan",
        "repo": "https://github.com/Jeffallan/claude-skills",
        "branch": "main",
        "subdir": "skills",
        "priority": 20,
        "exclude": [],
    },
    {
        "id": "nvidia",
        "repo": "https://github.com/NVIDIA/skills",
        "branch": "main",
        "subdir": "skills",
        "priority": 21,
        "exclude": ["plugins/"],
    },
    {
        "id": "stitch",
        "repo": "https://github.com/google-labs-code/stitch-skills",
        "branch": "main",
        "subdir": "plugins/stitch-build/skills",
        "priority": 22,
        "exclude": [],
    },
    {
        "id": "vercel",
        "repo": "https://github.com/vercel-labs/agent-skills",
        "branch": "main",
        "subdir": "skills",
        "priority": 23,
        "exclude": [],
    },
    {
        "id": "firebase",
        "repo": "https://github.com/firebase/agent-skills",
        "branch": "main",
        "subdir": "skills",
        "priority": 24,
        "exclude": [],
    },
    {
        "id": "khazix",
        "repo": "https://github.com/KKKKhazix/khazix-skills",
        "branch": "main",
        "subdir": ".",
        "priority": 25,
        "exclude": [],
    },
]

AUX = {
    "marketplace_json": "https://raw.githubusercontent.com/anthropics/claude-plugins-official/main/.claude-plugin/marketplace.json",
    "skills_sh_search": "https://skills.sh/api/search?q={query}",
    "github_repo_api": "https://api.github.com/repos/{repo}",
}

# Featured combos = curated self-compare picks (CONTEXT.md: two versions of one skill worth comparing;
# after ADR-0001 there are no cross-skill combos, so each entry is [id, id]).
DEFAULT_FEATURED = [
    ["impeccable", "impeccable"],
    ["test-driven-development", "test-driven-development"],
]
