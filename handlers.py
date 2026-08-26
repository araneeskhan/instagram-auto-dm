"""
Turns raw webhook payloads into bot actions, using the rules in rules.json.

Rule resolution for a comment, in order:
  1. keyword rules for THAT specific post   (rules["posts"][media_id]["comment_rules"])
  2. global keyword rules                    (rules["comment_rules"])
  3. that post's default                     (rules["posts"][media_id]["comment_default"])
  4. the global default                      (rules["comment_default"])

Set "ignore_global": true on a post to skip steps 2 and 4 — useful for a
giveaway post where you want ONLY that post's replies to fire.

Keep the matching logic here simple and readable — swap in an LLM call,
a database lookup, or a proper intent classifier later if you outgrow
keyword matching.
"""
import logging
import re

from graph_api import IGClient, GraphAPIError

logger = logging.getLogger(__name__)


def _contains_keyword(text: str, keyword: str) -> bool:
    """Whole-word match, so the keyword 'price' does NOT fire on 'surprise'.
    Falls back to a plain substring check for multi-word or emoji keywords."""
    kw = keyword.lower().strip()
    if not kw:
        return False
    pattern = r"(?<!\w)" + re.escape(kw) + r"(?!\w)"
    return re.search(pattern, text) is not None


def _find_rule(text: str, rule_list: list):
    """Return the first rule whose keywords appear in `text`, else None."""
    text_lower = (text or "").lower()
    for rule in rule_list or []:
        if any(_contains_keyword(text_lower, kw) for kw in rule.get("keywords", [])):
            return rule
    return None


def resolve_comment_reply(text: str, media_id, rules: dict):
    """Work out (public_reply, private_reply) for a comment on `media_id`."""
    posts = rules.get("posts") or {}
    post_cfg = posts.get(str(media_id), {}) if media_id else {}
    ignore_global = bool(post_cfg.get("ignore_global"))

    # 1. this post's own keyword rules
    rule = _find_rule(text, post_cfg.get("comment_rules"))

    # 2. fall back to global keyword rules
    if rule is None and not ignore_global:
        rule = _find_rule(text, rules.get("comment_rules"))

    if rule is not None:
        return rule.get("public_reply"), rule.get("private_reply")

    # 3. this post's default, else 4. the global default
    default = post_cfg.get("comment_default")
    if default is None and not ignore_global:
        default = rules.get("comment_default")
    default = default or {}
    return default.get("public_reply"), default.get("private_reply")


def handle_comment(client: IGClient, comment: dict, rules: dict, on_event=None) -> None:
    """
    `comment` is the webhook's changes[].value, which looks like:
    {
      "id": "17865799...",
      "text": "how much does this cost?",
      "from": {"id": "...", "username": "..."},
      "media": {"id": "17895695668004550", "media_product_type": "FEED"}
    }
    """
    comment_id = comment.get("id")
    text = comment.get("text", "")
    media_id = (comment.get("media") or {}).get("id")

    if not comment_id:
        logger.warning("Comment payload missing id: %s", comment)
        return

    # Don't reply to your own comments — that's how infinite loops start.
    if comment.get("from", {}).get("id") == client.cfg.IG_USER_ID:
        return

    public_reply, private_reply = resolve_comment_reply(text, media_id, rules)

    sent = []
    try:
        if public_reply:
            client.reply_to_comment(comment_id, public_reply)
            sent.append("public reply")
            logger.info("Replied publicly to comment %s (post %s)", comment_id, media_id)
        if private_reply:
            client.send_private_reply(comment_id, private_reply)
            sent.append("DM")
            logger.info("Sent private reply for comment %s (post %s)", comment_id, media_id)
    except GraphAPIError as exc:
        logger.exception("Failed to respond to comment %s", comment_id)
        if on_event:
            on_event({"kind": "comment", "media_id": media_id,
                      "summary": f'FAILED on "{text[:40]}": {exc}'})
        return

    if on_event and sent:
        on_event({"kind": "comment", "media_id": media_id,
                  "summary": f'"{text[:40]}" -> sent {" + ".join(sent)}'})


def handle_message(client: IGClient, messaging_event: dict, rules: dict, on_event=None) -> None:
    """
    `messaging_event` looks like:
    {
      "sender": {"id": "IGSID..."},
      "recipient": {"id": "..."},
      "message": {"mid": "...", "text": "hi there"}
    }

    DMs aren't attached to a post, so these use the global dm_rules only.
    """
    sender_id = messaging_event.get("sender", {}).get("id")
    message = messaging_event.get("message", {})
    text = message.get("text", "")

    if not sender_id:
        logger.warning("Message event missing sender id: %s", messaging_event)
        return

    # Ignore echoes of the bot's own outgoing messages to avoid loops.
    if message.get("is_echo") or sender_id == client.cfg.IG_USER_ID:
        return

    rule = _find_rule(text, rules.get("dm_rules"))
    reply = rule.get("reply") if rule else rules.get("dm_default")

    if not reply:
        return

    try:
        client.send_dm(sender_id, reply)
        logger.info("Replied to DM from %s", sender_id)
        if on_event:
            on_event({"kind": "dm", "media_id": None,
                      "summary": f'"{text[:40]}" -> replied'})
    except GraphAPIError as exc:
        logger.exception("Failed to send DM reply to %s", sender_id)
        if on_event:
            on_event({"kind": "dm", "media_id": None,
                      "summary": f'FAILED on "{text[:40]}": {exc}'})
