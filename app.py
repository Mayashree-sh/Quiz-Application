
from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import os

app = Flask(__name__)

DATABASE = os.path.join(os.path.dirname(__file__), "quiz.db")


# Connect to the database
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# Create database tables
def create_database():
    conn = get_db_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            option_a TEXT NOT NULL,
            option_b TEXT NOT NULL,
            option_c TEXT NOT NULL,
            option_d TEXT NOT NULL,
            correct_answer TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS quiz_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT NOT NULL,
            score INTEGER NOT NULL,
            total INTEGER NOT NULL,
            quiz_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


# Login page
@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if username == "student" and password == "quiz123":
            return redirect(url_for("dashboard"))

        return render_template(
            "login.html",
            error="Invalid username or password. Please try again."
        )

    return render_template("login.html")


# Dashboard
@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


# Take quiz and save result
@app.route("/quiz", methods=["GET", "POST"])
def quiz():
    conn = get_db_connection()

    questions = conn.execute(
        "SELECT * FROM questions ORDER BY id"
    ).fetchall()

    if request.method == "POST":
        score = 0
        total = len(questions)

        for q in questions:
            selected_answer = request.form.get(
                f"question_{q['id']}", ""
            )

            if selected_answer == q["correct_answer"]:
                score += 1

        # Save the result in the database
        conn.execute("""
            INSERT INTO quiz_results
            (student_name, score, total)
            VALUES (?, ?, ?)
        """, ("student", score, total))

        conn.commit()
        conn.close()

        return render_template(
            "result.html",
            score=score,
            total=total
        )

    conn.close()

    return render_template(
        "quiz.html",
        questions=questions
    )


# Add a question
@app.route("/add-question", methods=["GET", "POST"])
def add_question():
    message = ""

    if request.method == "POST":
        question = request.form.get("question", "").strip()
        option_a = request.form.get("option_a", "").strip()
        option_b = request.form.get("option_b", "").strip()
        option_c = request.form.get("option_c", "").strip()
        option_d = request.form.get("option_d", "").strip()
        correct_answer = request.form.get("correct_answer", "").strip()

        if not all([
            question, option_a, option_b,
            option_c, option_d, correct_answer
        ]):
            message = "Please fill in all fields."
        elif correct_answer not in ["A", "B", "C", "D"]:
            message = "Please select a valid correct answer."
        else:
            conn = get_db_connection()

            conn.execute("""
                INSERT INTO questions
                (question, option_a, option_b, option_c,
                 option_d, correct_answer)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                question, option_a, option_b,
                option_c, option_d, correct_answer
            ))

            conn.commit()
            conn.close()

            message = "Question saved successfully!"

    return render_template(
        "add_question.html",
        message=message
    )


# View all questions
@app.route("/view-questions")
def view_questions():
    conn = get_db_connection()

    questions = conn.execute(
        "SELECT * FROM questions ORDER BY id DESC"
    ).fetchall()

    conn.close()

    return render_template(
        "view_questions.html",
        questions=questions
    )


# View quiz history
@app.route("/history")
def history():
    conn = get_db_connection()

    results = conn.execute("""
        SELECT * FROM quiz_results
        ORDER BY quiz_date DESC, id DESC
    """).fetchall()

    conn.close()

    return render_template(
        "quiz_history.html",
        results=results
    )


# Quiz Performance Dashboard
@app.route("/performance")
def performance():
    conn = get_db_connection()

    stats = conn.execute("""
        SELECT
            COUNT(*) AS total_quizzes,
            COALESCE(MAX(
                CASE
                    WHEN total > 0
                    THEN score * 100.0 / total
                    ELSE 0
                END
            ), 0) AS best_percentage,
            COALESCE(AVG(
                CASE
                    WHEN total > 0
                    THEN score * 100.0 / total
                    ELSE NULL
                END
            ), 0) AS average_percentage
        FROM quiz_results
    """).fetchone()

    conn.close()

    return render_template(
        "performance.html",
        stats=stats
    )



# Edit an existing question
@app.route("/edit-question/<int:question_id>", methods=["GET", "POST"])
def edit_question(question_id):
    conn = get_db_connection()

    question = conn.execute(
        "SELECT * FROM questions WHERE id = ?",
        (question_id,)
    ).fetchone()

    if question is None:
        conn.close()
        return "Question not found", 404

    if request.method == "POST":
        question_text = request.form.get("question", "").strip()
        option_a = request.form.get("option_a", "").strip()
        option_b = request.form.get("option_b", "").strip()
        option_c = request.form.get("option_c", "").strip()
        option_d = request.form.get("option_d", "").strip()
        correct_answer = request.form.get("correct_answer", "").strip()

        if not all([
            question_text, option_a, option_b,
            option_c, option_d
        ]) or correct_answer not in ["A", "B", "C", "D"]:
            conn.close()
            return render_template(
                "edit_question.html",
                question=question,
                error="Please fill in every field and select a correct answer."
            )

        conn.execute("""
            UPDATE questions
            SET question = ?,
                option_a = ?,
                option_b = ?,
                option_c = ?,
                option_d = ?,
                correct_answer = ?
            WHERE id = ?
        """, (
            question_text, option_a, option_b,
            option_c, option_d, correct_answer, question_id
        ))

        conn.commit()
        conn.close()

        return redirect(url_for("view_questions"))

    conn.close()

    return render_template(
        "edit_question.html",
        question=question
    )




# Delete a question
@app.route("/delete-question/<int:question_id>", methods=["POST"])
def delete_question(question_id):
    conn = get_db_connection()

    conn.execute(
        "DELETE FROM questions WHERE id = ?",
        (question_id,)
    )

    conn.commit()
    conn.close()

    return redirect(url_for("view_questions"))


# Create database tables when the application starts
create_database()


# Run the application locally
if __name__ == "__main__":
    app.run(debug=True)
