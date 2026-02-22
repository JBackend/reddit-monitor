"""Markdown report generation."""

from datetime import datetime, timezone


def generate_report(new_posts, posts_with_comments, brand_findings, run_mode, run_time, brand_name):
    """Generate a markdown report of new findings."""
    lines = []
    lines.append(f"# Reddit Monitor Report — {run_time.strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append("")

    # Date range of analyzed posts
    if new_posts:
        timestamps = [p["created_utc"] for p in new_posts if "created_utc" in p]
        if timestamps:
            earliest = datetime.fromtimestamp(min(timestamps), tz=timezone.utc)
            latest = datetime.fromtimestamp(max(timestamps), tz=timezone.utc)
            fmt = lambda dt: dt.strftime("%b %d, %Y")
            date_range = f"**Posts from: {fmt(earliest)} – {fmt(latest)} | {len(new_posts)} posts analyzed**"
        else:
            date_range = f"**{len(new_posts)} posts analyzed**"
    else:
        date_range = "**No posts found**"
    lines.append(date_range)
    lines.append("")

    lines.append(f"**Mode:** {run_mode} | **New posts found:** {len(new_posts)}")
    lines.append("")

    urgent = [p for p in new_posts if p.get("_priority") == "URGENT"]
    high = [p for p in new_posts if p.get("_priority") == "HIGH"]
    medium = [p for p in new_posts if p.get("_priority") == "MEDIUM"]

    summary_parts = []
    if urgent:
        summary_parts.append(f"**{len(urgent)} URGENT** ({brand_name} mentions)")
    summary_parts.append(f"**{len(high)} HIGH**")
    summary_parts.append(f"**{len(medium)} MEDIUM**")
    lines.append(" | ".join(summary_parts))
    lines.append("")
    lines.append("---")
    lines.append("")

    if urgent:
        lines.append(f"## URGENT — {brand_name} Mentions")
        lines.append("")
        for p in urgent:
            _write_post_block(lines, p, posts_with_comments, brand_findings)
        lines.append("---")
        lines.append("")

    if high:
        lines.append("## HIGH — Competitor / Industry")
        lines.append("")
        for p in sorted(high, key=lambda x: x["score"] + x["num_comments"], reverse=True):
            _write_post_block(lines, p, posts_with_comments, brand_findings)
        lines.append("---")
        lines.append("")

    if medium:
        lines.append("## MEDIUM — General")
        lines.append("")
        for p in sorted(medium, key=lambda x: x["score"] + x["num_comments"], reverse=True):
            _write_post_block(lines, p, posts_with_comments, brand_findings)

    # Brand mention summary from comments
    all_findings = []
    for pid, findings in brand_findings.items():
        for f in findings:
            f["_post_id"] = pid
            all_findings.append(f)

    if all_findings:
        lines.append("---")
        lines.append("")
        lines.append("## Brand Mentions in Comments")
        lines.append("")
        for f in all_findings:
            brands = ", ".join(f["rise_mentions"] + f["competitor_mentions"])
            lines.append(f"- **u/{f['author']}** ({f['score']}pts) mentioned: {brands}")
            lines.append(f"  > {f['excerpt'][:200]}")
            lines.append("")

    if not new_posts:
        lines.append("No new posts found since last run. All clear.")
        lines.append("")

    return "\n".join(lines)


def _write_post_block(lines, post, posts_with_comments, brand_findings):
    """Write a single post block into the report."""
    priority = post.get("_priority", "MEDIUM")
    lines.append(f"### [{priority}] {post['title']}")
    lines.append("")
    lines.append(f"- **Subreddit:** r/{post['subreddit']} | "
                 f"**Score:** {post['score']} | "
                 f"**Comments:** {post['num_comments']} | "
                 f"**Author:** u/{post['author']}")
    ts = datetime.fromtimestamp(post["created_utc"], tz=timezone.utc).strftime("%Y-%m-%d")
    lines.append(f"- **Posted:** {ts} | **Link:** {post['url']}")
    lines.append(f"- **Query:** {post.get('_query_label', 'unknown')}")
    lines.append("")

    if post["selftext"]:
        lines.append(f"> {post['selftext'][:400]}")
        lines.append("")

    pid = post["id"]
    if pid in posts_with_comments:
        comments = posts_with_comments[pid]
        if comments:
            lines.append("**Top comments:**")
            for c in sorted(comments, key=lambda x: x["score"], reverse=True)[:5]:
                body = c["body"][:200].replace("\n", " ")
                lines.append(f"- [{c['score']}pts] u/{c['author']}: {body}")
            lines.append("")

    if pid in brand_findings and brand_findings[pid]:
        lines.append("**Brand mentions in thread:**")
        for f in brand_findings[pid]:
            brands = ", ".join(f["rise_mentions"] + f["competitor_mentions"])
            lines.append(f"- u/{f['author']}: {brands}")
        lines.append("")

    lines.append("")
