"""
Thin wrapper around the parts of Meta's Graph API this bot needs:

- Sending a DM (Instagram Send API)
- Sending a "private reply" DM in response to a comment
- Replying publicly to a comment
- Verifying the webhook payload signature

All calls use the official Graph API over HTTPS with your Page Access
Token. No browser automation, no scraping, no unofficial endpoints.
"""
import hashlib
import hmac
import logging

import requests

from config import Config

logger = logging.getLogger(__name__)


class GraphAPIError(RuntimeError):
    pass


class IGClient:
    def __init__(self, config: Config = Config):
        self.cfg = config

    # ---- outbound actions -------------------------------------------------

    def send_dm(self, recipient_igsid: str, text: str) -> dict:
        """Send a direct message to a user who has messaged you before
        (or within Meta's allowed messaging window / tags)."""
        url = f"{self.cfg.GRAPH_API_BASE}/{self.cfg.IG_USER_ID}/messages"
        payload = {
            "recipient": {"id": recipient_igsid},
            "message": {"text": text},
        }
        return self._post(url, payload)

    def send_private_reply(self, comment_id: str, text: str) -> dict:
        """Send a DM to whoever left `comment_id`, using Meta's official
        Private Replies feature. Must be sent within the allowed window
        after the comment was made (currently 7 days per Meta's policy)."""
        url = f"{self.cfg.GRAPH_API_BASE}/{comment_id}/private_replies"
        payload = {"message": text}
        return self._post(url, payload)

    def reply_to_comment(self, comment_id: str, text: str) -> dict:
        """Post a public reply underneath a comment."""
        url = f"{self.cfg.GRAPH_API_BASE}/{comment_id}/replies"
        payload = {"message": text}
        return self._post(url, payload)

    def _post(self, url: str, payload: dict) -> dict:
        params = {"access_token": self.cfg.PAGE_ACCESS_TOKEN}
        resp = requests.post(url, params=params, json=payload, timeout=15)
        if resp.status_code >= 400:
            logger.error("Graph API error %s: %s", resp.status_code, resp.text)
            raise GraphAPIError(f"{resp.status_code}: {resp.text}")
        return resp.json()

    # ---- inbound verification ----------------------------------------------

    def verify_signature(self, raw_body: bytes, signature_header: str) -> bool:
        """Verify X-Hub-Signature-256 so you know a webhook POST really
        came from Meta and not a spoofed request."""
        if not signature_header or not signature_header.startswith("sha256="):
            return False
        expected = signature_header.split("sha256=", 1)[1]
        computed = hmac.new(
            self.cfg.APP_SECRET.encode("utf-8"), raw_body, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, computed)
