# MCQ Portal — Bilingual Question Paper Extractor

A professional LMS-style web application that extracts MCQ questions from uploaded question paper images using OCR and NLP, supports both English and Hindi languages, and provides an interactive quiz portal.

---

## Features

- Upload question paper photo — AI extracts questions automatically
- Bilingual support — English and Hindi questions side by side
- Auto translation — missing Hindi or English auto-translated using Google Translate
- Manual translation — translate per question with one click
- Course management — create courses, add skills, add lessons
- Question sets — linked to lessons and skills
- Review and correct — edit extracted questions before saving
- Quiz portal — take quiz, get score, review answers
- Save, edit, delete question sets
- Bootstrap 5 LMS-style frontend

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python + Flask |
| OCR | Tesseract OCR + pytesseract |
| NLP | spaCy |
| Translation | deep-translator (Google Translate) |
| Frontend | HTML + CSS + Bootstrap 5 + JavaScript |
| Data Storage | JSON files |

---

## Project Structure

mcqPortal/
├── app.py               # Python Flask backend
├── frontend.html        # Bootstrap 5 frontend
├── requirements.txt     # Python dependencies
├── course_data.json     # Auto-created, stores all course data
└── uploads/             # Auto-created, stores uploaded images
---

## Installation and Setup

### 1. Clone the repository
git clone https://github.com/dearbhola/questionimagetojson.git
cd questionimagetojson
### 2. Install Python dependencies
pip install -r requirements.txt
### 3. Install Tesseract OCR on Windows
- Download from: https://github.com/UB-Mannheim/tesseract/wiki
- Install it — default path: C:\Program Files\Tesseract-OCR\tesseract.exe
- Download Hindi language file hin.traineddata from https://github.com/tesseract-ocr/tessdata
- Copy hin.traineddata to: C:\Program Files\Tesseract-OCR\tessdata\
### 4. Download spaCy English model
python -m spacy download en_core_web_sm
### 5. Run the application
python app.py
Open browser and go to: http://localhost:5000

---

## How It Works
Upload question paper image
↓
Image split into left half (English) and right half (Hindi)
↓
Tesseract OCR reads text from both halves
↓
spaCy NLP cleans English text
Regex cleans Hindi Devanagari text
↓
Questions and options extracted and paired by question number
↓
Missing translations auto-filled using Google Translate
Auto-translated questions marked with Auto Translated badge
↓
User reviews and corrects questions
Manual translate buttons available per question
↓
Saved to course_data.json under the course
↓
Quiz portal available for students

---

## Complete Flow
Step 1 — Create Course (name, subject, difficulty, marks)
Step 2 — Add Skills (name and description)
Step 3 — Add Lessons (serial number, name, summary)
Step 4 — Create Question Set (linked to lesson and skill)
Step 5 — Upload Question Paper Image
Step 6 — Review and Correct Extracted Questions
Step 7 — View Saved Question Sets Dashboard

---

## API Endpoints

| Method | Route | Description |
|---|---|---|
| GET | / | Serve frontend |
| POST | /api/course | Save course details |
| GET | /api/course | Get course details |
| POST | /api/skills | Add a skill |
| GET | /api/skills | Get all skills |
| POST | /api/lessons | Add a lesson |
| GET | /api/lessons | Get all lessons |
| POST | /upload | Upload image, extract, translate |
| POST | /translate | Manual translate text |
| POST | /api/question_sets | Save question set |
| GET | /api/question_sets | Get all question sets |
| GET | /api/question_sets/id | Get single question set |
| PUT | /api/question_sets/id | Update question set |
| DELETE | /api/question_sets/id | Delete question set |
| POST | /submit | Submit quiz answers |

---

## JSON Data Format
{
"course": {
"name": "General Knowledge 2025",
"code": "GK-2025",
"subject": "General Knowledge",
"difficulty": "medium",
"marks": 1
},
"skills": [
{
"id": 1,
"name": "Current Affairs",
"description": "Knowledge of recent events"
}
],
"lessons": [
{
"id": 1,
"sl_no": 1,
"name": "Lesson 1",
"summary": "Introduction to General Knowledge"
}
],
"question_sets": [
{
"id": 1,
"name": "Practice Set 1",
"type": "practice",
"difficulty": "medium",
"marks": 1,
"lesson_id": 1,
"skill_id": 1,
"questions": [
{
"id": 1,
"question_type": "multiple_choice",
"translations": {
"en": {
"question": "What is the capital of India?",
"options": {
"A": "Mumbai",
"B": "New Delhi",
"C": "Kolkata",
"D": "Chennai"
},
"explanation": "",
"translated": false
},
"hi": {
"question": "भारत की राजधानी क्या है?",
"options": {
"A": "मुंबई",
"B": "नई दिल्ली",
"C": "कोलकाता",
"D": "चेन्नई"
},
"explanation": "",
"translated": false
}
},
"correct_answer": "B",
"difficulty": "easy",
"marks": 1,
"subject": "General Knowledge"
}
]
}
]
}

---

## Deployment on Render

1. Push code to GitHub
2. Go to render.com and create a New Web Service
3. Connect your GitHub repository
4. Set Build Command:
pip install -r requirements.txt && python -m spacy download en_core_web_sm
5. Set Start Command:
gunicorn app:app
6. Click Deploy

---

## Requirements
flask
pytesseract
pillow
spacy
langdetect
indic-nlp-library
deep-translator
gunicorn

---

## Author

Built by Unnati Sawant