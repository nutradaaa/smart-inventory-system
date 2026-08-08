from flask import Flask, render_template, request, redirect, jsonify, session
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_connection, get_placeholder, init_db, get_all_items, delete_item, get_item_by_id, update_item, get_dashboard_stats, get_recommendations, create_user, get_user_by_username
from ocr import extract_text_from_image, find_date_in_text
from translations import translations, CATEGORY_KEY_MAP
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "smart-inventory-secret-key-change-later")
init_db()

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def get_lang_and_t():
    lang = session.get("lang", "th")
    t = translations[lang]
    return lang, t


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


@app.route("/register", methods=["GET", "POST"])
def register():
    lang, t = get_lang_and_t()

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        existing_user = get_user_by_username(username)
        if existing_user:
            return render_template("register.html", error="ชื่อผู้ใช้นี้มีอยู่แล้ว กรุณาเลือกชื่ออื่น", lang=lang)

        password_hash = generate_password_hash(password, method="pbkdf2:sha256")
        create_user(username, password_hash)

        return redirect("/login")

    return render_template("register.html", error=None, lang=lang)


@app.route("/login", methods=["GET", "POST"])
def login():
    lang, t = get_lang_and_t()

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = get_user_by_username(username)

        if not user or not check_password_hash(user["password_hash"], password):
            return render_template("login.html", error="ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง", lang=lang)

        session["user_id"] = user["id"]
        session["username"] = user["username"]
        return redirect("/")

    return render_template("login.html", error=None, lang=lang)


@app.route("/logout")
def logout():
    session.pop("user_id", None)
    session.pop("username", None)
    return redirect("/login")


@app.route("/")
@login_required
def home():
    search = request.args.get("search")
    category = request.args.get("category")
    user_id = session["user_id"]
    items = get_all_items(user_id, search=search, category=category)

    lang, t = get_lang_and_t()

    return render_template("index.html", items=items, search=search, category=category, t=t, lang=lang, category_map=CATEGORY_KEY_MAP)

@app.route("/set-language/<lang_code>")
def set_language(lang_code):
    if lang_code in translations:
        session["lang"] = lang_code
    return redirect(request.referrer or "/")

@app.route("/add-item")
@login_required
def add_item_form():
    lang, t = get_lang_and_t()
    return render_template("add_item.html", t=t, lang=lang)

@app.route("/add", methods=["POST"])
@login_required
def add_item():
    name = request.form.get("name")
    category = request.form.get("category")
    expiry_date = request.form.get("expiry_date")
    user_id = session["user_id"]

    conn = get_connection()
    cur = conn.cursor()
    p = get_placeholder()
    cur.execute(
        f"INSERT INTO items (user_id, name, category, expiry_date) VALUES ({p}, {p}, {p}, {p})",
        (user_id, name, category, expiry_date)
    )
    conn.commit()
    cur.close()
    conn.close()

    return redirect("/")

@app.route("/delete/<int:item_id>")
@login_required
def delete(item_id):
    user_id = session["user_id"]
    delete_item(item_id, user_id)
    return redirect("/")

@app.route("/edit/<int:item_id>")
@login_required
def edit_item_form(item_id):
    user_id = session["user_id"]
    item = get_item_by_id(item_id, user_id)
    lang, t = get_lang_and_t()
    return render_template("edit_item.html", item=item, t=t, lang=lang)

@app.route("/update/<int:item_id>", methods=["POST"])
@login_required
def update(item_id):
    name = request.form.get("name")
    category = request.form.get("category")
    expiry_date = request.form.get("expiry_date")
    user_id = session["user_id"]

    update_item(item_id, user_id, name, category, expiry_date)
    return redirect("/")

@app.route("/dashboard")
@login_required
def dashboard():
    lang, t = get_lang_and_t()
    user_id = session["user_id"]
    stats = get_dashboard_stats(user_id)
    recommendations = get_recommendations(t, user_id)
    return render_template("dashboard.html", stats=stats, recommendations=recommendations, t=t, lang=lang, category_map=CATEGORY_KEY_MAP)

@app.route("/scan-expiry", methods=["POST"])
@login_required
def scan_expiry():
    image_file = request.files.get("image")

    if not image_file:
        return jsonify({"success": False, "message": "ไม่พบไฟล์ภาพ"})

    image_path = os.path.join(UPLOAD_FOLDER, "temp_scan.jpg")
    image_file.save(image_path)

    text = extract_text_from_image(image_path)
    found_date = find_date_in_text(text)

    os.remove(image_path)

    if found_date:
        return jsonify({"success": True, "date": found_date, "raw_text": text})
    else:
        return jsonify({"success": False, "message": "ไม่พบวันที่ในภาพ", "raw_text": text})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)