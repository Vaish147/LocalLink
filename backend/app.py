import os
import uuid
from datetime import datetime
from functools import wraps

import mysql.connector
from mysql.connector import IntegrityError
from flask import Flask, jsonify, request, send_from_directory, session
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.dirname(BASE_DIR)
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ─────────────────────────────────────────────────────────────────────
#  MYSQL CONFIG  — EDIT THESE TWO LINES
# ─────────────────────────────────────────────────────────────────────
MYSQL_CONFIG = {
    "host":     "localhost",
    "port":     3306,
    "user":     "locallink",          
    "password": "locallink123",       
    "database": "locallink",
    "charset":  "utf8mb4",
    "use_unicode": True,
}

# ─────────────────────────────────────────────────────────────────────
#  AUTH TOGGLES
# ─────────────────────────────────────────────────────────────────────
REQUIRE_USER_AUTH_FOR_WRITES = False
REQUIRE_SHOP_AUTH_FOR_WRITES = False
REQUIRE_ADMIN_AUTH           = True

DEFAULT_ADMIN_EMAIL    = "admin@locallink.com"
DEFAULT_ADMIN_PASSWORD = "admin123"

app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024
app.secret_key = os.environ.get("LOCALLINK_SECRET", "locallink-dev-secret-change-me")

ALLOWED_PROOF = {"pdf", "png", "jpg", "jpeg", "webp"}
ALLOWED_LOGO  = {"png", "jpg", "jpeg", "webp", "gif"}


# ─────────────────────────────────────────────────────────────────────
#  DB HELPERS
# ─────────────────────────────────────────────────────────────────────
def db():
    return mysql.connector.connect(**MYSQL_CONFIG)


def _dict_cursor(conn):
    return conn.cursor(dictionary=True)


def fetchone(sql, params=()):
    conn = db()
    try:
        cur = _dict_cursor(conn)
        cur.execute(sql, params)
        row = cur.fetchone()
        cur.close()
        return row
    finally:
        conn.close()


def fetchall(sql, params=()):
    conn = db()
    try:
        cur = _dict_cursor(conn)
        cur.execute(sql, params)
        rows = cur.fetchall()
        cur.close()
        return rows
    finally:
        conn.close()


def execute(sql, params=()):
    """INSERT/UPDATE/DELETE — returns lastrowid."""
    conn = db()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        conn.commit()
        lastid = cur.lastrowid
        cur.close()
        return lastid
    finally:
        conn.close()


def ensure_admin():
    """Create the default admin user if it doesn't exist yet."""
    existing = fetchone(
        "SELECT id FROM users WHERE email=%s", (DEFAULT_ADMIN_EMAIL,)
    )
    if not existing:
        execute(
            "INSERT INTO users(name,email,password_hash,is_admin) "
            "VALUES(%s,%s,%s,1)",
            ("LocalLink Admin", DEFAULT_ADMIN_EMAIL,
             generate_password_hash(DEFAULT_ADMIN_PASSWORD)),
        )
        print(f"[INIT] Created default admin: {DEFAULT_ADMIN_EMAIL} / {DEFAULT_ADMIN_PASSWORD}")


# ─────────────────────────────────────────────────────────────────────
#  AUTH HELPERS
# ─────────────────────────────────────────────────────────────────────
def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    return fetchone("SELECT * FROM users WHERE id=%s", (uid,))


def require_user_auth(fn):
    @wraps(fn)
    def inner(*a, **kw):
        if REQUIRE_USER_AUTH_FOR_WRITES and not session.get("user_id"):
            return jsonify({"message": "Please log in."}), 401
        return fn(*a, **kw)
    return inner


def require_admin(fn):
    @wraps(fn)
    def inner(*a, **kw):
        if REQUIRE_ADMIN_AUTH:
            u = current_user()
            if not u:
                return jsonify({"message": "Admin login required."}), 401
            if not u["is_admin"]:
                return jsonify({"message": "Admin access only."}), 403
        return fn(*a, **kw)
    return inner


# ─────────────────────────────────────────────────────────────────────
#  SERIALISERS
# ─────────────────────────────────────────────────────────────────────
def clean_user(row):
    if not row:
        return None
    return {
        "id":      row["id"],
        "name":    row["name"],
        "email":   row["email"],
        "avatar":  row.get("avatar"),
        "isAdmin": bool(row.get("is_admin", 0)),
    }


def clean_review(row):
    return {
        "id":           row["id"],
        "shopId":       row["shop_id"],
        "userId":       row["user_id"],
        "reviewerName": row["reviewer_name"],
        "rating":       row["rating"],
        "comment":      row["comment"],
        "createdAt":    row["created_at"].isoformat() if row["created_at"] else None,
    }


def is_open_now(open_time, close_time):
    def parse(t):
        for fmt in ("%H:%M", "%H:%M:%S", "%I:%M %p"):
            try:
                return datetime.strptime((t or "").strip(), fmt).time()
            except (ValueError, AttributeError):
                continue
        return None
    start, end = parse(open_time), parse(close_time)
    if not start or not end:
        return False
    now = datetime.now().time()
    return start <= now < end if start <= end else (now >= start or now < end)


def rating_for(conn, shop_id):
    cur = _dict_cursor(conn)
    cur.execute(
        "SELECT ROUND(AVG(rating),1) AS avg_rating, COUNT(*) AS cnt "
        "FROM reviews WHERE shop_id=%s", (shop_id,)
    )
    r = cur.fetchone()
    cur.close()
    return float(r["avg_rating"] or 0), int(r["cnt"] or 0)


def clean_shop(row, conn=None):
    own = conn is None
    if own:
        conn = db()
    try:
        rating, review_count = rating_for(conn, row["id"])
    finally:
        if own:
            conn.close()
    return {
        "id":              row["id"],
        "name":            row["shop_name"],
        "shopName":        row["shop_name"],
        "ownerName":       row["owner_name"],
        "email":           row["email"],
        "phone":           row["phone"],
        "category":        row["category"],
        "website":         row["website"],
        "gst":             row["gst"],
        "shopAct":         row["shop_act"],
        "ownerIdProof":    row["owner_id_proof"],
        "logo":            row["logo"],
        "image":           f"/uploads/{row['logo']}" if row["logo"] else "/Images/real-images.png",
        "openTime":        row["open_time"],
        "closeTime":       row["close_time"],
        "address":         row["address"],
        "city":            row["city"],
        "state":           row["state"],
        "pincode":         row["pincode"],
        "description":     row["description"],
        "tags":            [x.strip() for x in (row["tags"] or "").split(",") if x.strip()],
        "rating":          rating,
        "reviewCount":     review_count,
        "openNow":         is_open_now(row["open_time"], row["close_time"]),
        "isVerified":      bool(row["is_verified"]),
        "isActive":        bool(row["is_active"]),
        "rejectionReason": row["rejection_reason"],
    }


# ─────────────────────────────────────────────────────────────────────
#  UPLOAD HELPERS
# ─────────────────────────────────────────────────────────────────────
def allowed(file, kinds):
    return bool(
        file and file.filename and "." in file.filename
        and file.filename.rsplit(".", 1)[1].lower() in kinds
    )


def save_upload(file, kinds):
    if not allowed(file, kinds):
        return None
    fname = f"{uuid.uuid4().hex[:10]}_{secure_filename(file.filename)}"
    file.save(os.path.join(UPLOAD_DIR, fname))
    return fname


# ─────────────────────────────────────────────────────────────────────
#  HEALTH
# ─────────────────────────────────────────────────────────────────────
@app.get("/api/health")
def health():
    try:
        fetchone("SELECT 1 AS ok")
        return jsonify({"status": "ok", "database": "mysql"})
    except mysql.connector.Error as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ─────────────────────────────────────────────────────────────────────
#  AUTH
# ─────────────────────────────────────────────────────────────────────
@app.post("/api/auth/signup")
def signup():
    data = request.get_json(silent=True) or {}
    name     = (data.get("name") or "").strip()
    email    = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    if not name or "@" not in email or len(password) < 6:
        return jsonify({"message": "Provide a valid name, email and password ≥ 6 chars."}), 400
    try:
        uid = execute(
            "INSERT INTO users(name,email,password_hash) VALUES(%s,%s,%s)",
            (name, email, generate_password_hash(password)),
        )
    except IntegrityError:
        return jsonify({"message": "Email already registered. Try logging in."}), 409
    row = fetchone("SELECT * FROM users WHERE id=%s", (uid,))
    session["user_id"] = row["id"]
    return jsonify({"message": "Sign up successful", "user": clean_user(row)}), 201


@app.post("/api/auth/login")
def login():
    data = request.get_json(silent=True) or {}
    email    = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    row = fetchone("SELECT * FROM users WHERE email=%s", (email,))
    if not row or not check_password_hash(row["password_hash"], password):
        return jsonify({"message": "Invalid email or password."}), 401
    session["user_id"] = row["id"]
    return jsonify({"message": "Login successful", "user": clean_user(row)})


@app.post("/api/auth/logout")
def logout_user():
    session.pop("user_id", None)
    return jsonify({"message": "Logged out"})


@app.get("/api/auth/me")
def auth_me():
    u = current_user()
    return jsonify({"user": clean_user(u) if u else None})


# ─────────────────────────────────────────────────────────────────────
#  USERS
# ─────────────────────────────────────────────────────────────────────
@app.get("/api/users/<int:user_id>")
def user_profile(user_id):
    row = fetchone("SELECT * FROM users WHERE id=%s", (user_id,))
    if not row:
        return jsonify({"message": "User not found"}), 404
    reviews = fetchall("""
        SELECT r.*, s.shop_name FROM reviews r
        JOIN shops s ON s.id = r.shop_id
        WHERE r.user_id=%s ORDER BY r.created_at DESC
    """, (user_id,))
    result = clean_user(row)
    result["reviews"] = [{**clean_review(r), "shopName": r["shop_name"]} for r in reviews]
    return jsonify(result)


@app.put("/api/users/<int:user_id>")
@require_user_auth
def update_user(user_id):
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"message": "Name is required."}), 400
    row = fetchone("SELECT * FROM users WHERE id=%s", (user_id,))
    if not row:
        return jsonify({"message": "User not found"}), 404
    execute("UPDATE users SET name=%s WHERE id=%s", (name, user_id))
    row = fetchone("SELECT * FROM users WHERE id=%s", (user_id,))
    return jsonify({"message": "Profile updated", "user": clean_user(row)})


@app.post("/api/users/<int:user_id>/password")
@require_user_auth
def change_password(user_id):
    data = request.get_json(silent=True) or {}
    old = data.get("oldPassword") or ""
    new = data.get("newPassword") or ""
    if len(new) < 6:
        return jsonify({"message": "New password must be ≥ 6 chars."}), 400
    row = fetchone("SELECT * FROM users WHERE id=%s", (user_id,))
    if not row or not check_password_hash(row["password_hash"], old):
        return jsonify({"message": "Current password is incorrect."}), 401
    execute("UPDATE users SET password_hash=%s WHERE id=%s",
            (generate_password_hash(new), user_id))
    return jsonify({"message": "Password changed"})


# ─────────────────────────────────────────────────────────────────────
#  SHOPS — REGISTRATION / LOGIN / UPDATE
# ─────────────────────────────────────────────────────────────────────
@app.post("/api/shops/register")
def register_shop():
    form = request.form
    required = ["shopName", "ownerName", "email", "phone", "category", "gst",
                "shopAct", "openTime", "closeTime", "address", "city",
                "state", "pincode", "description", "password"]
    if any(not (form.get(x) or "").strip() for x in required):
        return jsonify({"message": "Please fill all required fields."}), 400

    try:
        o = datetime.strptime(form["openTime"], "%H:%M").time()
        c = datetime.strptime(form["closeTime"], "%H:%M").time()
    except ValueError:
        return jsonify({"message": "Times must be HH:MM."}), 400
    if o >= c:
        return jsonify({"message": "Closing time must be after opening time."}), 400

    proof = request.files.get("ownerIdProof")
    logo  = request.files.get("logo")
    if not allowed(proof, ALLOWED_PROOF):
        return jsonify({"message": "Owner ID proof must be PDF or image."}), 400
    if proof.content_length and proof.content_length > 2 * 1024 * 1024:
        return jsonify({"message": "ID proof must be under 2 MB."}), 400
    if logo and logo.filename and not allowed(logo, ALLOWED_LOGO):
        return jsonify({"message": "Logo must be an image."}), 400

    proof_name = save_upload(proof, ALLOWED_PROOF)
    logo_name  = save_upload(logo, ALLOWED_LOGO)
    if not proof_name:
        return jsonify({"message": "Unable to save ID proof."}), 400

    try:
        shop_id = execute("""
            INSERT INTO shops
              (shop_name,owner_name,email,password_hash,phone,category,website,
               gst,shop_act,owner_id_proof,logo,open_time,close_time,address,
               city,state,pincode,description,tags,is_verified,is_active)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,0,1)
        """, (
            form["shopName"].strip(), form["ownerName"].strip(),
            form["email"].strip().lower(),
            generate_password_hash(form["password"]),
            form["phone"].strip(), form["category"].strip(),
            (form.get("website") or "").strip(),
            form["gst"].strip(), form["shopAct"].strip(),
            proof_name, logo_name,
            form["openTime"], form["closeTime"],
            form["address"].strip(), form["city"].strip(),
            form["state"].strip(), form["pincode"].strip(),
            form["description"].strip(), (form.get("tags") or "").strip(),
        ))
    except IntegrityError:
        return jsonify({"message": "A shop with this email already exists."}), 409

    row = fetchone("SELECT * FROM shops WHERE id=%s", (shop_id,))
    return jsonify({
        "message": "Shop registered. Awaiting admin approval.",
        "shop": clean_shop(row),
    }), 201


@app.post("/api/shops/login")
def shop_login():
    data = request.get_json(silent=True) or {}
    email    = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    row = fetchone("SELECT * FROM shops WHERE email=%s", (email,))
    if not row or not check_password_hash(row["password_hash"], password):
        return jsonify({"message": "Invalid credentials."}), 401
    session["shop_id"] = row["id"]
    return jsonify({"message": "Shop login successful", "shop": clean_shop(row)})


@app.post("/api/shops/logout")
def shop_logout():
    session.pop("shop_id", None)
    return jsonify({"message": "Shop logged out"})


@app.put("/api/shops/<int:shop_id>")
def update_shop(shop_id):
    if REQUIRE_SHOP_AUTH_FOR_WRITES and session.get("shop_id") != shop_id:
        return jsonify({"message": "Shop login required."}), 401

    data = request.get_json(silent=True) or {}
    field_map = {
        "shop_name":   data.get("shopName"),
        "owner_name":  data.get("ownerName"),
        "phone":       data.get("phone"),
        "category":    data.get("category"),
        "website":     data.get("website"),
        "open_time":   data.get("openTime"),
        "close_time":  data.get("closeTime"),
        "address":     data.get("address"),
        "city":        data.get("city"),
        "state":       data.get("state"),
        "pincode":     data.get("pincode"),
        "description": data.get("description"),
    }
    tags = data.get("tags")
    if isinstance(tags, list):
        field_map["tags"] = ",".join(tags)
    elif isinstance(tags, str):
        field_map["tags"] = tags

    fields = {k: (v.strip() if isinstance(v, str) else v)
              for k, v in field_map.items() if v is not None}
    if not fields:
        return jsonify({"message": "No changes supplied."}), 400

    row = fetchone("SELECT * FROM shops WHERE id=%s", (shop_id,))
    if not row:
        return jsonify({"message": "Shop not found"}), 404

    new_open  = fields.get("open_time",  row["open_time"])
    new_close = fields.get("close_time", row["close_time"])
    try:
        o = datetime.strptime(new_open,  "%H:%M").time()
        c = datetime.strptime(new_close, "%H:%M").time()
        if o >= c:
            return jsonify({"message": "Closing time must be after opening time."}), 400
    except ValueError:
        return jsonify({"message": "Times must be HH:MM."}), 400

    sets = ", ".join(f"{k}=%s" for k in fields)
    execute(f"UPDATE shops SET {sets} WHERE id=%s",
            (*fields.values(), shop_id))
    row = fetchone("SELECT * FROM shops WHERE id=%s", (shop_id,))
    return jsonify({"message": "Shop profile updated", "shop": clean_shop(row)})


# ─────────────────────────────────────────────────────────────────────
#  SHOPS — READ
# ─────────────────────────────────────────────────────────────────────
@app.get("/api/shops")
def list_shops():
    search   = (request.args.get("search")   or "").strip().lower()
    category = (request.args.get("category") or "").strip().lower()
    city     = (request.args.get("city")     or "").strip().lower()
    include_unverified = request.args.get("include_unverified") == "1"
    include_inactive   = request.args.get("include_inactive")   == "1"

    sql = "SELECT * FROM shops WHERE 1=1"
    if not include_unverified:
        sql += " AND is_verified = 1"
    if not include_inactive:
        sql += " AND is_active = 1"
    sql += " ORDER BY id DESC"
    rows = fetchall(sql)

    conn = db()
    try:
        result = []
        for row in rows:
            item = clean_shop(row, conn)
            hay = " ".join([item["name"], item["city"], item["category"],
                            item["description"], " ".join(item["tags"])]).lower()
            if search and search not in hay:  continue
            if category and item["category"].lower() != category: continue
            if city and city not in item["city"].lower(): continue
            result.append(item)
        return jsonify(result)
    finally:
        conn.close()


@app.get("/api/shops/<int:shop_id>")
def shop_detail(shop_id):
    row = fetchone("SELECT * FROM shops WHERE id=%s", (shop_id,))
    if not row:
        return jsonify({"message": "Shop not found"}), 404
    return jsonify(clean_shop(row))


# ─────────────────────────────────────────────────────────────────────
#  REVIEWS
# ─────────────────────────────────────────────────────────────────────
@app.get("/api/shops/<int:shop_id>/reviews")
def shop_reviews(shop_id):
    if not fetchone("SELECT 1 AS ok FROM shops WHERE id=%s", (shop_id,)):
        return jsonify({"message": "Shop not found"}), 404
    rows = fetchall(
        "SELECT * FROM reviews WHERE shop_id=%s ORDER BY created_at DESC",
        (shop_id,),
    )
    conn = db()
    try:
        avg, count = rating_for(conn, shop_id)
    finally:
        conn.close()
    return jsonify({
        "rating":      avg,
        "reviewCount": count,
        "reviews":     [clean_review(r) for r in rows],
    })


@app.post("/api/shops/<int:shop_id>/reviews")
@require_user_auth
def add_review(shop_id):
    data = request.get_json(silent=True) or {}
    comment = (data.get("comment") or "").strip()
    try:
        rating = int(data.get("rating"))
    except (TypeError, ValueError):
        rating = 0
    if rating not in range(1, 6) or not comment:
        return jsonify({"message": "Rating (1–5) and a comment are required."}), 400

    user_id = session.get("user_id") or data.get("userId")
    reviewer_name = (data.get("reviewerName") or "").strip()

    if not fetchone("SELECT 1 AS ok FROM shops WHERE id=%s", (shop_id,)):
        return jsonify({"message": "Shop not found"}), 404

    if user_id:
        u = fetchone("SELECT * FROM users WHERE id=%s", (user_id,))
        if u:
            reviewer_name = u["name"]
        else:
            user_id = None
    if not reviewer_name:
        reviewer_name = "LocalLink User"

    rid = execute(
        "INSERT INTO reviews(shop_id,user_id,reviewer_name,rating,comment) "
        "VALUES(%s,%s,%s,%s,%s)",
        (shop_id, user_id, reviewer_name, rating, comment),
    )
    review = fetchone("SELECT * FROM reviews WHERE id=%s", (rid,))
    conn = db()
    try:
        avg, count = rating_for(conn, shop_id)
    finally:
        conn.close()
    return jsonify({
        "message":     "Review submitted",
        "review":      clean_review(review),
        "rating":      avg,
        "reviewCount": count,
    }), 201


@app.get("/api/users/<int:user_id>/reviews")
def user_reviews(user_id):
    rows = fetchall("""
        SELECT r.*, s.shop_name FROM reviews r
        JOIN shops s ON s.id = r.shop_id
        WHERE r.user_id=%s ORDER BY r.created_at DESC
    """, (user_id,))
    return jsonify([{**clean_review(r), "shopName": r["shop_name"]} for r in rows])


# ─────────────────────────────────────────────────────────────────────
#  ADMIN
# ─────────────────────────────────────────────────────────────────────
@app.post("/api/admin/login")
def admin_login():
    data = request.get_json(silent=True) or {}
    email    = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    row = fetchone("SELECT * FROM users WHERE email=%s AND is_admin=1", (email,))
    if not row or not check_password_hash(row["password_hash"], password):
        return jsonify({"message": "Invalid admin credentials."}), 401
    session["user_id"] = row["id"]
    return jsonify({"message": "Admin login successful", "user": clean_user(row)})


@app.get("/api/admin/stats")
@require_admin
def admin_stats():
    def count(sql, params=()):
        r = fetchone(sql, params)
        return int(next(iter(r.values())))
    return jsonify({
        "totalUsers":    count("SELECT COUNT(*) AS c FROM users WHERE is_admin=0"),
        "totalShops":    count("SELECT COUNT(*) AS c FROM shops"),
        "verifiedShops": count("SELECT COUNT(*) AS c FROM shops WHERE is_verified=1"),
        "pendingShops":  count("SELECT COUNT(*) AS c FROM shops WHERE is_verified=0"),
        "totalReviews":  count("SELECT COUNT(*) AS c FROM reviews"),
    })


@app.get("/api/admin/shops")
@require_admin
def admin_shops():
    status = (request.args.get("status") or "").strip().lower()
    sql = "SELECT * FROM shops"
    if status == "pending":
        sql += " WHERE is_verified=0"
    elif status == "verified":
        sql += " WHERE is_verified=1"
    elif status == "inactive":
        sql += " WHERE is_active=0"
    sql += " ORDER BY id DESC"
    rows = fetchall(sql)
    conn = db()
    try:
        return jsonify([clean_shop(r, conn) for r in rows])
    finally:
        conn.close()


@app.post("/api/admin/shops/<int:shop_id>/approve")
@require_admin
def admin_approve(shop_id):
    if not fetchone("SELECT 1 AS ok FROM shops WHERE id=%s", (shop_id,)):
        return jsonify({"message": "Shop not found"}), 404
    execute(
        "UPDATE shops SET is_verified=1, is_active=1, rejection_reason=NULL "
        "WHERE id=%s", (shop_id,)
    )
    row = fetchone("SELECT * FROM shops WHERE id=%s", (shop_id,))
    return jsonify({"message": "Shop approved", "shop": clean_shop(row)})


@app.post("/api/admin/shops/<int:shop_id>/reject")
@require_admin
def admin_reject(shop_id):
    data = request.get_json(silent=True) or {}
    reason = (data.get("reason") or "").strip() or "Did not meet platform guidelines"
    if not fetchone("SELECT 1 AS ok FROM shops WHERE id=%s", (shop_id,)):
        return jsonify({"message": "Shop not found"}), 404
    execute(
        "UPDATE shops SET is_verified=0, is_active=0, rejection_reason=%s WHERE id=%s",
        (reason, shop_id),
    )
    row = fetchone("SELECT * FROM shops WHERE id=%s", (shop_id,))
    return jsonify({"message": "Shop rejected", "shop": clean_shop(row)})


@app.post("/api/admin/shops/<int:shop_id>/toggle")
@require_admin
def admin_toggle_shop(shop_id):
    if not fetchone("SELECT 1 AS ok FROM shops WHERE id=%s", (shop_id,)):
        return jsonify({"message": "Shop not found"}), 404
    execute("UPDATE shops SET is_active = 1 - is_active WHERE id=%s", (shop_id,))
    row = fetchone("SELECT * FROM shops WHERE id=%s", (shop_id,))
    return jsonify({"message": "Shop toggled", "shop": clean_shop(row)})


@app.get("/api/admin/users")
@require_admin
def admin_users():
    rows = fetchall("SELECT * FROM users WHERE is_admin=0 ORDER BY id DESC")
    return jsonify([clean_user(r) for r in rows])


@app.delete("/api/admin/users/<int:user_id>")
@require_admin
def admin_delete_user(user_id):
    if not fetchone("SELECT 1 AS ok FROM users WHERE id=%s AND is_admin=0", (user_id,)):
        return jsonify({"message": "User not found"}), 404
    execute("DELETE FROM users WHERE id=%s", (user_id,))
    return jsonify({"message": "User deleted"})


@app.get("/api/admin/reviews")
@require_admin
def admin_reviews():
    rows = fetchall("""
        SELECT r.*, s.shop_name FROM reviews r
        JOIN shops s ON s.id = r.shop_id
        ORDER BY r.created_at DESC
    """)
    return jsonify([{**clean_review(r), "shopName": r["shop_name"]} for r in rows])


@app.delete("/api/admin/reviews/<int:review_id>")
@require_admin
def admin_delete_review(review_id):
    if not fetchone("SELECT 1 AS ok FROM reviews WHERE id=%s", (review_id,)):
        return jsonify({"message": "Review not found"}), 404
    execute("DELETE FROM reviews WHERE id=%s", (review_id,))
    return jsonify({"message": "Review deleted"})


# ─────────────────────────────────────────────────────────────────────
#  UPLOADS + FRONTEND
# ─────────────────────────────────────────────────────────────────────
@app.get("/uploads/<path:filename>")
def uploads(filename):
    return send_from_directory(UPLOAD_DIR, filename)


@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/<path:path>")
def frontend(path):
    if path.startswith("api/") or path.startswith("uploads/"):
        return jsonify({"message": "Not found"}), 404
    full = os.path.join(FRONTEND_DIR, path)
    if os.path.isfile(full):
        return send_from_directory(FRONTEND_DIR, path)
    return send_from_directory(FRONTEND_DIR, "index.html")


if __name__ == "__main__":
    try:
        ensure_admin()
    except mysql.connector.Error as e:
        print("\n[X] Cannot connect to MySQL.")
        print(f"    {e}")
        print("    Check MYSQL_CONFIG at the top of app.py, and that")
        print("    'locallink' database exists in MySQL Workbench.\n")
        raise SystemExit(1)
    app.run(debug=True, host="127.0.0.1", port=5000)