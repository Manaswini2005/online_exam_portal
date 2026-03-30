import re
from flask import Flask, render_template, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)

app.secret_key = 'secret123'

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    role = db.Column(db.String(20))
class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer)
    question = db.Column(db.String(200))
    option1 = db.Column(db.String(100))
    option2 = db.Column(db.String(100))
    option3 = db.Column(db.String(100))
    option4 = db.Column(db.String(100))
    answer = db.Column(db.String(100))
class Exam(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    status = db.Column(db.String(20), default="Draft")
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
class Result(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer)
    exam_id = db.Column(db.Integer)
    score = db.Column(db.Integer)




with app.app_context():
    db.create_all()

@app.route('/')
def home():
    return redirect('/login')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        role=request.form.get('role')
        pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        if not re.match(pattern, email):
            return render_template('register.html', error="Enter valid email (example@gmail.com)")
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return render_template('register.html', error="Email already registered")

        user = User(name=name, email=email, password=password, role=role)
        db.session.add(user)
        db.session.commit()

        return render_template('login.html', success="Registration successful! Please login")

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()

        # ❌ If user not found
        if not user:
            return render_template('login.html', error="User not found")

        # ❌ If password wrong
        if user.password != password:
            return render_template('login.html', error="Incorrect password")

        # ✅ If login success
        session['user_id'] = user.id
        session['role'] = user.role
        session['name'] = user.name

        if user.role == 'admin':
            return redirect('/admin_dashboard')
        else:
            return redirect('/student_dashboard')

    return render_template('login.html')


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')

    return render_template('dashboard.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')
@app.route('/admin_dashboard')
def admin_dashboard():

    if 'user_id' not in session or session['role'] != 'admin':
        return redirect('/login')

    exams = Exam.query.all()

    exam_data = []

    for exam in exams:
        count = Question.query.filter_by(exam_id=exam.id).count()

        exam_data.append({
            "exam": exam,
            "count": count
        })

    return render_template('admin_dashboard.html', exam_data=exam_data)

@app.route('/student_dashboard')
def student_dashboard():

    if 'user_id' not in session or session['role'] != 'student':
        return redirect('/login')

    exams = Exam.query.all()
    now = datetime.now()

    results = Result.query.filter_by(student_id=session['user_id']).all()

    # ✅ Create dictionary for easy check
    result_dict = {}
    for r in results:
        result_dict[r.exam_id] = r.score

    return render_template('student_dashboard.html',
                           exams=exams,
                           now=now,
                           result_dict=result_dict)



@app.route('/add_question/<int:exam_id>', methods=['GET', 'POST'])
def add_question(exam_id):

    if request.method == 'POST':
        q = request.form.get('question')
        o1 = request.form.get('option1')
        o2 = request.form.get('option2')
        o3 = request.form.get('option3')
        o4 = request.form.get('option4')
        ans = request.form.get('answer')

        new_q = Question(
            exam_id=exam_id,
            question=q,
            option1=o1,
            option2=o2,
            option3=o3,
            option4=o4,
            answer=ans
        )

        db.session.add(new_q)
        db.session.commit()

    # ✅ always send questions
    questions = Question.query.filter_by(exam_id=exam_id).all()

    return render_template('add_question.html',
                           exam_id=exam_id,
                           questions=questions)


@app.route('/create_exam', methods=['GET', 'POST'])
def create_exam():
    if request.method == 'POST':
        title = request.form.get('title')
        start_time = datetime.strptime(request.form.get('start_time'), "%Y-%m-%dT%H:%M")
        end_time = datetime.strptime(request.form.get('end_time'), "%Y-%m-%dT%H:%M")


        exam = Exam(title=title, start_time=start_time, end_time=end_time, status="Active")
        db.session.add(exam)
        db.session.commit()

        # redirect to add questions for this exam
        return redirect(f"/add_question/{exam.id}")

    return render_template('create_exam.html')
@app.route('/finish_exam/<int:exam_id>')
def finish_exam(exam_id):
    exam = Exam.query.get(exam_id)
    if exam:
        exam.status = "Completed"
        db.session.commit()

    return redirect('/admin_dashboard')
@app.route('/exam/<int:exam_id>', methods=['GET', 'POST'])
def exam(exam_id):

    # 🚫 Prevent multiple attempts
    existing = Result.query.filter_by(
        student_id=session['user_id'],
        exam_id=exam_id
    ).first()

    if existing:
        return redirect('/student_dashboard')

    exam = Exam.query.get(exam_id)
    questions = Question.query.filter_by(exam_id=exam_id).all()

    if request.method == 'POST':
        score = 0
        user_answers = {}

        for q in questions:
            selected = request.form.get(f"q{q.id}")
            if selected:
                selected_stripped = selected.strip().lower()
                correct_stripped = q.answer.strip().lower()
                if selected_stripped == correct_stripped:
                    score += 1
                user_answers[q.id] = selected  # store original answer
            else:
                user_answers[q.id] = "Not Answered"

        wrong = len(questions) - score

        result = Result(
            student_id=session['user_id'],
            exam_id=exam_id,
            score=score
        )
        db.session.add(result)
        db.session.commit()

        return render_template('result.html',
                       score=score,
                       total=len(questions),
                       wrong=wrong,
                       questions=questions,
                       user_answers=user_answers)


    return render_template('exam.html',
                           questions=questions,
                           end_time=exam.end_time)



@app.route('/submit_exam/<int:exam_id>', methods=['POST'])
def submit_exam(exam_id):
    questions = Question.query.filter_by(exam_id=exam_id).all()
    score = 0

    for q in questions:
        selected = request.form.get(f"q{q.id}")
        if selected == q.answer:
            score += 1

    return f"Your Score: {score} / {len(questions)}"
@app.route('/view_results/<int:exam_id>')
def view_results(exam_id):
    results = Result.query.filter_by(exam_id=exam_id).all()

    data = []

    for r in results:
        user = User.query.get(r.student_id)
        data.append({
            "name": user.name,
            "score": r.score
        })

    return render_template('view_results.html', data=data)
@app.route('/leaderboard/<int:exam_id>')
def leaderboard(exam_id):

    results = Result.query.filter_by(exam_id=exam_id).all()

    # sort by score (high to low)
    results = sorted(results, key=lambda x: x.score, reverse=True)

    leaderboard_data = []

    rank = 1
    for r in results:
        user = User.query.get(r.student_id)

        leaderboard_data.append({
            "rank": rank,
            "name": user.name,
            "score": r.score
        })

        rank += 1

    return render_template('leaderboard.html',
                           data=leaderboard_data)
@app.route('/delete_question/<int:qid>/<int:exam_id>')
def delete_question(qid, exam_id):

    q = Question.query.get(qid)

    if q:
        db.session.delete(q)
        db.session.commit()

    return redirect(f"/add_question/{exam_id}")

@app.route('/edit_question/<int:qid>', methods=['GET', 'POST'])
def edit_question(qid):

    q = Question.query.get(qid)

    if request.method == 'POST':
        q.question = request.form.get('question')
        q.option1 = request.form.get('option1')
        q.option2 = request.form.get('option2')
        q.option3 = request.form.get('option3')
        q.option4 = request.form.get('option4')
        q.answer = request.form.get('answer')

        db.session.commit()

        return redirect(f"/add_question/{q.exam_id}")

    return render_template('edit_question.html', q=q)
@app.route('/delete_exam/<int:exam_id>')
def delete_exam(exam_id):

    # delete questions first
    Question.query.filter_by(exam_id=exam_id).delete()

    # delete results also (important)
    Result.query.filter_by(exam_id=exam_id).delete()

    exam = Exam.query.get(exam_id)

    if exam:
        db.session.delete(exam)
        db.session.commit()

    return redirect('/admin_dashboard')
@app.route('/edit_exam/<int:exam_id>', methods=['GET', 'POST'])
def edit_exam(exam_id):

    exam = Exam.query.get(exam_id)

    if request.method == 'POST':
        exam.title = request.form.get('title')
        exam.start_time = datetime.strptime(request.form.get('start_time'), "%Y-%m-%dT%H:%M")
        exam.end_time = datetime.strptime(request.form.get('end_time'), "%Y-%m-%dT%H:%M")

        db.session.commit()

        return redirect('/admin_dashboard')

    # ✅ fetch questions
    questions = Question.query.filter_by(exam_id=exam_id).all()

    return render_template('edit_exam.html',
                           exam=exam,
                           questions=questions)


if __name__ == '__main__':
    app.run(debug=True)