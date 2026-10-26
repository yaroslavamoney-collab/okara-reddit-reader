#!/usr/bin/env python3
"""Read-only access to Reddit through the official OAuth API.

Credentials come from .env next to this script (never commit it):
    REDDIT_CLIENT_ID=...
    REDDIT_CLIENT_SECRET=...
    REDDIT_USER_AGENT=okara-research/0.1 by u/<your_username>

Usage:
    python3 reddit.py top <subreddit> [--t day|week|month] [--limit N]
    python3 reddit.py search "<query>" [--sub <subreddit>] [--t week] [--limit N]
    python3 reddit.py comments <post_url_or_id> [--limit N]

Without credentials it prints NO_CREDENTIALS and exits with code 3,
so agents know to fall back to web search.
"""
import argparse
import base64
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import ssl

# macOS python.org builds ship without CA certs; use the system bundle.
SSL_CTX = ssl.create_default_context(cafile="/etc/ssl/cert.pem") if __import__("os").path.exists("/etc/ssl/cert.pem") else ssl.create_default_context()
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOKEN_CACHE = ROOT / ".cache" / "reddit_token.json"


def load_env():
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def get_token(cid, secret, ua):
    if TOKEN_CACHE.exists():
        data = json.loads(TOKEN_CACHE.read_text())
        if data.get("expires_at", 0) > time.time() + 60:
            return data["access_token"]
    auth = base64.b64encode(f"{cid}:{secret}".encode()).decode()
    req = urllib.request.Request(
        "https://www.reddit.com/api/v1/access_token",
        data=b"grant_type=client_credentials",
        headers={"Authorization": f"Basic {auth}", "User-Agent": ua},
    )
    with urllib.request.urlopen(req, timeout=20, context=SSL_CTX) as r:
        data = json.load(r)
    data["expires_at"] = time.time() + data.get("expires_in", 3600)
    TOKEN_CACHE.parent.mkdir(exist_ok=True)
    TOKEN_CACHE.write_text(json.dumps(data))
    return data["access_token"]


def api(path, params, token, ua):
    url = "https://oauth.reddit.com" + path + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Authorization": f"bearer {token}", "User-Agent": ua})
    with urllib.request.urlopen(req, timeout=30, context=SSL_CTX) as r:
        return json.load(r)


def fmt_post(p):
    d = p["data"]
    body = (d.get("selftext") or "").strip().replace("\n", " ")
    return {
        "title": d.get("title"),
        "subreddit": d.get("subreddit"),
        "score": d.get("score"),
        "comments": d.get("num_comments"),
        "created_utc": time.strftime("%Y-%m-%d %H:%M", time.gmtime(d.get("created_utc", 0))),
        "url": "https://www.reddit.com" + d.get("permalink", ""),
        "link": d.get("url") if not d.get("is_self") else None,
        "text": body[:600],
    }


def post_id(s):
    m = re.search(r"comments/([a-z0-9]+)", s)
    return m.group(1) if m else s


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    t = sp.add_parser("top"); t.add_argument("sub"); t.add_argument("--t", default="day"); t.add_argument("--limit", type=int, default=15)
    s = sp.add_parser("search"); s.add_argument("q"); s.add_argument("--sub"); s.add_argument("--t", default="week"); s.add_argument("--limit", type=int, default=10)
    c = sp.add_parser("comments"); c.add_argument("post"); c.add_argument("--limit", type=int, default=30)
    a = ap.parse_args()

    load_env()
    cid, secret = os.environ.get("REDDIT_CLIENT_ID"), os.environ.get("REDDIT_CLIENT_SECRET")
    ua = os.environ.get("REDDIT_USER_AGENT", "okara-research/0.1")
    if not cid or not secret:
        print("NO_CREDENTIALS: Reddit API keys are not set in .env. Fall back to WebSearch with site:reddit.com.")
        sys.exit(3)
    token = get_token(cid, secret, ua)

    if a.cmd == "top":
        data = api(f"/r/{a.sub}/top", {"t": a.t, "limit": a.limit}, token, ua)
        out = [fmt_post(p) for p in data["data"]["children"]]
    elif a.cmd == "search":
        path = f"/r/{a.sub}/search" if a.sub else "/search"
        params = {"q": a.q, "t": a.t, "limit": a.limit, "sort": "relevance"}
        if a.sub:
            params["restrict_sr"] = "on"
        data = api(path, params, token, ua)
        out = [fmt_post(p) for p in data["data"]["children"]]
    else:
        data = api(f"/comments/{post_id(a.post)}", {"limit": a.limit, "sort": "top", "depth": 2}, token, ua)
        post = fmt_post(data[0]["data"]["children"][0])
        comments = []
        for ch in data[1]["data"]["children"]:
            if ch["kind"] != "t1":
                continue
            d = ch["data"]
            comments.append({
                "score": d.get("score"),
                "text": (d.get("body") or "")[:500],
                "url": "https://www.reddit.com" + d.get("permalink", ""),
            })
        out = {"post": post, "top_comments": comments}
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
