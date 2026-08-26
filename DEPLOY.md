# Deploying free on Google Cloud Run

Cloud Run's free tier is **Always Free** (no end date) and includes:

- 2,000,000 requests / month
- 180,000 vCPU-seconds and 360,000 GiB-seconds / month
- 1 GB outbound data / month

Your bot sends tiny JSON payloads, so you will not come close to any of
these. Unlike Vercel's Hobby plan, Cloud Run has no non-commercial
restriction.

You do need a Google Cloud account with billing enabled (a card on file),
even though the free tier costs nothing. Set a budget alert of $1 if you
want a safety net.

## One-time setup

1. Install the gcloud CLI: https://cloud.google.com/sdk/docs/install
2. Log in and pick a project:

   ```bash
   gcloud auth login
   gcloud projects create ig-dm-bot-<something-unique>
   gcloud config set project ig-dm-bot-<something-unique>
   ```

3. Enable billing on that project in the Cloud console (required even for
   the free tier), then enable the services:

   ```bash
   gcloud services enable run.googleapis.com cloudbuild.googleapis.com
   ```

## Deploy

From this folder:

```bash
gcloud run deploy instagram-dm-bot \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "PAGE_ACCESS_TOKEN=xxx,IG_USER_ID=xxx,APP_SECRET=xxx,VERIFY_TOKEN=xxx"
```

That builds the Dockerfile, pushes it, and returns a public HTTPS URL like
`https://instagram-dm-bot-abc123-uc.a.run.app`.

Your webhook callback URL is that URL + `/webhook`.

Better than `--set-env-vars` for secrets: store them in Secret Manager and
reference them with `--set-secrets`, so tokens are not visible in your
deploy history.

## Point Meta at it

In the Meta App Dashboard > Webhooks > Instagram:

- Callback URL: `https://<your-cloud-run-url>/webhook`
- Verify Token: whatever you set as `VERIFY_TOKEN`

Then subscribe to the `comments` and `messages` fields.

## Cold starts

Cloud Run scales to zero when idle, so the first request after a quiet
period takes roughly 1-3 seconds to boot the container. Meta tolerates
this fine. This is very different from free tiers that *sleep* and take
~50 seconds to wake, which is what gets webhooks disabled.

If you want zero cold starts, set `--min-instances=1`, but note that this
runs continuously and will exceed the free tier.

## Updating your reply rules

The container filesystem is ephemeral, so `rules.json` ships inside the
image. To change your replies, edit `rules.json` and redeploy:

```bash
gcloud run deploy instagram-dm-bot --source . --region us-central1
```

If you later add a frontend that edits rules from a web page, the rules
must move out of the file and into storage (Firestore's free tier or a
free Postgres like Neon) — a serverless container cannot persist writes to
its own filesystem.

## Alternative: a real always-on VM, also free

Oracle Cloud's Always Free tier still includes 2 AMD micro instances
(1/8 OCPU, 1 GB RAM each) plus 200 GB storage, with no time limit. That is
enough for this bot and has no cold starts at all. Note Oracle halved the
ARM/Ampere allocation in 2026 (4 OCPU/24GB down to 2 OCPU/12GB), and ARM
capacity is often unavailable in popular regions — the AMD micro instances
are the reliable part. It is more setup than Cloud Run (you manage the OS,
nginx/caddy, TLS and a systemd service yourself).
