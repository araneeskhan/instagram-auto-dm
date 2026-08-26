"""
Fetches your PAGE_ACCESS_TOKEN and IG_USER_ID and writes them into .env.

Why this script exists
----------------------
The token the Graph API Explorer hands you is *short-lived* — it dies in
about an hour. If you paste that into .env your bot works for one hour and
then mysteriously stops. You actually need a Page access token derived from
a long-lived user token, which does not expire.

That exchange is three chained API calls and it's where most people get
stuck. This script does all three, finds the Instagram account linked to
your Page, and writes the results to .env for you.

Usage
-----
    python get_credentials.py

It asks for three things, all from your Meta app dashboard:
  1. App ID          (Settings > Basic)
  2. App Secret      (Settings > Basic, click "Show")
  3. A short-lived user token from the Graph API Explorer
"""
import sys
from pathlib import Path

import requests

API = "https://graph.facebook.com/v21.0"
ENV_PATH = Path(__file__).parent / ".env"

NEEDED_SCOPES = [
    "instagram_basic",
    "instagram_manage_messages",
    "instagram_manage_comments",
    "pages_show_list",
    "pages_manage_metadata",
    "pages_read_engagement",
    "business_management",
]


def die(msg: str, hint: str = ""):
    print(f"\n  ERROR: {msg}")
    if hint:
        print(f"  -> {hint}")
    sys.exit(1)


def call(path: str, params: dict, what: str) -> dict:
    r = requests.get(f"{API}/{path}", params=params, timeout=20)
    data = r.json()
    if "error" in data:
        err = data["error"]
        die(f"{what} failed: {err.get('message')}",
            "Your token may have expired (they last ~1 hour) — grab a fresh "
            "one from the Graph API Explorer and run this again.")
    return data


def main():
    print(__doc__)
    print("-" * 62)

    app_id = input("  App ID: ").strip()
    app_secret = input("  App Secret: ").strip()
    short_token = input("  Short-lived user token: ").strip()

    if not (app_id and app_secret and short_token):
        die("All three values are required.")

    # 1. short-lived user token -> long-lived user token (~60 days)
    print("\n  [1/4] Exchanging for a long-lived token...")
    long_token = call("oauth/access_token", {
        "grant_type": "fb_exchange_token",
        "client_id": app_id,
        "client_secret": app_secret,
        "fb_exchange_token": short_token,
    }, "Token exchange")["access_token"]
    print("        done.")

    # 2. list the Pages this user manages. Page tokens derived from a
    #    long-lived user token do not expire.
    print("  [2/4] Finding your Facebook Pages...")
    pages = call("me/accounts", {"access_token": long_token}, "Listing Pages").get("data", [])
    if not pages:
        die("No Facebook Pages found on this account.",
            "Your Instagram must be linked to a Facebook Page you manage. "
            "Also check you granted the pages_show_list and business_management "
            "permissions when creating the token.")
    print(f"        found {len(pages)} page(s).")

    # 3. find which Page has an Instagram professional account attached
    print("  [3/4] Looking for a linked Instagram account...")
    matches = []
    for page in pages:
        info = call(page["id"], {
            "fields": "name,instagram_business_account",
            "access_token": page["access_token"],
        }, f"Reading page {page.get('name')}")
        ig = info.get("instagram_business_account")
        if ig:
            matches.append((info.get("name"), page["access_token"], ig["id"]))

    if not matches:
        die("None of your Pages have an Instagram professional account linked.",
            "In the Facebook Page settings go to Linked Accounts and connect "
            "your Instagram. The Instagram account must be Business or Creator, "
            "not personal.")

    if len(matches) > 1:
        print("\n  Multiple linked accounts found:")
        for i, (name, _, ig_id) in enumerate(matches, 1):
            print(f"    {i}. {name}  (IG ID {ig_id})")
        choice = int(input("  Which one? ").strip() or "1") - 1
    else:
        choice = 0

    page_name, page_token, ig_id = matches[choice]
    print(f"        using: {page_name}")

    # 4. write into .env
    print("  [4/4] Writing to .env...")
    if not ENV_PATH.exists():
        die(".env not found next to this script.",
            "Copy .env.example to .env first.")

    lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
    updates = {
        "PAGE_ACCESS_TOKEN": page_token,
        "IG_USER_ID": ig_id,
        "APP_SECRET": app_secret,
    }
    seen = set()
    out = []
    for line in lines:
        key = line.split("=", 1)[0].strip() if "=" in line else None
        if key in updates:
            out.append(f"{key}={updates[key]}")
            seen.add(key)
        else:
            out.append(line)
    for key, value in updates.items():
        if key not in seen:
            out.append(f"{key}={value}")

    ENV_PATH.write_text("\n".join(out) + "\n", encoding="utf-8")

    print("        done.\n")
    print("-" * 62)
    print(f"  Page:         {page_name}")
    print(f"  IG_USER_ID:   {ig_id}")
    print(f"  Page token:   {page_token[:18]}... (written to .env)")
    print("-" * 62)
    print("\n  Your .env is ready. Start the bot with:  python app.py\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n  Cancelled.")
