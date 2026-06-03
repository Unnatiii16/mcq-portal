import os
import json
import re
import platform
import pytesseract
import webbrowser
import threading
from PIL import Image, ImageFilter, ImageEnhance
from flask import Flask, request, jsonify, send_file
import spacy
from langdetect import detect, LangDetectException
from deep_translator import GoogleTranslator

nlp_en = spacy.load("en_core_web_sm")
app = Flask(__name__)

if platform.system() == "Windows":
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

DATA_FILE = "course_data.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {
            "course": {},
            "skills": [],
            "lessons": [],
            "question_sets": []
        }
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def translate_to_hindi(text):
    try:
        if not text or not text.strip():
            return ""
        result = GoogleTranslator(source="en", target="hi").translate(text)
        return result or ""
    except Exception:
        return ""

def translate_to_english(text):
    try:
        if not text or not text.strip():
            return ""
        result = GoogleTranslator(source="hi", target="en").translate(text)
        return result or ""
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
    mid = width // 2
    left  = img.crop((0,   0, mid,   height))
    right = img.crop((int(width * 0.47), 0, width, height))
    os.makedirs("uploads", exist_ok=True)
    left_path  = "uploads/left_en.png"
    right_path = "uploads/right_hi.png"
    preprocess_image(left).save(left_path)
    preprocess_image(right).save(right_path)
    return left_path, right_path

def extract_text(filepath, lang):
    img = Image.open(filepath)
    config = "--oem 3 --psm 4"
    return pytesseract.image_to_string(img, lang=lang, config=config)

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
    questions = []
    if language == "hi":
        text = re.sub(r"\(6\)",   "(A)", text)
        text = re.sub(r"\(8\)\.", "(B)", text)
        text = re.sub(r"\(8\)",   "(B)", text)
        text = re.sub(r"\(0\)\.", "(C)", text)
        text = re.sub(r"\(0\)",   "(C)", text)
        text = re.sub(r"_#",      "(A)", text)
        text = re.sub(r"^\.\.\s*",   "32. ", text, flags=re.MULTILINE)
        text = re.sub(r"^\)\s*,\s*", "33. ", text, flags=re.MULTILINE)

    blocks = re.split(r"\n(?=\d{1,3}[\.\)]\s)", text.strip())
    for block in blocks:
        lines = [l.strip() for l in block.splitlines() if l.strip()]
        if len(lines) < 2:
            continue
        num_match = re.match(r"^(\d{1,3})[\.\)]\s*(.*)", lines[0])
        if not num_match:
            continue
        q_num = int(num_match.group(1))
        if q_num > 200:
            continue
        question_text = num_match.group(2).strip()
        options = {}

        for line in lines[1:]:
            opt = re.match(r"^\(?([A-Da-d])\)?[\.\)\s]\s*(.+)", line)
            if opt:
                label = opt.group(1).upper()
                val   = opt.group(2).strip()
                val   = clean_hindi(val) if language == "hi" else clean_english(val)
                if val and label in ["A","B","C","D"]:
                    options[label] = val
            else:
                if not options and line:
                    question_text += " " + line

        if language == "hi":
            question_text = clean_hindi(question_text)
        else:
            question_text = clean_english(question_text)

        question_text = re.sub(r"^\d+\s*", "", question_text).strip()

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
            "question":    en["question"],
            "options":     en["options"],
            "explanation": "",
            "translated":  False
        }

        if hi and hi.get("question"):
            hi_trans = {
                "question":    hi["question"],
                "options":     hi["options"],
                "explanation": "",
                "translated":  False
            }
        else:
            hi_question = translate_to_hindi(en["question"])
            hi_options  = {}
            for lbl, opt in en["options"].items():
                hi_options[lbl] = translate_to_hindi(opt)
            hi_trans = {
                "question":    hi_question,
                "options":     hi_options,
                "explanation": "",
                "translated":  True  
            }

        paired.append({
            "id":              i + 1,
            "question_number": en["q_num"],
            "question_type":   "multiple_choice",
            "translations": {
                "en": en_trans,
                "hi": hi_trans
            },
            "correct_answer": "",
            "difficulty":     "medium",
            "marks":          1,
            "subject":        ""
        })
    return paired

@app.route("/")
def index():
    return send_file(os.path.join(os.path.dirname(__file__), "frontend.html"))

@app.route("/api/course", methods=["POST"])
def save_course():
    data = load_data()
    data["course"] = request.get_json()
    save_data(data)
    return jsonify({"success": True})

@app.route("/api/course", methods=["GET"])
def get_course():
    data = load_data()
    return jsonify(data)

@app.route("/api/skills", methods=["POST"])
def add_skill():
    data  = load_data()
    skill = request.get_json()
    skill["id"] = len(data["skills"]) + 1
    data["skills"].append(skill)
    save_data(data)
    return jsonify({"success": True, "skill": skill})

@app.route("/api/skills", methods=["GET"])
def get_skills():
    data = load_data()
    return jsonify(data.get("skills", []))

@app.route("/api/lessons", methods=["POST"])
def add_lesson():
    data   = load_data()
    lesson = request.get_json()
    lesson["id"] = len(data["lessons"]) + 1
    data["lessons"].append(lesson)
    save_data(data)
    return jsonify({"success": True, "lesson": lesson})

@app.route("/api/lessons", methods=["GET"])
def get_lessons():
    data = load_data()
    return jsonify(data.get("lessons", []))

@app.route("/upload", methods=["POST"])
def upload():
    try:
        file = request.files.get("image")
        if not file:
            return jsonify({"error": "No image uploaded"}), 400

        os.makedirs("uploads", exist_ok=True)
        filepath = os.path.join("uploads", file.filename)
        file.save(filepath)

        left_path, right_path = split_image(filepath)

        en_text = extract_text(left_path,  lang="eng")
        hi_text = extract_text(right_path, lang="hin")

        en_questions = parse_questions(en_text,  language="en")
        hi_questions = parse_questions(hi_text,  language="hi")

        paired = pair_and_translate(en_questions, hi_questions)

        if not paired:
            return jsonify({"error": "No questions found. Try a clearer image."}), 400

        frontend_questions = []
        for q in paired:
            en = q["translations"]["en"]
            hi = q["translations"]["hi"]
            frontend_questions.append({
                "id":              q["id"],
                "question":        en["question"],
                "options":         list(en["options"].values()),
                "hindi_question":  hi["question"],
                "hindi_options":   list(hi["options"].values()),
                "hi_translated":   hi["translated"],
                "en_translated":   en["translated"],
                "answer":          -1
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

        if direction == "en_to_hi":
            result = translate_to_hindi(text)
        else:
            result = translate_to_english(text)

        return jsonify({"success": True, "translated": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/question_sets", methods=["POST"])
def save_question_set():
    try:
        body   = request.get_json()
        data   = load_data()
        qset   = body.get("question_set", {})
        qset["id"] = len(data["question_sets"]) + 1
        data["question_sets"].append(qset)
        save_data(data)
        return jsonify({"success": True, "id": qset["id"]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/question_sets", methods=["GET"])
def get_question_sets():
    data = load_data()
    return jsonify(data.get("question_sets", []))

@app.route("/api/question_sets/<int:set_id>", methods=["GET"])
def get_question_set(set_id):
    data = load_data()
    for qs in data.get("question_sets", []):
        if qs["id"] == set_id:
            return jsonify(qs)
    return jsonify({"error": "Not found"}), 404

@app.route("/api/question_sets/<int:set_id>", methods=["PUT"])
def update_question_set(set_id):
    try:
        body = request.get_json()
        data = load_data()
        for i, qs in enumerate(data["question_sets"]):
            if qs["id"] == set_id:
                body["id"] = set_id
                data["question_sets"][i] = body
                save_data(data)
                return jsonify({"success": True})
        return jsonify({"error": "Not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/question_sets/<int:set_id>", methods=["DELETE"])
def delete_question_set(set_id):
    data = load_data()
    data["question_sets"] = [qs for qs in data["question_sets"] if qs["id"] != set_id]
    save_data(data)
    return jsonify({"success": True})

@app.route("/submit", methods=["POST"])
def submit():
    body         = request.get_json()
    user_answers = body.get("answers", {})
    questions    = body.get("questions", [])

    score   = 0
    results = []

    for i, q in enumerate(questions):
        user_ans      = user_answers.get(str(i), -1)
        correct_label = q.get("answer", "")
        correct_index = -1

        if correct_label in ["A","B","C","D"]:
            correct_index = ["A","B","C","D"].index(correct_label)

        is_correct = correct_index >= 0 and user_ans == correct_index
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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    threading.Timer(1.5, lambda: webbrowser.open(f"http://localhost:{port}")).start()
    app.run(host="0.0.0.0", port=port, debug=True)