# okara-reddit-reader

A tiny **read-only** personal research script for the Reddit Data API.

I'm an independent creator (@okara.talks on Instagram/TikTok) making short educational videos in Ukrainian about technology, business and venture capital. This script helps me see how Reddit communities discuss tech and business news, and which problems small businesses and professionals talk about.

## What it does
- `top <subreddit>`: top posts of a public subreddit (day/week)
- `search "<query>"`: keyword search
- `comments <post>`: top comments of a single post

Output is printed to the terminal as JSON and summarized into my private research notes.

## What it does NOT do
- No posting, commenting, voting or messaging (application-only OAuth, read-only).
- No bulk downloading, archiving or reselling of Reddit content.
- No training of AI/ML models on Reddit data.
- No collecting or profiling of individual users.

## Volume
About 50–150 requests per day from one script-type OAuth client, well under Reddit's rate limits.

## Setup
```
cp .env.example .env   # add REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT
python3 reddit.py top startups --t day --limit 15
```
Python 3 standard library only, no dependencies.
