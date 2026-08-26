"""
Password-protected web UI for editing reply rules, at /admin.

Security notes, because this page can change what your account DMs people:

  - If ADMIN_PASSWORD or SECRET_KEY is unset, the whole blueprint is never
    registered. The safe default is "no admin UI", never "open admin UI".
  - The password is compared with hmac.compare_digest to avoid leaking
    length/content through timing.
  - Login state is a signed Flask session cookie, HTTP-only and SameSite.
  - Saves are validated before they are written, so a malformed rule can't
    take the bot down.
"""
import hmac
import logging

from flask import (
    Blueprint, jsonify, render_template, request, session,
)

logger = logging.getLogger(__name__)

admin_bp = Blueprint("admin", __name__, template_folder="templates")

_store = None
_config = None


def init_admin(store, config):
    global _store, _config
    _store, _config = store, config
    return admin_bp


def _logged_in() -> bool:
    return session.get("admin_ok") is True


def _require_login():
    if not _logged_in():
        return jsonify({"error": "not authenticated"}), 401
    return None


# ---- validation ---------------------------------------------------------

def validate_rules(rules) -> list:
    """Return a list of problems. Empty list means the payload is safe."""
    problems = []

    if not isinstance(rules, dict):
        return ["Rules must be a JSON object."]

    def check_rule_list(rule_list, where, reply_keys):
        if not isinstance(rule_list, list):
            problems.append(f"{where}: must be a list.")
            return
        for i, rule in enumerate(rule_list):
            label = f"{where}[{i}]"
            if not isinstance(rule, dict):
                problems.append(f"{label}: must be an object.")
                continue
            kws = rule.get("keywords")
            if not isinstance(kws, list) or not kws:
                problems.append(f"{label}: needs a non-empty 'keywords' list.")
            elif not all(isinstance(k, str) and k.strip() for k in kws):
                problems.append(f"{label}: keywords must be non-empty strings.")
            if not any(rule.get(k) for k in reply_keys):
                problems.append(
                    f"{label}: needs at least one of {', '.join(reply_keys)}."
                )

    check_rule_list(rules.get("comment_rules", []), "comment_rules",
                    ["public_reply", "private_reply"])
    check_rule_list(rules.get("dm_rules", []), "dm_rules", ["reply"])

    posts = rules.get("posts", {})
    if not isinstance(posts, dict):
        problems.append("posts: must be an object keyed by media ID.")
    else:
        for media_id, cfg in posts.items():
            if not str(media_id).isdigit():
                problems.append(f"posts['{media_id}']: media ID should be numeric.")
            if not isinstance(cfg, dict):
                problems.append(f"posts['{media_id}']: must be an object.")
                continue
            check_rule_list(cfg.get("comment_rules", []),
                            f"posts['{media_id}'].comment_rules",
                            ["public_reply", "private_reply"])

    return problems


# ---- routes -------------------------------------------------------------

@admin_bp.route("/admin")
def admin_page():
    return render_template("admin.html", logged_in=_logged_in())


@admin_bp.route("/admin/login", methods=["POST"])
def login():
    supplied = (request.get_json(silent=True) or {}).get("password", "")
    if hmac.compare_digest(str(supplied), _config.ADMIN_PASSWORD):
        session["admin_ok"] = True
        session.permanent = True
        logger.info("Admin login succeeded")
        return jsonify({"ok": True})
    logger.warning("Admin login failed from %s", request.remote_addr)
    return jsonify({"ok": False, "error": "Incorrect password"}), 401


@admin_bp.route("/admin/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"ok": True})


@admin_bp.route("/admin/api/rules", methods=["GET"])
def get_rules():
    if (resp := _require_login()):
        return resp
    return jsonify(_store.load_rules())


@admin_bp.route("/admin/api/rules", methods=["PUT"])
def put_rules():
    if (resp := _require_login()):
        return resp

    rules = request.get_json(silent=True)
    problems = validate_rules(rules)
    if problems:
        return jsonify({"ok": False, "problems": problems}), 400

    _store.save_rules(rules)
    logger.info("Rules updated via admin UI")
    return jsonify({"ok": True})


@admin_bp.route("/admin/api/events", methods=["GET"])
def get_events():
    if (resp := _require_login()):
        return resp
    return jsonify({"events": _store.recent_events(limit=50)})
