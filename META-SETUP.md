# Getting your Meta credentials

Roughly 30 minutes. It's all dashboard clicking — no coding. The only
genuinely confusing part (the token exchange) is automated by
`get_credentials.py` at the end.

You need three values:

| Value | What it is |
|---|---|
| `PAGE_ACCESS_TOKEN` | Proves your bot is allowed to act as your account |
| `IG_USER_ID` | Which Instagram account it acts as |
| `APP_SECRET` | Used to verify webhooks really came from Meta |

---

## Part 1 — Instagram must be a Professional account

In the Instagram app: **Settings > Account type and tools > Switch to
professional account**. Choose Business or Creator.

Personal accounts cannot use the API at all. This is not optional.

---

## Part 2 — Link it to a Facebook Page

The Instagram API works *through* a Facebook Page. You need one, even if
you never post on it.

- If you don't have a Page: create one at facebook.com/pages/create
  (a name and a category is enough)
- Link it: Instagram app > **Settings > Business tools and controls >
  Connect or create** > connect your Facebook Page

To verify it worked: on the Facebook Page, go to **Settings > Linked
accounts** and confirm your Instagram shows there.

**This is the step people get wrong.** If the link isn't right,
`get_credentials.py` will tell you no linked Instagram was found.

---

## Part 3 — Create the Meta app

1. Go to https://developers.facebook.com/apps
2. You may be asked to register as a developer — accept, it's free
3. **Create app**
4. Use case: choose **Other**, then app type **Business**
5. Name it whatever you like ("my instagram bot"), pick your email
6. If asked for a Business Portfolio, create one or pick the existing one

Now add the API:

7. On the app dashboard find **Instagram** and click **Set up**
8. Also add **Webhooks** from the product list

---

## Part 4 — Grab your App ID and Secret

**Settings > Basic** in the left sidebar.

- **App ID** — visible at the top
- **App Secret** — click **Show**, enter your Facebook password

Keep these two handy for the next part. The App Secret is a password —
don't paste it into a screenshot or a public repo.

---

## Part 5 — Generate a token

1. Go to https://developers.facebook.com/tools/explorer
2. Top right: pick **your app** from the dropdown
3. Below that, "User or Page" -> **User token**
4. Click **Add a Permission** and tick all of these:

   - `instagram_basic`
   - `instagram_manage_messages`
   - `instagram_manage_comments`
   - `pages_show_list`
   - `pages_manage_metadata`
   - `pages_read_engagement`
   - `business_management`

5. Click **Generate Access Token**, log in, and allow everything it asks
6. Copy the long string it produces

**This token dies in about an hour.** That is normal and expected — the
next step converts it into a permanent one. Don't paste it into `.env`
yourself; if you do, your bot will work for an hour and then quietly stop,
which is a horrible bug to debug.

---

## Part 6 — Run the helper

In your terminal, in this folder, with the venv active:

```powershell
python get_credentials.py
```

Paste in your App ID, App Secret, and that short-lived token when asked.

It will:

1. Exchange your 1-hour token for a long-lived one
2. Find your Facebook Pages
3. Work out which one has Instagram linked
4. Write `PAGE_ACCESS_TOKEN`, `IG_USER_ID` and `APP_SECRET` into `.env`

Your other settings (admin password, verify token) are preserved.

---

## What's next

At this point your `.env` is complete and the bot can talk to Instagram.
The remaining piece is giving Instagram a public URL to send comments to —
that's `DEPLOY.md`.

---

## If something goes wrong

**"No Facebook Pages found"**
You didn't grant `pages_show_list` / `business_management` when generating
the token. Go back to Part 5 and tick them all.

**"None of your Pages have an Instagram professional account linked"**
Part 2 didn't take. Check Facebook Page > Settings > Linked accounts.

**"Token exchange failed" / "session has expired"**
Your short-lived token ran out. Generate a fresh one (Part 5) and re-run.

**Bot works for an hour then stops**
You pasted the short-lived token into `.env` by hand instead of running
`get_credentials.py`. Run the helper.
