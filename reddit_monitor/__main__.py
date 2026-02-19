"""CLI entry point for reddit_monitor."""

import argparse
import sys

from .config import load_config
from .monitor import run_monitor
from .scrape import run_scrape
from .analyze import run_analysis


def main():
    parser = argparse.ArgumentParser(
        prog="reddit-monitor",
        description="Reddit brand monitoring tool — monitor Reddit for brand mentions, "
                    "competitor activity, and industry discussions.",
    )
    parser.add_argument(
        "--config", default=None,
        help="Path to config.toml (default: config.toml in project root)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # monitor subcommand
    monitor_parser = subparsers.add_parser("monitor", help="Run incremental monitoring")
    mode_group = monitor_parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument("--daily", action="store_const", const="daily", dest="mode",
                           help="Run daily high-priority queries")
    mode_group.add_argument("--weekly", action="store_const", const="weekly", dest="mode",
                           help="Run all queries (daily + weekly)")
    mode_group.add_argument("--all", action="store_const", const="all", dest="mode",
                           help="Same as --weekly")
    monitor_parser.add_argument("--analyze", action="store_true",
                               help="Run AI analysis after monitoring (requires ANTHROPIC_API_KEY)")

    # scrape subcommand
    scrape_parser = subparsers.add_parser("scrape", help="Run one-shot deep scraper for baseline data")
    scrape_parser.add_argument("--analyze", action="store_true",
                              help="Run AI analysis after scraping (requires ANTHROPIC_API_KEY)")

    # analyze subcommand (standalone — re-analyze latest data)
    subparsers.add_parser("analyze", help="Re-run AI analysis on the most recent monitoring data")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Load config
    cfg = load_config(args.config)

    if args.command == "monitor":
        summary = run_monitor(cfg, mode=args.mode)
        if summary["new_post_count"] == 0:
            print("\nNo new posts — inbox zero!")
        elif args.analyze:
            print(f"\n{'='*60}")
            print("  Running AI analysis...")
            print(f"{'='*60}")
            posts = summary.get("_posts", [])
            comments = summary.get("_posts_with_comments", {})
            run_analysis(cfg, posts, comments)

    elif args.command == "scrape":
        summary = run_scrape(cfg)
        print(f"\nScrape complete: {summary['total_posts']} posts collected")
        if args.analyze and summary.get("_posts"):
            print(f"\n{'='*60}")
            print("  Running AI analysis...")
            print(f"{'='*60}")
            run_analysis(cfg, summary["_posts"], summary.get("_posts_with_comments", {}))

    elif args.command == "analyze":
        # Re-analyze from saved data
        import json
        import os
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        raw_file = os.path.join(base_dir, "data", "reddit_raw_data.json")
        if not os.path.exists(raw_file):
            print("No data to analyze. Run 'monitor' or 'scrape' first.")
            sys.exit(1)
        with open(raw_file) as f:
            raw = json.load(f)
        # Flatten posts from search results
        all_posts = []
        for group_posts in raw.get("search_results", {}).values():
            all_posts.extend(group_posts)
        comments = {}
        for pid, data in raw.get("posts_with_comments", {}).items():
            if isinstance(data, dict) and "comments" in data:
                comments[pid] = data["comments"]
            elif isinstance(data, list):
                comments[pid] = data
        run_analysis(cfg, all_posts, comments)


if __name__ == "__main__":
    main()
