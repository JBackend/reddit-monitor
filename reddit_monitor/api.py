"""Shared Reddit API functions."""

import json
import urllib.request
import urllib.parse
import time


def fetch_reddit(url, label="", user_agent="Mozilla/5.0", rate_delay=2):
    """Fetch a Reddit JSON endpoint with rate limiting."""
    headers = {
        "User-Agent": user_agent,
        "Accept": "application/json",
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        time.sleep(rate_delay)
        return data
    except Exception as e:
        print(f"  [ERROR] {label}: {e}")
        return None


def extract_posts(data):
    """Extract post details from Reddit JSON response."""
    if not data or "data" not in data:
        return []
    posts = []
    for child in data["data"].get("children", []):
        d = child.get("data", {})
        posts.append({
            "title": d.get("title", ""),
            "subreddit": d.get("subreddit", ""),
            "author": d.get("author", ""),
            "score": d.get("score", 0),
            "num_comments": d.get("num_comments", 0),
            "created_utc": d.get("created_utc", 0),
            "selftext": (d.get("selftext", "") or "")[:1000],
            "url": f"https://reddit.com{d.get('permalink', '')}",
            "permalink": d.get("permalink", ""),
            "id": d.get("id", ""),
        })
    return posts


def fetch_comments_for_post(post_id, subreddit, user_agent="Mozilla/5.0", rate_delay=2):
    """Fetch comments for a specific post."""
    url = f"https://old.reddit.com/r/{subreddit}/comments/{post_id}.json?limit=50"
    data = fetch_reddit(url, f"comments for {post_id}", user_agent, rate_delay)
    if not data or not isinstance(data, list) or len(data) < 2:
        return []
    comments = []

    def walk_comments(node):
        if isinstance(node, dict):
            kind = node.get("kind")
            if kind == "t1":
                cd = node.get("data", {})
                comments.append({
                    "author": cd.get("author", ""),
                    "body": (cd.get("body", "") or "")[:1000],
                    "score": cd.get("score", 0),
                    "id": cd.get("id", ""),
                })
                replies = cd.get("replies")
                if isinstance(replies, dict):
                    for child in replies.get("data", {}).get("children", []):
                        walk_comments(child)
            elif kind == "Listing":
                for child in node.get("data", {}).get("children", []):
                    walk_comments(child)

    walk_comments(data[1])
    return comments


def run_search(label, query, subreddit=None, time_filter="week",
               user_agent="Mozilla/5.0", rate_delay=2, max_results=25):
    """Run a single Reddit search query."""
    params = {
        "q": query,
        "sort": "new",
        "t": time_filter,
        "limit": str(max_results),
    }
    if subreddit:
        params["restrict_sr"] = "on"
        base = f"https://old.reddit.com/r/{subreddit}/search.json"
    else:
        base = "https://old.reddit.com/search.json"

    url = f"{base}?{urllib.parse.urlencode(params)}"
    print(f"  Searching: {label} ...", end=" ", flush=True)
    data = fetch_reddit(url, label, user_agent, rate_delay)
    posts = extract_posts(data)
    print(f"found {len(posts)} posts")
    return posts
