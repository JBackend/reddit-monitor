"""State management for tracking seen posts across runs."""

import json
import os


def load_state(state_file):
    """Load the monitor state file (seen post IDs, last run time)."""
    if os.path.exists(state_file):
        with open(state_file, "r") as f:
            return json.load(f)
    return {"seen_post_ids": [], "last_run": None}


def save_state(state, state_file):
    """Save the monitor state file."""
    os.makedirs(os.path.dirname(state_file), exist_ok=True)
    with open(state_file, "w") as f:
        json.dump(state, f, indent=2)


def trim_seen_ids(state, max_ids=5000):
    """Trim seen IDs list to prevent unbounded growth. Keeps most recent."""
    ids = state.get("seen_post_ids", [])
    if len(ids) > max_ids:
        state["seen_post_ids"] = ids[-max_ids:]
    return state
