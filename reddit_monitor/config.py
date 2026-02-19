"""Configuration loader for Reddit Monitor."""

import sys
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

REQUIRED_SECTIONS = [
    "brand",
    "competitors",
    "subreddits",
    "keywords",
    "queries",
    "settings",
]


def load_config(path: str | Path | None = None) -> dict:
    """Load and validate the TOML configuration file.

    Parameters
    ----------
    path : str | Path | None
        Path to the TOML config file.  When *None* (the default), the loader
        looks for ``config.toml`` in the project root (two directories above
        this module).

    Returns
    -------
    dict
        Parsed configuration dictionary.

    Raises
    ------
    SystemExit
        If the file is missing or any required section is absent.
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
    missing = [section for section in REQUIRED_SECTIONS if section not in config]
    if missing:
        print(f"ERROR: config.toml is missing required section(s): {', '.join(missing)}")
        print(f"  Required sections: {', '.join(REQUIRED_SECTIONS)}")
        sys.exit(1)

    return config
