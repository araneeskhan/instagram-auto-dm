"""
Prints your recent Instagram posts with their media IDs.

You need the media ID to attach keyword rules to a *specific* post in
rules.json. Run:

    python list_posts.py

...then copy the ID of the post you want and paste it as a key under
"posts" in rules.json.
"""
import sys
import textwrap

import requests

from config import Config


def fetch_media(limit: int = 25) -> list:
    url = f"{Config.GRAPH_API_BASE}/{Config.IG_USER_ID}/media"
    params = {
        "fields": "id,caption,permalink,timestamp,media_type",
        "limit": limit,
        "access_token": Config.PAGE_ACCESS_TOKEN,
    }
    resp = requests.get(url, params=params, timeout=15)
    if resp.status_code >= 400:
        print(f"Graph API error {resp.status_code}: {resp.text}", file=sys.stderr)
        sys.exit(1)
    return resp.json().get("data", [])


def main():
    Config.validate()
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 25
    posts = fetch_media(limit)

    if not posts:
        print("No posts found. Check that IG_USER_ID and PAGE_ACCESS_TOKEN are correct.")
        return

    print(f"\nFound {len(posts)} post(s). Copy an ID into the \"posts\" section of rules.json.\n")
    for post in posts:
        caption = (post.get("caption") or "(no caption)").replace("\n", " ")
        caption = textwrap.shorten(caption, width=70, placeholder="...")
        print(f'  "{post["id"]}"')
        print(f"      {post.get('media_type', '?'):<14} {post.get('timestamp', '')}")
        print(f"      {caption}")
        print(f"      {post.get('permalink', '')}")
        print()


if __name__ == "__main__":
    main()
