import os
import pdfplumber
import json
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise Exception("❌ OPENAI_API_KEY is missing in .env")

client = OpenAI(api_key=OPENAI_API_KEY)

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def home():
    return "✅ Adaptiq AI backend (OpenAI) is live."

@app.route('/generate-quiz', methods=['POST'])
def generate_quiz_from_pdf():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']
    if not file.filename.endswith('.pdf'):
        return jsonify({"error": "Only PDF files are supported"}), 400

    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)

    try:
        with pdfplumber.open(filepath) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)

        if not text.strip():
            return jsonify({"error": "PDF has no extractable text"}), 400

        text = text[:3000]

        max_retries = 2  
        for attempt in range(max_retries):
            try:
                prompt = f"""
From the following text, generate exactly 10 multiple-choice questions. 
Each should be in the following JSON format:

{{
  "QuestionId": 0,
  "Comp_body": "...context...",
  "Question": "...the MCQ...",
  "Opt_1": "...",
  "Opt_2": "...",
  "Opt_3": "...",
  "Opt_4": "...",
  "Correct_answer": "..."
}}

Return ONLY the JSON array.

TEXT:
\"\"\"{text}\"\"\"
"""

                response = client.chat.completions.create(
                    model="gpt-4",  # Change to "gpt-3.5-turbo" if needed
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7
                )

                raw_output = response.choices[0].message.content.strip()
                questions = json.loads(raw_output)
                return jsonify(questions)

            except json.JSONDecodeError:
                if attempt < max_retries - 1:
                    continue  # Try again if not the last attempt
                return jsonify({
                    "error": "Failed to generate valid JSON after multiple attempts.",
                    "raw_output": raw_output
                }), 500
            except Exception as e:
                if attempt < max_retries - 1:
                    continue  # Try again if not the last attempt
                return jsonify({"error": str(e)}), 403

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
