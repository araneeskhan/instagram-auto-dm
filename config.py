"""
Configuration loader.

All secrets come from environment variables (see .env.example).
Never hardcode tokens in source files.
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Long-lived Page Access Token for the Facebook Page linked to your
    # Instagram professional (Business/Creator) account.
    PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN", "")

    # The Instagram-scoped User ID (IGSID) of *your* account, i.e. the
    # business account the bot is running for. Used to build API URLs.
    IG_USER_ID = os.environ.get("IG_USER_ID", "")

    # App Secret from Meta App Dashboard > Settings > Basic.
    # Used to verify the X-Hub-Signature-256 header on incoming webhooks.
    APP_SECRET = os.environ.get("APP_SECRET", "")

    # Arbitrary string you choose yourself and enter in the Meta Webhooks
    # product config ("Verify Token" field) when you subscribe the webhook.
    VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "")

    # Graph API version to target.
    GRAPH_API_VERSION = os.environ.get("GRAPH_API_VERSION", "v21.0")

    GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

    PORT = int(os.environ.get("PORT", "5000"))

    # --- admin UI -------------------------------------------------------
    # Password for the rules editor at /admin. If this is left empty the
    # admin UI is DISABLED entirely rather than left open to the world.
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")

    # Signs the login session cookie. Any long random string.
    SECRET_KEY = os.environ.get("SECRET_KEY", "")

    # --- rules storage --------------------------------------------------
    # "file" (local dev) or "firestore" (Cloud Run, survives restarts).
    RULES_BACKEND = os.environ.get("RULES_BACKEND", "file")
    FIRESTORE_COLLECTION = os.environ.get("FIRESTORE_COLLECTION", "igbot")

    @classmethod
    def validate(cls):
        missing = [
            name
            for name in ("PAGE_ACCESS_TOKEN", "IG_USER_ID", "APP_SECRET", "VERIFY_TOKEN")
            if not getattr(cls, name)
        ]
        if missing:
            raise RuntimeError(
                f"Missing required environment variables: {', '.join(missing)}. "
                f"Copy .env.example to .env and fill them in."
            )

    @classmethod
    def admin_enabled(cls) -> bool:
        return bool(cls.ADMIN_PASSWORD and cls.SECRET_KEY)
