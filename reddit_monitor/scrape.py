"""One-shot Reddit scraper for deep research/baseline data collection."""

import json
import os
from . import api


def run_scrape(cfg):
    """Run the one-shot scraper. Returns a summary dict."""
    settings = cfg.get("settings", {})
    user_agent = settings.get("user_agent", "reddit-monitor/1.0")
    rate_delay = settings.get("rate_delay", 2)
    max_results = settings.get("max_results_per_query", 25)

    # Paths
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, "data")
    os.makedirs(data_dir, exist_ok=True)

    scrape_queries = cfg["queries"].get("scrape", [])
    if not scrape_queries:
        print("No scrape queries found in config.")
        return {"total_posts": 0, "queries_run": 0}

    # Group queries by label prefix for organized output
    groups = {}
    for q in scrape_queries:
        # Determine group from label prefix (e.g., "rise_general" -> "rise")
        prefix = q["label"].split("_")[0] if "_" in q["label"] else q["label"]
        groups.setdefault(prefix, []).append(q)

    all_results = {}
    all_posts_seen = set()

    for group_name, queries in groups.items():
        print(f"\n{'='*60}")
        print(f"  GROUP: {group_name.upper()}")
        print(f"{'='*60}")
        group_posts = []

        for q in queries:
            posts = api.run_search(
                q["label"], q["query"], q.get("subreddit"),
                time_filter="year", user_agent=user_agent,
                rate_delay=rate_delay, max_results=max_results,
            )
            # Retry with "all" if no results
            if not posts:
                posts = api.run_search(
                    f"{q['label']}_alltime", q["query"], q.get("subreddit"),
                    time_filter="all", user_agent=user_agent,
                    rate_delay=rate_delay, max_results=max_results,
                )

            new_posts = []
            for p in posts:
                if p["id"] not in all_posts_seen:
                    all_posts_seen.add(p["id"])
                    new_posts.append(p)
            group_posts.extend(new_posts)

        all_results[group_name] = group_posts
        print(f"\n  Total unique posts for {group_name}: {len(group_posts)}")

    # Fetch comments for top posts by engagement
    print(f"\n{'='*60}")
    print(f"  FETCHING COMMENTS FOR TOP POSTS")
    print(f"{'='*60}")

    all_posts = []
    for group_name, posts in all_results.items():
        for p in posts:
            p["_group"] = group_name
            all_posts.append(p)

    all_posts.sort(key=lambda x: x["num_comments"] + x["score"], reverse=True)

    posts_with_comments = {}
    fetch_count = min(30, len(all_posts))
    for i, post in enumerate(all_posts[:fetch_count]):
        print(f"  [{i+1}/{fetch_count}] Fetching comments for: {post['title'][:60]}...")
        comments = api.fetch_comments_for_post(post["id"], post["subreddit"], user_agent, rate_delay)
        posts_with_comments[post["id"]] = {
            "post": post,
            "comments": comments,
        }
        print(f"    -> {len(comments)} comments fetched")

    # Save raw JSON
    output = {
        "search_results": all_results,
        "posts_with_comments": posts_with_comments,
        "metadata": {
            "total_unique_posts": len(all_posts_seen),
            "total_posts_with_comments": len(posts_with_comments),
            "queries_run": len(scrape_queries),
        }
    }

    output_file = os.path.join(data_dir, "reddit_raw_data.json")
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n  Raw data saved to: {output_file}")

    # Save human-readable summary
    summary_file = os.path.join(data_dir, "reddit_summary.txt")
    with open(summary_file, "w") as f:
        f.write("REDDIT BRAND INTELLIGENCE - RAW DATA SUMMARY\n")
        f.write("=" * 60 + "\n\n")

        for group_name, posts in all_results.items():
            f.write(f"\n{'='*60}\n")
            f.write(f"GROUP: {group_name.upper()} ({len(posts)} unique posts)\n")
            f.write(f"{'='*60}\n\n")

            for p in sorted(posts, key=lambda x: x["score"], reverse=True):
                f.write(f"[{p['score']}↑ | {p['num_comments']} comments] r/{p['subreddit']}\n")
                f.write(f"  Title: {p['title']}\n")
                f.write(f"  Author: u/{p['author']}\n")
                f.write(f"  URL: {p['url']}\n")
                if p["selftext"]:
                    text = p["selftext"][:300].replace("\n", "\n    ")
                    f.write(f"  Text: {text}\n")
                f.write("\n")

                if p["id"] in posts_with_comments:
                    for c in posts_with_comments[p["id"]]["comments"][:10]:
                        body = c["body"][:200].replace("\n", "\n      ")
                        f.write(f"    [{c['score']}↑] u/{c['author']}: {body}\n")
                    f.write("\n")

    print(f"  Summary saved to: {summary_file}")
    print(f"\n  DONE! Total unique posts collected: {len(all_posts_seen)}")

    return {
        "total_posts": len(all_posts_seen),
        "posts_with_comments": len(posts_with_comments),
        "queries_run": len(scrape_queries),
    }
