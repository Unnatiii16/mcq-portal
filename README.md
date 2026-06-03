# MCQ Portal — Bilingual Question Paper Extractor

A professional LMS-style web application that extracts MCQ questions from uploaded question paper images using OCR and NLP, supports both English and Hindi languages, and provides an interactive quiz portal.

---

## Features

- Upload question paper photo → AI extracts questions automatically
- Bilingual support — English and Hindi questions side by side
- Auto translation — missing Hindi/English auto-translated using Google Translate
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
| Data | JSON files |

---

## Project Structure
---

## Installation & Setup

### 1. Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/mcq-portal.git
cd mcq-portal
```

### 2. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 3. Install Tesseract OCR

**Windows:**
- Download from: https://github.com/UB-Mannheim/tesseract/wiki
- Install and note the path: `C:\Program Files\Tesseract-OCR\tesseract.exe`
- Download Hindi language file `hin.traineddata` from https://github.com/tesseract-ocr/tessdata
- Copy to `C:\Program Files\Tesseract-OCR\tessdata\`

### 4. Download spaCy model
```bash
python -m spacy download en_core_web_sm
```

### 5. Run the application
```bash
python app.py
```

Open browser and go to: **http://localhost:5000**

---

## How It Works
Upload question paper image
↓
Image split into left (English) and right (Hindi) halves
↓
Tesseract OCR reads text from both halves
↓
spaCy NLP cleans English text
Regex cleans Hindi Devanagari text
↓
Questions and options extracted and paired
↓
Missing translations auto-filled using Google Translate
↓
User reviews and corrects questions
↓
Saved to course_data.json
↓
Quiz portal available for students

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
| GET | /api/question_sets/<id> | Get single question set |
| PUT | /api/question_sets/<id> | Update question set |
| DELETE | /api/question_sets/<id> | Delete question set |
| POST | /submit | Submit quiz answers |

---

## JSON Data Format

```json
{
  "course": {
    "name": "General Knowledge 2025",
    "subject": "General Knowledge",
    "difficulty": "medium"
  },
  "skills": [
    { "id": 1, "name": "Current Affairs", "description": "..." }
  ],
  "lessons": [
    { "id": 1, "name": "Lesson 1", "summary": "..." }
  ],
  "question_sets": [
    {
      "id": 1,
      "name": "Practice Set 1",
      "questions": [
        {
          "id": 1,
          "question_type": "multiple_choice",
          "translations": {
            "en": { "question": "...", "options": { "A": "...", "B": "..." } },
            "hi": { "question": "...", "options": { "A": "...", "B": "..." }, "translated": true }
          },
          "correct_answer": "A",
          "marks": 1
        }
      ]
    }
  ]
}
```

---

## Deployment on Render

1. Push code to GitHub
2. Go to render.com → New → Web Service
3. Connect your GitHub repository
4. Set Build Command:
pip install -r requirements.txt && python -m spacy download en_core_web_sm
5. Set Start Command:
gunicorn app:app
6. Deploy ✅

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

Build by Unnati Sawant