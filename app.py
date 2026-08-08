from flask import Flask, render_template, request, redirect, jsonify, session
from database import get_connection, init_db, get_all_items, delete_item, get_item_by_id, update_item, get_dashboard_stats, get_recommendations
from ocr import extract_text_from_image, find_date_in_text
from translations import translations, CATEGORY_KEY_MAP
import os

app = Flask(__name__)
app.secret_key = "smart-inventory-secret-key-change-later"
init_db()

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def get_lang_and_t():
    lang = session.get("lang", "th")
    t = translations[lang]
    return lang, t


@app.route("/")
def home():
    search = request.args.get("search")
    category = request.args.get("category")
    items = get_all_items(search=search, category=category)

    lang, t = get_lang_and_t()

    return render_template("index.html", items=items, search=search, category=category, t=t, lang=lang, category_map=CATEGORY_KEY_MAP)

@app.route("/set-language/<lang_code>")
def set_language(lang_code):
    if lang_code in translations:
        session["lang"] = lang_code
    return redirect("/")

@app.route("/add-item")
def add_item_form():
    lang, t = get_lang_and_t()
    return render_template("add_item.html", t=t, lang=lang)

@app.route("/add", methods=["POST"])
def add_item():
    name = request.form.get("name")
    category = request.form.get("category")
    expiry_date = request.form.get("expiry_date")

    conn = get_connection()
    conn.execute(
        "INSERT INTO items (name, category, expiry_date) VALUES (?, ?, ?)",
        (name, category, expiry_date)
    )
    conn.commit()
    conn.close()

    return redirect("/")

@app.route("/delete/<int:item_id>")
def delete(item_id):
    delete_item(item_id)
    return redirect("/")

@app.route("/edit/<int:item_id>")
def edit_item_form(item_id):
    item = get_item_by_id(item_id)
    lang, t = get_lang_and_t()
    return render_template("edit_item.html", item=item, t=t, lang=lang)

@app.route("/update/<int:item_id>", methods=["POST"])
def update(item_id):
    name = request.form.get("name")
    category = request.form.get("category")
    expiry_date = request.form.get("expiry_date")

    update_item(item_id, name, category, expiry_date)
    return redirect("/")

@app.route("/dashboard")
def dashboard():
    lang, t = get_lang_and_t()
    stats = get_dashboard_stats()
    recommendations = get_recommendations(t)
    return render_template("dashboard.html", stats=stats, recommendations=recommendations, t=t, lang=lang, category_map=CATEGORY_KEY_MAP)

@app.route("/scan-expiry", methods=["POST"])
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