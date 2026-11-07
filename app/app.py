import json
import logging
import time

from flask import (Flask, abort, flash, jsonify, redirect, render_template, request,
                   session, url_for)

import auth
import aws_clients
import config
import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("cloudscale")

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = config.MAX_UPLOAD_BYTES
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = True  # site is served over HTTPS by CloudFront
app.config["PERMANENT_SESSION_LIFETIME"] = 8 * 3600


@app.before_request
def _ensure_secret_key():
    if not app.secret_key:
        app.secret_key = config.get_secret_key()


@app.context_processor
def _inject():
    return {"user": auth.current_user(), "categories": config.CATEGORIES,
            "version": config.APP_VERSION}


@app.template_filter("thumb")
def thumb_url(key):
    """Photos are served from CloudFront as thumbnails only (originals are never public)."""
    return f"/media/thumbnails/{aws_clients.image_name(key)}.jpg" if key else ""


# ---------------------------------------------------------------- health / ops
@app.get("/health")
def health():
    try:
        db.ping()
        return jsonify(status="ok", version=config.APP_VERSION), 200
    except Exception as exc:
        log.error("health check failed: %s", exc)
        return jsonify(status="db-unavailable"), 503


@app.get("/api/stress")
def stress():
    if not config.stress_enabled():
        abort(404)
    ms = max(1, min(request.args.get("ms", default=300, type=int), 2000))
    end = time.perf_counter() + ms / 1000.0
    n = 0
    while time.perf_counter() < end:
        n += sum(i * i for i in range(500))
    return jsonify(burned_ms=ms, work=n)


# ---------------------------------------------------------------- auth
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        err = auth.sign_up(email, request.form["password"], request.form["name"].strip())
        if err:
            flash(err, "error")
        else:
            flash("Account created. Enter the code we emailed you.", "ok")
            return redirect(url_for("confirm", email=email))
    return render_template("signup.html")


@app.route("/confirm", methods=["GET", "POST"])
def confirm():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        err = auth.confirm_sign_up(email, request.form["code"].strip())
        if err:
            flash(err, "error")
        else:
            flash("Email confirmed. You can sign in now.", "ok")
            return redirect(url_for("login"))
    return render_template("confirm.html", email=request.args.get("email", ""))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        claims, err = auth.log_in(email, request.form["password"])
        if err:
            flash(err, "error")
        else:
            session.clear()
            session["user"] = claims
            session.permanent = True
            nxt = request.args.get("next", "")
            return redirect(nxt if nxt.startswith("/") and not nxt.startswith("//") else url_for("index"))
    return render_template("login.html")


@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


# ---------------------------------------------------------------- AI helpers
def _json_login_required(view):
    import functools

    @functools.wraps(view)
    def wrapper(*a, **kw):
        if not auth.current_user():
            return jsonify(error="Please sign in first."), 401
        if not request.is_json:  # JSON-only, so cross-site form posts can't trigger it
            return jsonify(error="JSON body required."), 415
        return view(*a, **kw)

    return wrapper


@app.post("/api/suggest-category")
@_json_login_required
def api_suggest_category():
    data = request.get_json(silent=True) or {}
    title = str(data.get("title", "")).strip()[:200]
    notes = str(data.get("notes", "")).strip()[:300]
    if not (title or notes):
        return jsonify(error="Enter a title or notes first."), 400
    try:
        result = aws_clients.predict_category(title, notes)
        return jsonify(category=result["category"], confidence=result["confidence"])
    except Exception as exc:
        log.error("category prediction failed: %s", exc)
        return jsonify(error="Category suggestion is unavailable right now."), 502


@app.post("/api/write-description")
@_json_login_required
def api_write_description():
    data = request.get_json(silent=True) or {}
    title = str(data.get("title", "")).strip()[:200]
    notes = str(data.get("notes", "")).strip()[:300]
    if not (title or notes):
        return jsonify(error="Enter a title or notes first."), 400
    kind = "found" if data.get("kind") == "found" else "lost"
    category = data.get("category") if data.get("category") in config.CATEGORIES else "Other"
    try:
        text = aws_clients.write_description(kind, title, notes, category,
                                             str(data.get("location", ""))[:120])
        return jsonify(description=text)
    except Exception as exc:
        log.error("description generation failed: %s", exc)
        return jsonify(error="The description writer is unavailable right now."), 502


# ---------------------------------------------------------------- items
@app.get("/")
def index():
    q = request.args.get("q", "").strip()
    kind = request.args.get("kind", "")
    category = request.args.get("category", "")
    sql = ["SELECT i.*, u.display_name AS owner_name FROM items i JOIN users u ON u.sub = i.owner_sub WHERE 1=1"]
    params = []
    if q:
        sql.append("AND (i.title ILIKE %s OR i.notes ILIKE %s OR i.description ILIKE %s OR i.location ILIKE %s)")
        params += [f"%{q}%"] * 4
    if kind in ("lost", "found"):
        sql.append("AND i.kind = %s")
        params.append(kind)
    if category in config.CATEGORIES:
        sql.append("AND i.category = %s")
        params.append(category)
    sql.append("ORDER BY i.created_at DESC LIMIT 60")
    with db.get_conn() as conn:
        items = conn.execute(" ".join(sql), params).fetchall()
    return render_template("index.html", items=items, q=q, kind=kind, category=category)


@app.route("/items/new", methods=["GET", "POST"])
@auth.login_required
def new_item():
    if request.method == "POST":
        f = request.form
        kind = f.get("kind", "lost")
        title = f.get("title", "").strip()
        if kind not in ("lost", "found") or not title:
            flash("Please choose lost/found and enter a title.", "error")
            return render_template("new_item.html", form=f)
        category = f.get("category") if f.get("category") in config.CATEGORIES else "Other"
        ml_category = f.get("ml_category") if f.get("ml_category") in config.CATEGORIES else None
        try:
            ml_conf = min(max(float(f.get("ml_confidence", "")), 0.0), 1.0) if ml_category else None
        except ValueError:
            ml_conf = None
        try:
            key = aws_clients.upload_photo(request.files.get("photo"))
        except ValueError as exc:
            flash(str(exc), "error")
            return render_template("new_item.html", form=f)
        with db.get_conn() as conn:
            row = conn.execute(
                """INSERT INTO items (owner_sub, kind, title, notes, description, category,
                                      ml_category, ml_confidence, location, item_date, image_key)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NULLIF(%s, '')::date, %s)
                   RETURNING id""",
                (auth.current_user()["sub"], kind, title, f.get("notes", "").strip(),
                 f.get("description", "").strip(), category, ml_category, ml_conf,
                 f.get("location", "").strip(), f.get("item_date", ""), key),
            ).fetchone()
        flash("Item posted.", "ok")
        return redirect(url_for("item_detail", item_id=row["id"]))
    return render_template("new_item.html", form={})


@app.get("/items/<int:item_id>")
def item_detail(item_id):
    with db.get_conn() as conn:
        item = conn.execute(
            "SELECT i.*, u.display_name AS owner_name FROM items i "
            "JOIN users u ON u.sub = i.owner_sub WHERE i.id = %s", (item_id,)).fetchone()
        if not item:
            abort(404)
        claims = conn.execute(
            "SELECT c.*, u.display_name AS claimant_name FROM claims c "
            "JOIN users u ON u.sub = c.claimant_sub WHERE c.item_id = %s ORDER BY c.created_at",
            (item_id,)).fetchall()
    photo_state, meta = "none", None
    if item["image_key"]:
        meta = aws_clients.get_meta(item["image_key"])
        photo_state = "pending" if meta is None else ("flagged" if meta.get("flagged") else "ok")
    if meta and not meta.get("flagged") and meta.get("labels") and not item["labels"]:
        item["labels"] = meta["labels"]  # persist the Rekognition labels the Lambda cannot write to RDS
        try:
            with db.get_conn() as conn:
                conn.execute("UPDATE items SET labels = %s::jsonb WHERE id = %s",
                             (json.dumps(meta["labels"]), item_id))
        except Exception as exc:
            log.warning("could not store labels: %s", exc)
    me = auth.current_user()
    # Claim messages may contain contact details: only the owner and the claimants may read them.
    claims_visible = bool(me) and (me["sub"] == item["owner_sub"]
                                   or any(c["claimant_sub"] == me["sub"] for c in claims))
    return render_template("item.html", item=item, claims=claims, photo_state=photo_state,
                           claims_visible=claims_visible,
                           is_owner=bool(me) and me["sub"] == item["owner_sub"])


@app.post("/items/<int:item_id>/claim")
@auth.login_required
def claim_item(item_id):
    me = auth.current_user()
    with db.get_conn() as conn:
        item = conn.execute(
            "SELECT i.*, u.email AS owner_email FROM items i JOIN users u ON u.sub = i.owner_sub "
            "WHERE i.id = %s", (item_id,)).fetchone()
        if not item:
            abort(404)
        if item["kind"] != "found" or item["status"] != "open":
            flash("Only open 'found' items can be claimed.", "error")
            return redirect(url_for("item_detail", item_id=item_id))
        if item["owner_sub"] == me["sub"]:
            flash("You can't claim your own item.", "error")
            return redirect(url_for("item_detail", item_id=item_id))
        message = request.form.get("message", "").strip()
        conn.execute("INSERT INTO claims (item_id, claimant_sub, message) VALUES (%s, %s, %s)",
                     (item_id, me["sub"], message))
        conn.execute("UPDATE items SET status = 'claimed' WHERE id = %s", (item_id,))
    aws_clients.publish_claim(item["owner_email"], item["title"], me["name"], me["email"], message)
    flash("Claim sent. The owner will be notified.", "ok")
    return redirect(url_for("item_detail", item_id=item_id))


@app.post("/items/<int:item_id>/return")
@auth.login_required
def mark_returned(item_id):
    me = auth.current_user()
    with db.get_conn() as conn:
        item = conn.execute("SELECT owner_sub, status FROM items WHERE id = %s", (item_id,)).fetchone()
        if not item:
            abort(404)
        if item["owner_sub"] != me["sub"]:
            abort(403)
        if item["status"] != "claimed":
            flash("Only a claimed item can be marked as returned.", "error")
            return redirect(url_for("item_detail", item_id=item_id))
        conn.execute("UPDATE items SET status = 'returned' WHERE id = %s", (item_id,))
    flash("Marked as returned. Thank you!", "ok")
    return redirect(url_for("item_detail", item_id=item_id))


@app.errorhandler(413)
def too_large(_):
    flash("Photo is too large (max 5 MB).", "error")
    return redirect(url_for("new_item"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
