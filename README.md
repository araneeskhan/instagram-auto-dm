# Instagram Comment & DM Auto-Reply Bot

Auto-replies to Instagram comments and DMs using **Meta's official Instagram
Graph API** — no Selenium, no scraping, no unofficial endpoints that risk a
ban. This is the same mechanism used by tools like ManyChat/Chatfuel under
the hood.

## What it does

- Someone comments a trigger word (e.g. "price") on your post → the bot
  posts a public reply and/or sends them a **private DM** (Meta's official
  "Private Replies" feature).
- Someone DMs your account with a trigger word (e.g. "hi", "hours") → the
  bot auto-replies in the DM thread.
- All rules live in `rules.json` — edit that file, no code changes needed.

## Requirements (Meta side, one-time setup)

1. **Instagram account** must be a **Professional account** (Business or
   Creator) — personal accounts cannot use the API.
2. That Instagram account must be **linked to a Facebook Page** you manage.
3. A **Meta Developer app**: create one at https://developers.facebook.com/apps
   → type "Business".
4. Add the **Instagram** product to the app, and generate a
   **Page Access Token** with these permissions:
   - `instagram_basic`
   - `instagram_manage_messages`
   - `instagram_manage_comments`
   - `pages_messaging`
   - `pages_show_list`
   For a real (non-test) app these require **App Review** from Meta before
   they work for anyone other than admins/testers on the app — budget a
   few days for that if you're launching for real.
5. Note your **App Secret** (App Dashboard → Settings → Basic).
6. Note your Instagram account's **IGSID** — you can get it with:
   ```
   GET https://graph.facebook.com/v21.0/me?fields=id&access_token=PAGE_ACCESS_TOKEN
   ```

## Local setup

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # then fill in your real values
```

## Running it

```bash
python app.py
```

This starts a Flask server on `http://localhost:5000`. Meta needs to reach
it over the public internet, so for local testing tunnel it, e.g.:

```bash
ngrok http 5000
```

Take the `https://xxxx.ngrok-free.app` URL ngrok gives you.

## Registering the webhook with Meta

1. App Dashboard → your app → **Webhooks** → choose the **Instagram**
   object.
2. Callback URL: `https://xxxx.ngrok-free.app/webhook`
3. Verify Token: whatever you set as `VERIFY_TOKEN` in `.env`.
4. Click **Verify and Save** — this triggers a GET request your `app.py`
   answers automatically.
5. Subscribe to the `comments` and `messages` fields.

From this point on, comments and DMs on your connected Instagram account
will hit your `/webhook` endpoint in real time.

## Customizing replies

Edit `rules.json`. A rule block looks like:

```json
{
  "keywords": ["price", "cost"],
  "public_reply": "Thanks for asking! Check your DMs 👀",
  "private_reply": "Here's our pricing: https://example.com/pricing"
}
```

Add as many blocks as you want to `comment_rules` / `dm_rules`; the first
keyword match wins. `comment_default` / `dm_default` fire when nothing
matches. Set `public_reply` to `null` to DM only (no visible comment).

Keywords match on **whole words**, so `"price"` does not fire on
"surprise". Multi-word keywords like `"how much"` match as a phrase.

## Per-post rules (specific keyword → specific DM on one post)

**Step 1 — find the post's media ID:**

```bash
python list_posts.py
```

This prints your recent posts with their IDs, captions and links.

**Step 2 — add that ID under `posts` in `rules.json`:**

```json
"posts": {
  "17895695668004550": {
    "_label": "Summer sale reel",
    "comment_rules": [
      {
        "keywords": ["sale", "discount", "code"],
        "public_reply": "Sent you the code in your DMs! 💌",
        "private_reply": "Here's your 20% off code: SUMMER20"
      }
    ],
    "comment_default": {
      "public_reply": null,
      "private_reply": "Thanks for commenting on our sale post!"
    }
  }
}
```

Now "discount" on *that* post sends the code, while "discount" anywhere
else falls through to your global rules.

**Order of resolution for a comment:**

1. That post's `comment_rules`
2. Global `comment_rules`
3. That post's `comment_default`
4. Global `comment_default`

Add `"ignore_global": true` to a post to skip steps 2 and 4 — useful for a
giveaway post where you want *only* the giveaway reply to fire and
everything else to stay silent.

DMs aren't attached to a post, so `dm_rules` are always global.

## Important limits to know (this is what keeps you within Meta's rules)

- **24-hour messaging window**: you can only free-form message a user
  within 24 hours of their last message to you, *unless* the message
  qualifies for an approved message tag, or is sent as a **Private Reply**
  to a comment (private replies have their own separate 7-day window and
  don't count against the 24-hour rule).
- **No cold outbound / bulk DMs** to people who haven't messaged you —
  the API will reject it, and doing it anyway is exactly the kind of
  abuse Meta's automation policy targets.
- **Rate limits** apply per Page/app — see Meta's Platform Rate Limits
  docs if you scale this up.
- Test users/admins on the app can use it immediately; anyone else needs
  your app to pass **App Review** for the `instagram_manage_messages` /
  `instagram_manage_comments` permissions.

## Deploying for real

For anything beyond local testing, run `app.py` behind a real HTTPS
endpoint (e.g. on a small VPS, Render, Railway, Fly.io) instead of ngrok,
point the webhook URL at that, and keep `.env` out of version control
(already handled by `.gitignore`).

## File structure

```
instagram-dm-bot/
├── app.py             # Flask webhook server (GET verify + POST events)
├── graph_api.py       # Graph API client: send DM, private reply, comment reply, signature check
├── handlers.py        # Turns webhook payloads into actions using rules.json
├── rules.json         # Your keyword → reply rules, global + per-post (edit this)
├── list_posts.py      # Prints your posts' media IDs for the per-post rules
├── config.py          # Loads settings from .env
├── requirements.txt
├── .env.example
└── .gitignore
```
