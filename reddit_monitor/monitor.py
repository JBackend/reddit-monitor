"""Core monitoring logic — config-driven Reddit brand monitoring."""

import os
import json
from datetime import datetime, timezone
from . import api, state
from .report import generate_report


def is_relevant(post, high_value_subreddits, relevance_keywords):
    """Check if a post is relevant based on subreddit and keywords."""
    sub = post["subreddit"].lower()
    if sub in high_value_subreddits:
        return True
    text = (post["title"] + " " + post["selftext"]).lower()
    return any(kw in text for kw in relevance_keywords)


def classify_priority(post, brand_aliases, competitor_names, geographic_terms, comments=None):
    """Classify post priority: URGENT, HIGH, or MEDIUM."""
    text = (post["title"] + " " + post["selftext"]).lower()

    # URGENT: Direct brand mention
    if any(brand in text for brand in brand_aliases):
        return "URGENT"

    # Check comments too
    if comments:
        comment_text = " ".join(c["body"].lower() for c in comments)
        if any(brand in comment_text for brand in brand_aliases):
            return "URGENT"

    # HIGH: Competitor mention (especially in geographic context)
    has_competitor = any(comp in text for comp in competitor_names)
    if has_competitor:
        return "HIGH"

    return "MEDIUM"


def scan_comments_for_brands(comments, brand_aliases, competitor_names):
    """Scan comments for brand mentions, return findings."""
    findings = []
    for c in comments:
        body_lower = c["body"].lower()
        mentioned_brand = [b for b in brand_aliases if b in body_lower]
        mentioned_competitors = [b for b in competitor_names if b in body_lower]
        if mentioned_brand or mentioned_competitors:
            findings.append({
                "author": c["author"],
                "score": c["score"],
                "rise_mentions": mentioned_brand,
                "competitor_mentions": mentioned_competitors,
                "excerpt": c["body"][:300],
            })
    return findings


def run_monitor(cfg, mode="daily"):
    """Run the monitor. Returns a summary dict."""
    # Extract config values
    brand_name = cfg["brand"]["name"]
    brand_aliases = [a.lower() for a in cfg["brand"]["aliases"]]
    competitor_names = [c.lower() for c in cfg["competitors"]["names"]]
    high_value_subs = set(s.lower() for s in cfg["subreddits"]["high_value"])
    relevance_kw = [k.lower() for k in cfg["keywords"]["relevance"]]
    geographic = [g.lower() for g in cfg["keywords"]["geographic"]]
    settings = cfg["settings"]
    user_agent = settings["user_agent"]
    rate_delay = settings["rate_delay"]
    max_results = settings["max_results_per_query"]
    max_comments = settings.get("max_comments_to_fetch", 15)
    min_comments = settings.get("min_comments_for_fetch", 5)
    max_seen = settings.get("max_seen_ids", 5000)

    # Paths (relative to project root — config.toml's directory)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, "data")
    reports_dir = os.path.join(data_dir, "reports")
    state_file = os.path.join(data_dir, "monitor_state.json")

    run_time = datetime.now(timezone.utc)
    print(f"Reddit Monitor — {mode} run at {run_time.strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*60}")

    # Load state
    st = state.load_state(state_file)
    seen_ids = set(st["seen_post_ids"])
    print(f"  Tracking {len(seen_ids)} previously seen posts")

    # Select queries based on mode
    queries = list(cfg["queries"].get("daily", []))
    if mode in ("weekly", "all"):
        queries += list(cfg["queries"].get("weekly", []))
    time_filter = "week" if mode == "daily" else "month"

    # Run searches
    all_posts = []
    for q in queries:
        posts = api.run_search(
            q["label"], q["query"], q.get("subreddit"),
            time_filter=time_filter, user_agent=user_agent,
            rate_delay=rate_delay, max_results=max_results,
        )
        for p in posts:
            p["_query_label"] = q["label"]
        all_posts.extend(posts)

    # Deduplicate
    unique = {}
    for p in all_posts:
        if p["id"] not in unique:
            unique[p["id"]] = p
    all_posts = list(unique.values())
    print(f"\n  Total unique posts from search: {len(all_posts)}")

    # Filter seen
    new_posts = [p for p in all_posts if p["id"] not in seen_ids]
    print(f"  New (unseen) posts: {len(new_posts)}")

    # Filter relevant
    new_posts = [p for p in new_posts if is_relevant(p, high_value_subs, relevance_kw)]
    print(f"  Relevant new posts: {len(new_posts)}")

    # Classify priority
    for p in new_posts:
        p["_priority"] = classify_priority(p, brand_aliases, competitor_names, geographic)

    # Sort by priority then engagement
    priority_order = {"URGENT": 0, "HIGH": 1, "MEDIUM": 2}
    new_posts.sort(key=lambda x: (priority_order.get(x.get("_priority", "MEDIUM"), 2),
                                   -(x["score"] + x["num_comments"])))

    # Fetch comments for high-engagement posts
    posts_with_comments = {}
    brand_findings = {}
    comment_worthy = [p for p in new_posts if p["num_comments"] > min_comments]
    print(f"\n  Fetching comments for {len(comment_worthy)} high-engagement posts...")

    for i, post in enumerate(comment_worthy[:max_comments]):
        print(f"  [{i+1}/{min(len(comment_worthy), max_comments)}] {post['title'][:55]}...")
        comments = api.fetch_comments_for_post(post["id"], post["subreddit"], user_agent, rate_delay)
        posts_with_comments[post["id"]] = comments

        # Re-classify with comment context
        post["_priority"] = classify_priority(post, brand_aliases, competitor_names, geographic, comments)

        # Scan for brand mentions
        findings = scan_comments_for_brands(comments, brand_aliases, competitor_names)
        if findings:
            brand_findings[post["id"]] = findings
            print(f"    -> {len(findings)} brand mention(s) found!")

    # Generate report
    report = generate_report(new_posts, posts_with_comments, brand_findings, mode, run_time, brand_name)

    # Write reports
    os.makedirs(reports_dir, exist_ok=True)
    date_file = os.path.join(reports_dir, f"{run_time.strftime('%Y-%m-%d')}.md")
    latest_file = os.path.join(reports_dir, "latest.md")

    with open(date_file, "a") as f:
        if os.path.getsize(date_file) > 0:
            f.write("\n\n---\n\n")
        f.write(report)

    with open(latest_file, "w") as f:
        f.write(report)

    print(f"\n  Report written to: {date_file}")
    print(f"  Latest report at:  {latest_file}")

    # Update state
    for p in all_posts:
        seen_ids.add(p["id"])
    st["seen_post_ids"] = list(seen_ids)
    st["last_run"] = run_time.isoformat()
    state.trim_seen_ids(st, max_seen)
    state.save_state(st, state_file)
    print(f"  State saved ({len(st['seen_post_ids'])} total seen posts)")

    # Summary
    has_urgent = any(p.get("_priority") == "URGENT" for p in new_posts)
    urgent_count = sum(1 for p in new_posts if p.get("_priority") == "URGENT")
    high_count = sum(1 for p in new_posts if p.get("_priority") == "HIGH")

    summary = {
        "new_post_count": len(new_posts),
        "has_urgent": has_urgent,
        "urgent_count": urgent_count,
        "high_count": high_count,
        "run_mode": mode,
        "timestamp": run_time.isoformat(),
        "_posts": new_posts,
        "_posts_with_comments": posts_with_comments,
    }

    # Write summary for GitHub Actions
    summary_file = os.path.join(data_dir, "last_run_summary.json")
    with open(summary_file, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n{'='*60}")
    print(f"  DONE — {len(new_posts)} new relevant posts")
    if urgent_count:
        print(f"  *** {urgent_count} URGENT ({brand_name} mentions) ***")
    if high_count:
        print(f"  {high_count} HIGH priority posts")
    print(f"{'='*60}")

    return summary
