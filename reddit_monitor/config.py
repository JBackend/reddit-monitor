"""Configuration loader for Reddit Monitor.

Only 3 fields are required:
  - brand.name
  - brand.industry
  - competitors.names

Everything else (aliases, subreddits, keywords, queries, settings) is
optional and will be derived programmatically from those 3 fields when
missing.  Existing full config.toml files continue to work unchanged.
"""

import re
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    # Python < 3.11 fallback
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ModuleNotFoundError:
        print("ERROR: Python 3.11+ is required (for tomllib), or install tomli: pip install tomli")
        sys.exit(1)

# Project root is two levels up from this file (reddit_monitor/config.py -> project root)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Only brand and competitors sections are truly required now.
REQUIRED_SECTIONS = [
    "brand",
    "competitors",
]

# Required keys within those sections
REQUIRED_KEYS = {
    "brand": ["name", "industry"],
    "competitors": ["names"],
}

# Default settings values
_DEFAULT_SETTINGS = {
    "user_agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "rate_delay": 2,
    "max_results_per_query": 25,
    "max_comments_to_fetch": 15,
    "min_comments_for_fetch": 5,
    "max_seen_ids": 5000,
}


# ---------------------------------------------------------------------------
# Derivation helpers — generate smart defaults from the 3 required fields
# ---------------------------------------------------------------------------

def _derive_aliases(brand_name: str) -> list[str]:
    """Generate brand aliases from the brand name.

    Produces: lowercase form, no-spaces form, .com form.
    """
    lower = brand_name.lower()
    no_spaces = lower.replace(" ", "")
    dot_com = no_spaces + ".com"
    aliases = [lower]
    if no_spaces != lower:
        aliases.append(no_spaces)
    aliases.append(dot_com)
    return aliases


def _derive_subreddits(industry: str) -> list[str]:
    """Return a reasonable set of subreddits based on industry keywords."""
    # Always include these general business subs
    subs = [
        "smallbusiness", "entrepreneur", "startup", "startups", "saas",
    ]
    industry_lower = industry.lower()

    # Map well-known industry terms to relevant subreddits
    _INDUSTRY_SUB_MAP = {
        "hr": ["humanresources"],
        "human resources": ["humanresources"],
        "payroll": ["payroll", "bookkeeping", "accounting"],
        "finance": ["personalfinancecanada", "personalfinance", "accounting"],
        "accounting": ["accounting", "bookkeeping"],
        "tax": ["tax", "cantax"],
        "marketing": ["marketing", "digitalmarketing", "socialmedia"],
        "sales": ["sales"],
        "crm": ["sales", "crm"],
        "ecommerce": ["ecommerce", "shopify"],
        "devops": ["devops", "sysadmin"],
        "software": ["sysadmin"],
        "legal": ["legaladvice"],
        "real estate": ["realestate", "commercialrealestate"],
        "healthcare": ["healthcare"],
        "education": ["edtech"],
        "recruiting": ["recruiting", "humanresources"],
    }

    for term, sub_list in _INDUSTRY_SUB_MAP.items():
        if term in industry_lower:
            for s in sub_list:
                if s not in subs:
                    subs.append(s)

    return subs


def _derive_relevance_keywords(industry: str) -> list[str]:
    """Split industry into keyword terms and add common synonyms."""
    # Split on common separators
    raw_terms = re.split(r"[/,&]+", industry.lower())
    keywords = []
    for term in raw_terms:
        term = term.strip()
        if term:
            keywords.append(term)
            # Add "software" variant
            keywords.append(f"{term} software")

    # Add generic business terms
    keywords.extend(["small business", "startup", "recommend", "best"])
    # Deduplicate while preserving order
    seen = set()
    unique = []
    for kw in keywords:
        if kw not in seen:
            seen.add(kw)
            unique.append(kw)
    return unique


def _derive_queries(brand_name: str, industry: str, competitor_names: list[str]) -> dict:
    """Auto-generate daily, weekly, and scrape query sets.

    Templates:
      - Direct brand mentions
      - Competitor mentions with industry terms
      - "best <industry> software" style queries
      - Comparison / switching threads
    """
    # Prepare helper strings
    brand_nospace = brand_name.replace(" ", "")
    brand_dotcom = brand_nospace.lower() + ".com"
    industry_terms = [t.strip() for t in re.split(r"[/,&]+", industry) if t.strip()]
    industry_slug = " ".join(industry_terms).lower()

    # Pick top competitors for OR-chain (max 4 to keep queries short)
    top_comps = competitor_names[:4]
    comp_or = " OR ".join(f'"{c.title()}"' for c in top_comps)

    year = datetime.now(timezone.utc).year

    daily = [
        {
            "label": "brand_direct",
            "query": f'"{brand_name}" OR "{brand_nospace}" OR "{brand_dotcom}"',
        },
        {
            "label": "industry_recommend",
            "query": f"{industry_slug} software recommend OR best",
        },
        {
            "label": "competitor_mentions",
            "query": f'{comp_or} {industry_slug}',
        },
    ]

    weekly = [
        {
            "label": "switching_platforms",
            "query": f'switching OR migrating {industry_slug} software',
        },
        {
            "label": "comparison_threads",
            "query": f'{industry_slug} vs recommend',
        },
        {
            "label": f"best_{year}",
            "query": f"best {industry_slug} software {year}",
        },
    ]

    scrape = [
        {
            "label": "brand_general",
            "query": f'"{brand_name}"',
        },
        {
            "label": "brand_domain",
            "query": f'"{brand_nospace}" OR "{brand_dotcom}"',
        },
        {
            "label": f"best_{industry_terms[0] if industry_terms else 'software'}",
            "query": f"best {industry_slug} software",
        },
        {
            "label": "recommend",
            "query": f"{industry_slug} software recommendation",
        },
    ]

    # Add one scrape query per top competitor
    for comp in top_comps:
        safe_label = re.sub(r"[^a-z0-9]+", "_", comp.lower()).strip("_")
        scrape.append({
            "label": safe_label,
            "query": f'"{comp.title()}" {industry_slug}',
        })

    return {"daily": daily, "weekly": weekly, "scrape": scrape}


# ---------------------------------------------------------------------------
# Main loader
# ---------------------------------------------------------------------------

def _populate_defaults(config: dict) -> dict:
    """Fill in missing optional sections/keys with smart derived defaults.

    Mutates *config* in place and returns it.
    """
    brand_name = config["brand"]["name"]
    industry = config["brand"]["industry"]
    competitor_names = config["competitors"]["names"]

    # brand.aliases
    if not config["brand"].get("aliases"):
        config["brand"]["aliases"] = _derive_aliases(brand_name)

    # subreddits.high_value
    config.setdefault("subreddits", {})
    if not config["subreddits"].get("high_value"):
        config["subreddits"]["high_value"] = _derive_subreddits(industry)

    # keywords.relevance / keywords.geographic
    config.setdefault("keywords", {})
    if not config["keywords"].get("relevance"):
        config["keywords"]["relevance"] = _derive_relevance_keywords(industry)
    if not config["keywords"].get("geographic"):
        config["keywords"]["geographic"] = []

    # queries (daily / weekly / scrape)
    config.setdefault("queries", {})
    if not config["queries"].get("daily") and not config["queries"].get("weekly") and not config["queries"].get("scrape"):
        derived = _derive_queries(brand_name, industry, competitor_names)
        config["queries"] = derived
    else:
        # Ensure all sub-keys exist even if only some are provided
        config["queries"].setdefault("daily", [])
        config["queries"].setdefault("weekly", [])
        config["queries"].setdefault("scrape", [])

    # settings — merge provided values over defaults
    config.setdefault("settings", {})
    for key, default_val in _DEFAULT_SETTINGS.items():
        config["settings"].setdefault(key, default_val)

    # analysis (optional section)
    config.setdefault("analysis", {})
    config["analysis"].setdefault("model", "claude-sonnet-4-20250514")
    config["analysis"].setdefault("free_runs_per_month", 6)

    # email (optional section)
    config.setdefault("email", {})
    config["email"].setdefault("subject_prefix", "[Reddit Monitor]")

    return config


def load_config(path: str | Path | None = None) -> dict:
    """Load and validate the TOML configuration file.

    Only 3 fields are required:
      - brand.name
      - brand.industry
      - competitors.names

    All other sections/keys are optional and will be derived from those
    three values when missing.

    Parameters
    ----------
    path : str | Path | None
        Path to the TOML config file.  When *None* (the default), the loader
        looks for ``config.toml`` in the project root (two directories above
        this module).

    Returns
    -------
    dict
        Parsed configuration dictionary with defaults applied.

    Raises
    ------
    SystemExit
        If the file is missing or any required field is absent.
    """
    if path is None:
        path = _PROJECT_ROOT / "config.toml"
    else:
        path = Path(path)

    # --- Check file exists ---------------------------------------------------
    if not path.exists():
        print(f"ERROR: Configuration file not found: {path}")
        print("  Copy config.example.toml to config.toml and fill in your settings.")
        sys.exit(1)

    # --- Parse TOML -----------------------------------------------------------
    try:
        with open(path, "rb") as fh:
            config = tomllib.load(fh)
    except tomllib.TOMLDecodeError as exc:
        print(f"ERROR: Failed to parse {path}: {exc}")
        sys.exit(1)

    # --- Validate required sections ------------------------------------------
    missing_sections = [s for s in REQUIRED_SECTIONS if s not in config]
    if missing_sections:
        print(f"ERROR: config.toml is missing required section(s): {', '.join(missing_sections)}")
        print(f"  Required sections: {', '.join(REQUIRED_SECTIONS)}")
        sys.exit(1)

    # --- Validate required keys within sections ------------------------------
    missing_keys = []
    for section, keys in REQUIRED_KEYS.items():
        for key in keys:
            if key not in config.get(section, {}):
                missing_keys.append(f"{section}.{key}")
    if missing_keys:
        print(f"ERROR: config.toml is missing required field(s): {', '.join(missing_keys)}")
        print("  Required fields: brand.name, brand.industry, competitors.names")
        sys.exit(1)

    # --- Populate defaults for optional fields --------------------------------
    _populate_defaults(config)

    return config
