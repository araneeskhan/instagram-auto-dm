"""
Flask webhook server for Instagram comment + DM auto-replies via Meta's
official Graph API, plus a password-protected rules editor at /admin.

Run locally for testing:
    python app.py
Then expose it publicly (e.g. `ngrok http 5000`) so Meta can reach the
/webhook endpoint, and register that public URL + your VERIFY_TOKEN in
the Meta App Dashboard under Webhooks > Instagram.

See README.md for setup and DEPLOY.md for free hosting.
"""
import logging
from datetime import timedelta

from flask import Flask, request, jsonify

from admin import init_admin
from config import Config
from graph_api import IGClient
from handlers import handle_comment, handle_message
from storage import get_store

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)
client = IGClient(Config)
store = get_store(Config.RULES_BACKEND, Config.FIRESTORE_COLLECTION)

# The admin UI is only mounted when a password AND a secret key are set.
# The safe default is no admin UI at all, never an unprotected one.
if Config.admin_enabled():
    app.secret_key = Config.SECRET_KEY
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=not app.debug,
        PERMANENT_SESSION_LIFETIME=timedelta(days=7),
    )
    app.register_blueprint(init_admin(store, Config))
    logger.info("Admin UI enabled at /admin")
else:
    logger.warning(
        "Admin UI DISABLED — set ADMIN_PASSWORD and SECRET_KEY to enable it."
    )


@app.route("/webhook", methods=["GET"])
def verify_webhook():
    """Meta calls this once, synchronously, when you click 'Verify and
    Save' on the Webhooks product page."""
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == Config.VERIFY_TOKEN:
        logger.info("Webhook verified successfully.")
        return challenge, 200

    logger.warning("Webhook verification failed.")
    return "Verification failed", 403


@app.route("/webhook", methods=["POST"])
def receive_webhook():
    """Meta calls this for every subscribed event (comments, messages, ...)."""
    signature = request.headers.get("X-Hub-Signature-256", "")
    if not client.verify_signature(request.get_data(), signature):
        logger.warning("Rejected webhook with invalid signature.")
        return jsonify({"status": "invalid signature"}), 403

    body = request.get_json(silent=True) or {}
    rules = store.load_rules()

    def on_event(event):
        try:
            store.log_event(event)
        except Exception:
            # Never let logging failures break a reply.
            logger.exception("Failed to record event")

    for entry in body.get("entry", []):
        # Comment events arrive as entry.changes[].value
        for change in entry.get("changes", []):
            if change.get("field") == "comments":
                handle_comment(client, change.get("value", {}), rules, on_event)

        # DM events arrive as entry.messaging[]
        for messaging_event in entry.get("messaging", []):
            if "message" in messaging_event:
                handle_message(client, messaging_event, rules, on_event)

    # Always return 200 quickly so Meta doesn't retry/disable the webhook.
    return jsonify({"status": "ok"}), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"}), 200


if __name__ == "__main__":
    Config.validate()
    app.run(host="0.0.0.0", port=Config.PORT, debug=False)
