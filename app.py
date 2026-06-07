"""
Lichi Hair — Backend API (Flask)  ->  goes on PythonAnywhere

Only TWO files belong on PythonAnywhere: this app.py and requirements.txt.
The rest of the files in the repo are the website and are served by Vercel.

Local run:
    pip install -r requirements.txt
    python app.py            # http://127.0.0.1:5000
"""

import os
import time
import secrets
import sqlite3
from functools import wraps
from werkzeug.utils import secure_filename
from flask import Flask, request, jsonify, g, send_from_directory

# --------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "lichi.db")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")     # photos live here (no /static)
ALLOWED_EXT = {"png", "jpg", "jpeg", "webp", "gif"}
TOKEN_TTL = 60 * 60 * 24 * 30  # 30 days

# CHANGE before going live (set as PythonAnywhere env vars):
ADMIN_PASSWORD = os.environ.get("LICHI_ADMIN_PASSWORD", "lichi-admin")

# Comma-separated frontend origins, e.g. "https://lichi.vercel.app".
# Empty = reflect any origin (fine for testing; lock down for production).
ALLOWED_ORIGINS = [
    o.strip() for o in os.environ.get("LICHI_ALLOWED_ORIGINS", "").split(",") if o.strip()
]

DEFAULT_SETTINGS = {
    "brand_name": "Lichi",
    "tagline": "Luxury hair, crafted for the woman who owns every room.",
    "whatsapp_number": "2348000000000",
    "hero_note": "Premium bundles, frontals & wigs — handpicked for queens.",
    "instagram": "",
    "currency_default": "NGN",
}

os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024  # 8 MB per upload


# --------------------------------------------------------------------------
# CORS (token auth -> no cookies needed)
# --------------------------------------------------------------------------
@app.after_request
def add_cors(resp):
    origin = request.headers.get("Origin")
    if origin and (not ALLOWED_ORIGINS or origin in ALLOWED_ORIGINS):
        resp.headers["Access-Control-Allow-Origin"] = origin
        resp.headers["Vary"] = "Origin"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        resp.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        resp.headers["Access-Control-Max-Age"] = "86400"
    return resp


# --------------------------------------------------------------------------
# Database
# --------------------------------------------------------------------------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.execute("""CREATE TABLE IF NOT EXISTS hairs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL, description TEXT DEFAULT '',
        price REAL, currency TEXT DEFAULT 'NGN',
        price_mode TEXT DEFAULT 'fixed', image TEXT,
        position INTEGER DEFAULT 0, visible INTEGER DEFAULT 1,
        created_at INTEGER )""")
    db.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
    db.execute("CREATE TABLE IF NOT EXISTS tokens (token TEXT PRIMARY KEY, created INTEGER)")
    for k, v in DEFAULT_SETTINGS.items():
        db.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))
    db.commit()
    db.close()


def get_settings():
    rows = get_db().execute("SELECT key, value FROM settings").fetchall()
    data = {r["key"]: r["value"] for r in rows}
    for k, v in DEFAULT_SETTINGS.items():
        data.setdefault(k, v)
    return data


# --------------------------------------------------------------------------
# Token auth
# --------------------------------------------------------------------------
def make_token():
    t = secrets.token_urlsafe(32)
    db = get_db()
    db.execute("INSERT INTO tokens (token, created) VALUES (?, ?)", (t, int(time.time())))
    db.execute("DELETE FROM tokens WHERE created < ?", (int(time.time()) - TOKEN_TTL,))
    db.commit()
    return t


def token_valid(t):
    if not t:
        return False
    row = get_db().execute("SELECT created FROM tokens WHERE token = ?", (t,)).fetchone()
    return bool(row) and (time.time() - row["created"] <= TOKEN_TTL)


def bearer():
    auth = request.headers.get("Authorization", "")
    return auth[7:] if auth.startswith("Bearer ") else None


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not token_valid(bearer()):
            return jsonify({"error": "Authentication required"}), 401
        return fn(*args, **kwargs)
    return wrapper


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    if data.get("password") == ADMIN_PASSWORD:
        return jsonify({"ok": True, "token": make_token()})
    return jsonify({"error": "Wrong password"}), 401


@app.route("/api/logout", methods=["POST"])
def logout():
    t = bearer()
    if t:
        get_db().execute("DELETE FROM tokens WHERE token = ?", (t,))
        get_db().commit()
    return jsonify({"ok": True})


@app.route("/api/session")
def session_status():
    return jsonify({"admin": token_valid(bearer())})


# --------------------------------------------------------------------------
# Read API
# --------------------------------------------------------------------------
def hair_to_dict(r):
    return {
        "id": r["id"], "name": r["name"], "description": r["description"] or "",
        "price": r["price"], "currency": r["currency"] or "NGN",
        "price_mode": r["price_mode"] or "fixed", "image": r["image"],
        "position": r["position"], "visible": bool(r["visible"]),
    }


@app.route("/api/settings")
def api_settings():
    return jsonify(get_settings())


@app.route("/api/hairs")
def api_hairs():
    # Unlimited best sellers — every visible item, newest first.
    rows = get_db().execute(
        "SELECT * FROM hairs WHERE visible = 1 ORDER BY position ASC, created_at DESC"
    ).fetchall()
    return jsonify([hair_to_dict(r) for r in rows])


@app.route("/api/admin/hairs")
@login_required
def api_admin_hairs():
    rows = get_db().execute(
        "SELECT * FROM hairs ORDER BY position ASC, created_at DESC"
    ).fetchall()
    return jsonify([hair_to_dict(r) for r in rows])


# --------------------------------------------------------------------------
# Write API
# --------------------------------------------------------------------------
def _save_image(fs):
    if not fs or fs.filename == "":
        return None
    ext = fs.filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_EXT:
        return None
    fname = f"{int(time.time())}_{secrets.token_hex(4)}_{secure_filename(fs.filename)}"
    fs.save(os.path.join(UPLOAD_DIR, fname))
    return fname


def _price(mode, raw):
    if mode != "fixed":
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


@app.route("/api/hairs", methods=["POST"])
@login_required
def add_hair():
    db = get_db()
    name = (request.form.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Name is required"}), 400
    mode = request.form.get("price_mode", "fixed")
    db.execute(
        "INSERT INTO hairs (name, description, price, currency, price_mode, image, "
        "position, visible, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
        (name, (request.form.get("description") or "").strip(),
         _price(mode, request.form.get("price")), request.form.get("currency", "NGN"),
         mode, _save_image(request.files.get("image")),
         int(request.form.get("position", 0) or 0),
         1 if request.form.get("visible", "1") in ("1", "true", "on") else 0,
         int(time.time())))
    db.commit()
    return jsonify({"ok": True})


@app.route("/api/hairs/<int:hid>", methods=["POST", "PUT"])
@login_required
def update_hair(hid):
    db = get_db()
    row = db.execute("SELECT * FROM hairs WHERE id = ?", (hid,)).fetchone()
    if not row:
        return jsonify({"error": "Not found"}), 404
    mode = request.form.get("price_mode", row["price_mode"])
    db.execute(
        "UPDATE hairs SET name=?, description=?, price=?, currency=?, price_mode=?, "
        "image=?, position=?, visible=? WHERE id=?",
        ((request.form.get("name") or row["name"]).strip(),
         (request.form.get("description") or row["description"] or "").strip(),
         _price(mode, request.form.get("price")),
         request.form.get("currency", row["currency"]), mode,
         _save_image(request.files.get("image")) or row["image"],
         int(request.form.get("position", row["position"]) or 0),
         1 if request.form.get("visible", "1") in ("1", "true", "on") else 0, hid))
    db.commit()
    return jsonify({"ok": True})


@app.route("/api/hairs/<int:hid>", methods=["DELETE"])
@login_required
def delete_hair(hid):
    db = get_db()
    row = db.execute("SELECT image FROM hairs WHERE id = ?", (hid,)).fetchone()
    if row and row["image"]:
        try:
            os.remove(os.path.join(UPLOAD_DIR, row["image"]))
        except OSError:
            pass
    db.execute("DELETE FROM hairs WHERE id = ?", (hid,))
    db.commit()
    return jsonify({"ok": True})


@app.route("/api/settings", methods=["POST"])
@login_required
def update_settings():
    db = get_db()
    data = request.get_json(silent=True) or {}
    allowed = set(DEFAULT_SETTINGS.keys())
    for k, v in data.items():
        if k in allowed:
            db.execute("INSERT INTO settings (key, value) VALUES (?, ?) "
                       "ON CONFLICT(key) DO UPDATE SET value = excluded.value", (k, str(v)))
    db.commit()
    return jsonify({"ok": True})


# --------------------------------------------------------------------------
# Misc
# --------------------------------------------------------------------------
@app.route("/")
def root():
    return jsonify({"service": "Lichi Hair API", "ok": True})


@app.route("/uploads/<path:fname>")
def uploaded(fname):
    return send_from_directory(UPLOAD_DIR, fname)


init_db()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
