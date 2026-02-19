"""AI-powered brand intelligence analysis using Claude API.

Sends collected Reddit posts to Claude for strategic analysis.
Produces a structured intelligence report (competitive landscape,
sentiment, pain points, recommendations).

Uses raw urllib — zero dependencies beyond stdlib.
Requires ANTHROPIC_API_KEY environment variable or config setting.
"""

import json
import os
import urllib.request
from datetime import datetime, timezone


API_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_MODEL = "claude-sonnet-4-20250514"


def _get_api_key(cfg):
    """Get API key from environment (preferred) or config."""
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        key = cfg.get("analysis", {}).get("api_key", "")
    return key


def _track_usage(data_dir):
    """Track monthly analysis runs. Returns (count_this_month, usage_dict)."""
    usage_file = os.path.join(data_dir, "analysis_usage.json")
    month_key = datetime.now(timezone.utc).strftime("%Y-%m")

    if os.path.exists(usage_file):
        with open(usage_file, "r") as f:
            usage = json.load(f)
    else:
        usage = {}

    count = usage.get(month_key, 0)
    return count, usage, usage_file, month_key


def _save_usage(usage, usage_file, month_key, count):
    """Save updated usage count."""
    usage[month_key] = count
    os.makedirs(os.path.dirname(usage_file), exist_ok=True)
    with open(usage_file, "w") as f:
        json.dump(usage, f, indent=2)


def _build_prompt(posts_data, cfg):
    """Build the analysis prompt from collected posts."""
    brand_name = cfg["brand"]["name"]
    competitors = cfg["competitors"]["names"]

    # Format posts for the prompt
    posts_text = []
    for p in posts_data[:50]:  # Cap at 50 posts to stay within context
        entry = f"[{p.get('_priority', 'MEDIUM')}] r/{p['subreddit']} | {p['score']}pts | {p['num_comments']} comments\n"
        entry += f"Title: {p['title']}\n"
        if p.get("selftext"):
            entry += f"Text: {p['selftext'][:500]}\n"
        if p.get("_comments_text"):
            entry += f"Top comments: {p['_comments_text'][:800]}\n"
        posts_text.append(entry)

    posts_block = "\n---\n".join(posts_text)

    return f"""You are a brand intelligence analyst. Analyze these Reddit posts and comments about {brand_name} and its competitors in the HR/payroll software space.

Competitors to track: {', '.join(competitors)}

## Reddit Posts & Comments

{posts_block}

## Required Output

Produce a structured brand intelligence report in markdown with these sections:

1. **{brand_name} Brand Perception** — What users say (strengths, weaknesses, sentiment). Use a table format with quotes.

2. **Competitive Landscape** — Table of competitors with: mentions count, core strengths (from Reddit), core weaknesses, position vs {brand_name}.

3. **Market Insights** — What buyers in this market need, with Reddit evidence and implications for {brand_name}. Table format.

4. **Pain Points & Opportunities** — Common frustrations across the market and how {brand_name} can capitalize. Include strategic opportunities.

5. **Recommendation Patterns** — Who gets recommended in which situations and why. Table format.

6. **Key Threats** — Competitors gaining mindshare, with evidence and potential impact.

7. **Actionable Recommendations** — Specific, prioritized actions for {brand_name} across messaging, pricing, support, product, and community. Table format.

8. **Quote Bank** — Key Reddit quotes with source and insight. Table format.

9. **Summary** — 4-5 bullet executive summary with strategic focus areas.

Be specific. Use actual quotes and usernames from the data. Be direct about weaknesses — this is an internal report, not marketing copy."""


def run_analysis(cfg, posts_data, posts_with_comments=None):
    """Run Claude-powered analysis on collected posts. Returns the analysis report text."""
    api_key = _get_api_key(cfg)
    if not api_key:
        print("  [ERROR] ANTHROPIC_API_KEY is required for brand intelligence analysis.")
        print("          Set it as an environment variable or GitHub Secret.")
        print("          Get your key at: https://console.anthropic.com/")
        print("          Without it, you'll only get raw post listings (no strategic analysis).")
        return None

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, "data")
    analysis_cfg = cfg.get("analysis", {})
    model = analysis_cfg.get("model", DEFAULT_MODEL)

    # Track usage
    count, usage, usage_file, month_key = _track_usage(data_dir)
    free_runs = analysis_cfg.get("free_runs_per_month", 6)

    if count >= free_runs:
        print(f"\n  You've used {count} analysis runs this month (included: {free_runs}).")
        print(f"  This tool is free and always will be. If the insights are valuable to you,")
        print(f"  consider supporting continued development — $10 covers ~4 analysis runs.")
        print(f"  E-transfer: justbedi7@gmail.com")
        print()

    # Enrich posts with comment text for the prompt
    if posts_with_comments:
        for p in posts_data:
            if p["id"] in posts_with_comments:
                comments = posts_with_comments[p["id"]]
                if isinstance(comments, list):
                    p["_comments_text"] = " | ".join(
                        f"u/{c['author']} ({c['score']}pts): {c['body'][:200]}"
                        for c in sorted(comments, key=lambda x: x["score"], reverse=True)[:5]
                    )

    prompt = _build_prompt(posts_data, cfg)

    print(f"  Sending {len(posts_data)} posts to Claude ({model}) for analysis...")

    # Call Claude API via urllib
    request_body = json.dumps({
        "model": model,
        "max_tokens": 8000,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")

    req = urllib.request.Request(API_URL, data=request_body, headers={
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    })

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        print(f"  [ERROR] Claude API returned {e.code}: {error_body[:200]}")
        return None
    except Exception as e:
        print(f"  [ERROR] Claude API call failed: {e}")
        return None

    # Extract text from response
    analysis_text = ""
    for block in result.get("content", []):
        if block.get("type") == "text":
            analysis_text += block["text"]

    if not analysis_text:
        print("  [ERROR] Empty response from Claude API")
        return None

    # Add header
    run_time = datetime.now(timezone.utc)
    brand_name = cfg["brand"]["name"]
    header = (
        f"# {brand_name} - Brand Intelligence Report (Reddit-derived)\n\n"
        f"*AI-analyzed from {len(posts_data)} Reddit posts and comments*\n"
        f"*Date: {run_time.strftime('%B %d, %Y')}*\n"
        f"*Model: {model}*\n\n---\n\n"
    )
    full_report = header + analysis_text

    # Save analysis report
    reports_dir = os.path.join(data_dir, "reports")
    os.makedirs(reports_dir, exist_ok=True)

    analysis_file = os.path.join(reports_dir, "analysis.md")
    with open(analysis_file, "w") as f:
        f.write(full_report)

    dated_file = os.path.join(reports_dir, f"analysis-{run_time.strftime('%Y-%m-%d')}.md")
    with open(dated_file, "w") as f:
        f.write(full_report)

    # Update usage counter
    _save_usage(usage, usage_file, month_key, count + 1)

    # Usage stats
    input_tokens = result.get("usage", {}).get("input_tokens", 0)
    output_tokens = result.get("usage", {}).get("output_tokens", 0)
    cost_estimate = (input_tokens * 3 / 1_000_000) + (output_tokens * 15 / 1_000_000)

    print(f"  Analysis complete!")
    print(f"  Saved to: {analysis_file}")
    print(f"  Tokens: {input_tokens} in / {output_tokens} out (~${cost_estimate:.3f})")
    print(f"  Runs this month: {count + 1}/{free_runs} free")

    if count + 1 >= free_runs:
        print(f"\n  ---")
        print(f"  This tool is free and open source. If the analysis is valuable,")
        print(f"  consider supporting development: $10 covers ~4 analysis runs.")
        print(f"  E-transfer: justbedi7@gmail.com")
        print(f"  ---")

    return full_report
