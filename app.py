from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import uuid
import re

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

questions = []
user_answers = {}
score = 0


@app.route("/")
def home():
    return render_template("index.html")


# --------------------------------------------------
# Загрузка TXT
# --------------------------------------------------
@app.route('/upload', methods=['POST'])
def upload_file():
    global questions, user_answers, score
    user_answers = {}
    score = 0

    if 'file' not in request.files:
        return jsonify({"error": "Нет файла"}), 400

    file = request.files['file']
    filename = secure_filename(file.filename)

    if not filename.endswith(".txt"):
        return jsonify({"error": "Только .txt"}), 400

    file_id = str(uuid.uuid4())
    path = os.path.join(app.config["UPLOAD_FOLDER"], file_id + ".txt")
    file.save(path)

    questions = parse_txt(path)

    return jsonify({
        "questions": questions,
        "total_questions": len(questions)
    })


# --------------------------------------------------
# Парсер TXT — улучшенная версия
# --------------------------------------------------
def parse_txt(path):
    with open(path, "r", encoding="utf-8") as f:
        lines = [line.rstrip() for line in f.readlines()]

    questions = []
    current_q = None

    # Шаблон номера вопроса в начале строки
    q_pattern = re.compile(r"^(\d+)[\.\)\-]\s*(.*)$")

    for line in lines:
        line = line.strip()

        if not line:
            continue

        # -----------------------------
        # Новый вопрос
        # -----------------------------
        match = q_pattern.match(line)
        if match:
            number = match.group(1)
            text = match.group(2)

            # заканчиваем предыдущий вопрос
            if current_q:
                questions.append(current_q)

            current_q = {
                "number": int(number),
                "text": text.strip(),
                "options": [],
                "correct": [],
                "explanation": ""
            }
            continue

        # -----------------------------
        # Варианты ответов
        # -----------------------------
        if current_q:

            # правильный ответ
            if line.startswith("+"):
                opt = line[1:].strip()
                current_q["options"].append(opt)
                current_q["correct"].append(len(current_q["options"]) - 1)
                continue

            # неправильный
            if line.startswith("-"):
                opt = line[1:].strip()
                current_q["options"].append(opt)
                continue

            # многострочный текст вопроса
            current_q["text"] += " " + line

    if current_q:
        questions.append(current_q)

    return questions


# --------------------------------------------------
# Приём ответа
# --------------------------------------------------
@app.route('/submit_answer', methods=['POST'])
def submit_answer():
    global score, user_answers

    data = request.json
    q_index = data.get("question_index")
    selected_texts = data.get("selected_options", [])

    if q_index is None or q_index >= len(questions):
        return jsonify({"error": "Неверный индекс"}), 400

    q = questions[q_index]

    selected_indices = []
    for s in selected_texts:
        if s in q["options"]:
            selected_indices.append(q["options"].index(s))

    is_correct = set(selected_indices) == set(q["correct"])

    if q_index not in user_answers:
        if is_correct:
            score += 1

    user_answers[q_index] = {
        "user_answer": selected_texts,
        "is_correct": is_correct,
        "correct_answer": [q["options"][i] for i in q["correct"]]
    }

    return jsonify({
        "is_correct": is_correct,
        "correct_answers": [q["options"][i] for i in q["correct"]],
        "score": score
    })


# --------------------------------------------------
# Результаты
# --------------------------------------------------
@app.route('/get_results', methods=['GET'])
def get_results():
    detailed = []

    for i, q in enumerate(questions):
        if i in user_answers:
            ua = user_answers[i]["user_answer"]
            detailed.append({
                "question_number": i + 1,
                "question_text": q["text"],
                "user_answer": ua,
                "correct_answer": [q["options"][j] for j in q["correct"]],
                "is_correct": user_answers[i]["is_correct"]
            })
        else:
            detailed.append({
                "question_number": i + 1,
                "question_text": q["text"],
                "user_answer": [],
                "correct_answer": [q["options"][j] for j in q["correct"]],
                "is_correct": False
            })

    return jsonify({
        "score": score,
        "total_questions": len(questions),
        "percentage": round((score / max(len(questions), 1)) * 100),
        "detailed_results": detailed
    })


# --------------------------------------------------
# Reset
# --------------------------------------------------
@app.route('/reset', methods=['GET'])
def reset():
    global questions, user_answers, score
    questions = []
    user_answers = {}
    score = 0
    return jsonify({"status": "reset"})


if __name__ == '__main__':
    app.run(debug=True)
