import os
import json
import re
import platform
import pytesseract
import webbrowser
import threading
from datetime import datetime
from PIL import Image, ImageFilter, ImageEnhance
from flask import Flask, request, jsonify, send_file, session
from werkzeug.security import generate_password_hash, check_password_hash
import spacy
from langdetect import detect, LangDetectException
from deep_translator import GoogleTranslator
import PyPDF2
import docx

nlp_en = spacy.load("en_core_web_sm")
app = Flask(__name__)
app.secret_key = "mcqportal_secret_key_2025"

if platform.system() == "Windows":
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

DATA_FILE = "course_data.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"users": [], "courses": []}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return {"users": [], "courses": []}
            return json.loads(content)
    except Exception:
        return {"users": [], "courses": []}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def current_user():
    return session.get("user")

def require_login():
    if not session.get("user"):
        return jsonify({"error": "Not logged in"}), 401
    return None

def translate_to_hindi(text):
    try:
        if not text or not text.strip():
            return ""
        return GoogleTranslator(source="en", target="hi").translate(text) or ""
    except Exception:
        return ""

def translate_to_english(text):
    try:
        if not text or not text.strip():
            return ""
        return GoogleTranslator(source="hi", target="en").translate(text) or ""
    except Exception:
        return ""

def preprocess_image(img):
    img = img.convert("L")
    img = ImageEnhance.Contrast(img).enhance(2.5)
    img = ImageEnhance.Sharpness(img).enhance(2.0)
    img = img.filter(ImageFilter.MedianFilter(size=3))
    return img

def split_image(filepath):
    img = Image.open(filepath)
    width, height = img.size
    left  = img.crop((0, 0, width // 2, height))
    right = img.crop((int(width * 0.47), 0, width, height))
    os.makedirs("uploads", exist_ok=True)
    left_path  = "uploads/left_en.png"
    right_path = "uploads/right_hi.png"
    preprocess_image(left).save(left_path)
    preprocess_image(right).save(right_path)
    return left_path, right_path

def extract_text_from_image(filepath, lang):
    img = Image.open(filepath)
    config = "--oem 3 --psm 4"
    return pytesseract.image_to_string(img, lang=lang, config=config)

def extract_text_from_pdf(filepath):
    text = ""
    try:
        with open(filepath, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() + "\n"
    except Exception as e:
        text = ""
    return text

def extract_text_from_docx(filepath):
    text = ""
    try:
        doc = docx.Document(filepath)
        for para in doc.paragraphs:
            text += para.text + "\n"
    except Exception as e:
        text = ""
    return text

def extract_text_from_file(filepath, filename):
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext in ["jpg", "jpeg", "png", "webp"]:
        left_path, right_path = split_image(filepath)
        en_text = extract_text_from_image(left_path, lang="eng")
        hi_text = extract_text_from_image(right_path, lang="hin")
        return en_text, hi_text

    elif ext == "pdf":
        text = extract_text_from_pdf(filepath)
        return text, ""   
    elif ext in ["doc", "docx"]:
        text = extract_text_from_docx(filepath)
        return text, ""   
    return "", ""

def clean_english(text):
    text = text.replace("|", "I").replace("'", "'")
    text = re.sub(r"[~`@#$%^&*_+=<>{}\\]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    doc = nlp_en(text)
    return " ".join([t.text for t in doc if not t.is_space])

def clean_hindi(text):
    text = re.sub(r"[^\u0900-\u097F\s\?\-।,०-९]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def parse_questions(text, language="en"):
    """
    Parses raw OCR text into structured questions.
    Handles question numbers starting from 1, 2, 3...
    Also handles multi-line questions before options.
    """
    questions = []

    if language == "hi":
        text = re.sub(r"\(6\)",   "(A)", text)
        text = re.sub(r"\(8\)\.", "(B)", text)
        text = re.sub(r"\(8\)",   "(B)", text)
        text = re.sub(r"\(0\)\.", "(C)", text)
        text = re.sub(r"\(0\)",   "(C)", text)
        text = re.sub(r"_#",      "(A)", text)
        text = re.sub(r"\(©\)",   "(C)", text)
        text = re.sub(r"\(o\)",   "(C)", text)

    # Normalize option labels spacing
    text = re.sub(r"\(([A-Da-d])\)", r"(\1) ", text)

    # Split into blocks at question numbers like 1. 2. 3. 32. 33.
    blocks = re.split(r"\n(?=\d{1,3}[\.\)]\s)", text.strip())

    for block in blocks:
        lines = [l.strip() for l in block.splitlines() if l.strip()]
        if len(lines) < 2:
            continue

        # Match question number at start like "1." or "32."
        num_match = re.match(r"^(\d{1,3})[\.\)]\s*(.*)", lines[0])
        if not num_match:
            continue

        q_num = int(num_match.group(1))
        if q_num > 200:
            continue

        question_text = num_match.group(2).strip()
        options = {}

        for line in lines[1:]:
            # Match options in all common formats
            opt = re.match(
                r"^\(?([A-Da-d])\)?\s*[\.\)]?\s*(.+)", line
            )
            if opt:
                label = opt.group(1).upper()
                val   = opt.group(2).strip()
                # Remove trailing option labels accidentally included
                val = re.sub(r"\s*\([A-D]\)\s*$", "", val).strip()
                if language == "hi":
                    val = clean_hindi(val)
                else:
                    val = clean_english(val)
                if val and label in ["A","B","C","D"]:
                    options[label] = val
            else:
                # Continuation of question text before options start
                if not options and line:
                    question_text += " " + line

        # Clean question text
        if language == "hi":
            question_text = clean_hindi(question_text)
        else:
            question_text = clean_english(question_text)

        # Remove leading number if accidentally included
        question_text = re.sub(r"^\d+[\.\)]\s*", "", question_text).strip()

        # Only save if we have at least 2 options and valid question
        if len(options) >= 2 and len(question_text) > 5:
            questions.append({
                "q_num":    q_num,
                "question": question_text,
                "options":  options
            })

    return questions

def pair_and_translate(en_list, hi_list):
    hi_dict = {q["q_num"]: q for q in hi_list}
    paired  = []

    for i, en in enumerate(en_list):
        hi = hi_dict.get(en["q_num"])

        en_trans = {
            "question":   en["question"],
            "options":    en["options"],
            "explanation": "",
            "translated": False
        }

        if hi and hi.get("question"):
            hi_trans = {
                "question":   hi["question"],
                "options":    hi["options"],
                "explanation": "",
                "translated": False
            }
        else:
            hi_question = translate_to_hindi(en["question"])
            hi_options  = {lbl: translate_to_hindi(opt) for lbl, opt in en["options"].items()}
            hi_trans = {
                "question":   hi_question,
                "options":    hi_options,
                "explanation": "",
                "translated": True
            }

        paired.append({
            "id":              i + 1,
            "question_number": en["q_num"],
            "question_type":   "multiple_choice",
            "translations":    {"en": en_trans, "hi": hi_trans},
            "correct_answer":  "",
            "difficulty":      "medium",
            "marks":           1,
            "subject":         "",
            "tags":            [],
            "hint":            "",
            "uploaded_by":     current_user(),
            "uploaded_at":     now()
        })
    return paired


@app.route("/")
def index():
    return send_file(os.path.join(os.path.dirname(__file__), "frontend.html"))

@app.route("/api/register", methods=["POST"])
def register():
    body     = request.get_json()
    username = body.get("username", "").strip()
    password = body.get("password", "").strip()
    name     = body.get("name", "").strip()

    if not username or not password or not name:
        return jsonify({"error": "All fields required"}), 400

    data = load_data()
    if any(u["username"] == username for u in data["users"]):
        return jsonify({"error": "Username already exists"}), 400

    user = {
        "id":         len(data["users"]) + 1,
        "username":   username,
        "password":   generate_password_hash(password),
        "name":       name,
        "role":       "teacher",
        "created_at": now()
    }
    data["users"].append(user)
    save_data(data)
    return jsonify({"success": True})

@app.route("/api/login", methods=["POST"])
def login():
    body     = request.get_json()
    username = body.get("username", "").strip()
    password = body.get("password", "").strip()

    data = load_data()
    user = next((u for u in data["users"] if u["username"] == username), None)

    if not user or not check_password_hash(user["password"], password):
        return jsonify({"error": "Invalid username or password"}), 401

    session["user"] = {
        "id":       user["id"],
        "username": user["username"],
        "name":     user["name"],
        "role":     user["role"]
    }
    return jsonify({"success": True, "user": session["user"]})

@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success": True})

@app.route("/api/me", methods=["GET"])
def me():
    user = session.get("user")
    if not user:
        return jsonify({"error": "Not logged in"}), 401
    return jsonify(user)

@app.route("/api/users", methods=["GET"])
def get_users():
    data = load_data()
    return jsonify([
        {"id": u["id"], "username": u["username"], "name": u["name"]}
        for u in data["users"]
    ])

@app.route("/api/courses", methods=["POST"])
def create_course():
    err = require_login()
    if err: return err
    body   = request.get_json()
    data   = load_data()
    user   = current_user()
    course = {
        "id":          len(data["courses"]) + 1,
        "name":        body.get("name", ""),
        "code":        body.get("code", ""),
        "subject":     body.get("subject", ""),
        "difficulty":  body.get("difficulty", "medium"),
        "marks":       body.get("marks", 1),
        "description": body.get("description", ""),
        "skills":      [],
        "lessons":     [],
        "question_sets": [],
        "created_by":  user["name"],
        "created_by_id": user["id"],
        "created_at":  now(),
        "updated_by":  user["name"],
        "updated_at":  now()
    }
    data["courses"].append(course)
    save_data(data)
    return jsonify({"success": True, "course": course})

@app.route("/api/courses", methods=["GET"])
def get_courses():
    data = load_data()
    return jsonify(data.get("courses", []))

@app.route("/api/courses/<int:course_id>", methods=["GET"])
def get_course(course_id):
    data = load_data()
    for c in data["courses"]:
        if c["id"] == course_id:
            return jsonify(c)
    return jsonify({"error": "Not found"}), 404

@app.route("/api/courses/<int:course_id>", methods=["PUT"])
def update_course(course_id):
    err = require_login()
    if err: return err
    body = request.get_json()
    data = load_data()
    user = current_user()
    for i, c in enumerate(data["courses"]):
        if c["id"] == course_id:
            c.update({
                "name":        body.get("name", c["name"]),
                "code":        body.get("code", c["code"]),
                "subject":     body.get("subject", c["subject"]),
                "difficulty":  body.get("difficulty", c["difficulty"]),
                "marks":       body.get("marks", c["marks"]),
                "description": body.get("description", c["description"]),
                "updated_by":  user["name"],
                "updated_at":  now()
            })
            data["courses"][i] = c
            save_data(data)
            return jsonify({"success": True})
    return jsonify({"error": "Not found"}), 404

@app.route("/api/courses/<int:course_id>/skills", methods=["POST"])
def add_skill(course_id):
    err = require_login()
    if err: return err
    data  = load_data()
    user  = current_user()
    body  = request.get_json()
    for c in data["courses"]:
        if c["id"] == course_id:
            skill = {
                "id":          len(c["skills"]) + 1,
                "name":        body.get("name", ""),
                "description": body.get("description", ""),
                "added_by":    user["name"],
                "added_at":    now()
            }
            c["skills"].append(skill)
            c["updated_by"] = user["name"]
            c["updated_at"] = now()
            save_data(data)
            return jsonify({"success": True, "skill": skill})
    return jsonify({"error": "Course not found"}), 404

@app.route("/api/courses/<int:course_id>/skills", methods=["GET"])
def get_skills(course_id):
    data = load_data()
    for c in data["courses"]:
        if c["id"] == course_id:
            return jsonify(c.get("skills", []))
    return jsonify([])

@app.route("/api/courses/<int:course_id>/lessons", methods=["POST"])
def add_lesson(course_id):
    err = require_login()
    if err: return err
    data = load_data()
    user = current_user()
    body = request.get_json()

    for c in data["courses"]:
        if c["id"] == course_id:
            lesson = {
                "id":       len(c["lessons"]) + 1,
                "sl_no":    body.get("sl_no", len(c["lessons"]) + 1),
                "name":     body.get("name", ""),
                "summary":  body.get("summary", ""),
                "added_by": user["name"],
                "added_at": now()
            }
            c["lessons"].append(lesson)
            c["updated_by"] = user["name"]
            c["updated_at"] = now()
            save_data(data)
            return jsonify({"success": True, "lesson": lesson})
    return jsonify({"error": "Course not found"}), 404

@app.route("/api/courses/<int:course_id>/lessons", methods=["GET"])
def get_lessons(course_id):
    data = load_data()
    for c in data["courses"]:
        if c["id"] == course_id:
            return jsonify(c.get("lessons", []))
    return jsonify([])

@app.route("/api/courses/<int:course_id>/question_sets", methods=["POST"])
def save_question_set(course_id):
    err = require_login()
    if err: return err
    data = load_data()
    user = current_user()
    body = request.get_json()
    qset = body.get("question_set", {})

    for c in data["courses"]:
        if c["id"] == course_id:
            qset["id"]          = len(c["question_sets"]) + 1
            qset["created_by"]  = user["name"]
            qset["created_at"]  = now()
            qset["updated_by"]  = user["name"]
            qset["updated_at"]  = now()
            qset["edit_history"] = [{
                "action":    "created",
                "by":        user["name"],
                "at":        now()
            }]
            c["question_sets"].append(qset)
            c["updated_by"] = user["name"]
            c["updated_at"] = now()
            save_data(data)
            return jsonify({"success": True, "id": qset["id"]})
    return jsonify({"error": "Course not found"}), 404

@app.route("/api/courses/<int:course_id>/question_sets", methods=["GET"])
def get_question_sets(course_id):
    data = load_data()
    for c in data["courses"]:
        if c["id"] == course_id:
            return jsonify(c.get("question_sets", []))
    return jsonify([])

@app.route("/api/courses/<int:course_id>/question_sets/<int:set_id>", methods=["GET"])
def get_question_set(course_id, set_id):
    data = load_data()
    for c in data["courses"]:
        if c["id"] == course_id:
            for qs in c.get("question_sets", []):
                if qs["id"] == set_id:
                    return jsonify(qs)
    return jsonify({"error": "Not found"}), 404

@app.route("/api/courses/<int:course_id>/question_sets/<int:set_id>", methods=["PUT"])
def update_question_set(course_id, set_id):
    err = require_login()
    if err: return err
    data = load_data()
    user = current_user()
    body = request.get_json()

    for c in data["courses"]:
        if c["id"] == course_id:
            for i, qs in enumerate(c["question_sets"]):
                if qs["id"] == set_id:
                    body["id"]         = set_id
                    body["created_by"] = qs.get("created_by", user["name"])
                    body["created_at"] = qs.get("created_at", now())
                    body["updated_by"] = user["name"]
                    body["updated_at"] = now()
                    history = qs.get("edit_history", [])
                    history.append({
                        "action": "edited",
                        "by":     user["name"],
                        "at":     now()
                    })
                    body["edit_history"] = history
                    c["question_sets"][i] = body
                    c["updated_by"] = user["name"]
                    c["updated_at"] = now()
                    save_data(data)
                    return jsonify({"success": True})
    return jsonify({"error": "Not found"}), 404

@app.route("/api/courses/<int:course_id>/question_sets/<int:set_id>", methods=["DELETE"])
def delete_question_set(course_id, set_id):
    err = require_login()
    if err: return err
    data = load_data()
    for c in data["courses"]:
        if c["id"] == course_id:
            c["question_sets"] = [qs for qs in c["question_sets"] if qs["id"] != set_id]
            save_data(data)
            return jsonify({"success": True})
    return jsonify({"error": "Not found"}), 404

@app.route("/upload", methods=["POST"])
def upload():
    try:
        files = request.files.getlist("files")
        if not files:
            return jsonify({"error": "No files uploaded"}), 400

        os.makedirs("uploads", exist_ok=True)
        all_en_questions = []
        all_hi_questions = []

        for file in files:
            if not file.filename:
                continue

            filepath = os.path.join("uploads", file.filename)
            file.save(filepath)

            en_text, hi_text = extract_text_from_file(filepath, file.filename)

            en_qs = parse_questions(en_text, language="en")
            hi_qs = parse_questions(hi_text, language="hi") if hi_text else []

            offset = len(all_en_questions)
            for q in en_qs:
                q["q_num"] += offset
            for q in hi_qs:
                q["q_num"] += offset

            all_en_questions.extend(en_qs)
            all_hi_questions.extend(hi_qs)

        if not all_en_questions:
            return jsonify({"error": "No questions found in uploaded files."}), 400

        paired = pair_and_translate(all_en_questions, all_hi_questions)

        frontend_questions = []
        for q in paired:
            en = q["translations"]["en"]
            hi = q["translations"]["hi"]
            frontend_questions.append({
                "id":             q["id"],
                "question":       en["question"],
                "options":        list(en["options"].values()),
                "hindi_question": hi["question"],
                "hindi_options":  list(hi["options"].values()),
                "hi_translated":  hi["translated"],
                "en_translated":  en["translated"],
                "answer":         -1
            })

        return jsonify({"success": True, "questions": frontend_questions})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/courses/<int:course_id>/question_sets/<int:set_id>/add_questions", methods=["POST"])
def add_more_questions(course_id, set_id):
    err = require_login()
    if err: return err

    try:
        files = request.files.getlist("files")
        if not files:
            return jsonify({"error": "No files uploaded"}), 400

        os.makedirs("uploads", exist_ok=True)
        all_en_questions = []
        all_hi_questions = []

        for file in files:
            if not file.filename:
                continue
            filepath = os.path.join("uploads", file.filename)
            file.save(filepath)
            en_text, hi_text = extract_text_from_file(filepath, file.filename)
            all_en_questions.extend(parse_questions(en_text, language="en"))
            if hi_text:
                all_hi_questions.extend(parse_questions(hi_text, language="hi"))

        if not all_en_questions:
            return jsonify({"error": "No questions found."}), 400

        new_questions = pair_and_translate(all_en_questions, all_hi_questions)

        frontend_questions = []
        for q in new_questions:
            en = q["translations"]["en"]
            hi = q["translations"]["hi"]
            frontend_questions.append({
                "id":             q["id"],
                "question":       en["question"],
                "options":        list(en["options"].values()),
                "hindi_question": hi["question"],
                "hindi_options":  list(hi["options"].values()),
                "hi_translated":  hi["translated"],
                "en_translated":  en["translated"],
                "answer":         -1
            })

        return jsonify({"success": True, "questions": frontend_questions})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/translate", methods=["POST"])
def translate():
    try:
        body      = request.get_json()
        text      = body.get("text", "")
        direction = body.get("direction", "en_to_hi")
        result    = translate_to_hindi(text) if direction == "en_to_hi" else translate_to_english(text)
        return jsonify({"success": True, "translated": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/submit", methods=["POST"])
def submit():
    body         = request.get_json()
    user_answers = body.get("answers", {})
    questions    = body.get("questions", [])
    score        = 0
    results      = []

    for i, q in enumerate(questions):
        user_ans      = user_answers.get(str(i), -1)
        correct_label = q.get("answer", "")
        correct_index = ["A","B","C","D"].index(correct_label) if correct_label in ["A","B","C","D"] else -1
        is_correct    = correct_index >= 0 and user_ans == correct_index
        if is_correct:
            score += 1
        results.append({
            "question":       q.get("question",""),
            "options":        q.get("options",[]),
            "user_answer":    user_ans,
            "correct_answer": correct_index,
            "is_correct":     is_correct
        })

    total = len(questions)
    return jsonify({
        "score":      score,
        "total":      total,
        "percentage": round((score / total) * 100) if total else 0,
        "results":    results
    })

@app.route("/debug_ocr", methods=["POST"])
def debug_ocr():
    """Debug route to see raw OCR output."""
    try:
        file = request.files.get("file")
        if not file:
            return jsonify({"error": "No file"}), 400
        os.makedirs("uploads", exist_ok=True)
        filepath = os.path.join("uploads", file.filename)
        file.save(filepath)
        left_path, right_path = split_image(filepath)
        en_text = extract_text_from_image(left_path, lang="eng")
        hi_text = extract_text_from_image(right_path, lang="hin")
        en_questions = parse_questions(en_text, language="en")
        hi_questions = parse_questions(hi_text, language="hi")
        return jsonify({
            "en_raw": en_text,
            "hi_raw": hi_text,
            "en_questions_found": len(en_questions),
            "hi_questions_found": len(hi_questions),
            "en_questions": en_questions,
            "hi_questions": hi_questions
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    threading.Timer(1.5, lambda: webbrowser.open(f"http://localhost:{port}")).start()
    app.run(host="0.0.0.0", port=port, debug=True)