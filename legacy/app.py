from flask import Flask, jsonify, render_template, request, redirect, session, url_for, flash
import pandas as pd
import json
from werkzeug.security import generate_password_hash, check_password_hash
import os
import time
import torch
import numpy as np
from train import training, transform
from chatbot import rating
model = training()
app = Flask(__name__)
app.secret_key = 'app_secret_key'

result = []
all_result = []
user_id = 0

@app.route("/", methods=["GET", "POST"])
def index():
    if 'user' in session:
        return redirect(url_for('account')) 
    return render_template("index.html")

# Đăng nhập và đăng ký
def save_user_to_excel(name, email, phone, studytype, password):

    df = pd.read_excel('users.xlsx')
    hashed_password = generate_password_hash(password)
    user_id = 0
    if (len(df.iloc[:, 0]) != 0):
        user_id = df.iloc[len(df.iloc[:, 0]) - 1, 0] + 1
    else:
        user_id = 0
    user_input = [user_id, name, email, phone, studytype, hashed_password]
    new_user = pd.DataFrame([user_input], columns=['id', 'name', 'email', 'phone', 'studytype', 'password'])
    df = pd.concat([df, new_user], ignore_index=True)
    
    df.to_excel('users.xlsx', index=False)


def verify_user(email, password):
    if os.path.exists('users.xlsx'):
        df = pd.read_excel('users.xlsx')
        user = df[df['email'] == email]
        if not user.empty:
            stored_password = user.iloc[0]['password']
            return check_password_hash(stored_password, password)
    return False

def get_studytype_from_db(email):
    df = pd.read_excel('users.xlsx')
    user_row = df[df['email'] == email]
    if not user_row.empty:
        return user_row.iloc[0]['studytype']
    else:
        return None

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        rname = request.form['rname']
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        studytype = request.form['studytype']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        session['studytype1'] = studytype

        if password != confirm_password:
            flash('Mật khẩu không khớp. Vui lòng thử lại.')
            return render_template('register.html', rname=rname, name=name, email=email, phone=phone)

        save_user_to_excel(name, email, phone, studytype, password)
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        if verify_user(email, password):
            session['user'] = email
            session['studytype'] = get_studytype_from_db(email)
            return redirect(url_for('account'))
        else:
            flash('Email hoặc mật khẩu không đúng. Vui lòng thử lại.')
            return redirect(url_for('login'))

    return render_template('login.html')

# Tài liệu
def load_data_from_excel(file):
    df = pd.read_excel(file)
    tai_lieus = {}

    for _, row in df.iterrows():
        tai_lieu = {
            "Subject": row["Subject"],
            "Doc": row["Doc"]
        }
        tai_lieus[row["Type"]] = tai_lieu

    return tai_lieus

tai_lieus = load_data_from_excel('tailieu.xlsx')

@app.route('/account', methods=['GET', 'POST'])
def account():
    if 'user' not in session: 
        flash('Bạn phải đăng nhập để truy cập trang này.')
        return redirect(url_for('login'))

    user_email = session['user']
    if request.method == "POST":
        for type in tai_lieus.keys():
            if request.form.get(f'tailieu_{type}') == f'activated_{type}':
                session['type'] = type
                return redirect((url_for('reading')))
               
    return render_template('account.html', user_email=user_email, tai_lieus=tai_lieus)

# Route đăng xuất
@app.route('/logout')
def logout():
    session.pop('user', None)
    flash('Bạn đã đăng xuất.')
    return redirect(url_for('login'))

# Tài liệu
@app.route('/reading', methods=["GET", 'POST'])
def reading():
    start_time = time.time()
    result.append(start_time)
    selected_type = session.get('type')
    tai_lieu = tai_lieus[selected_type]
    if request.form.get('button_action') == 'activated':
        end_time = time.time()
        etime = end_time - result[0]
        all_result.append(etime)
        result.clear()
        return redirect(url_for('quiz'))
    
    pdf_filename = tai_lieu["Doc"] 

    return render_template("reading.html", tai_lieu = tai_lieu, pdf_filename=pdf_filename, type=selected_type)

etime = 0

# Câu hỏi
def load_questions_from_excel(file_path):
    df = pd.read_excel(file_path)
    questions = {}

    for _, row in df.iterrows():
        question = {
            "type": row["Type"],
            "nques": row["Nques"],
            "question": row["Question"],
            "options": [row["Option 1"], row["Option 2"], row["Option 3"], row["Option 4"]],
            "correct_answer": row["Correct Answer"],
            "difficulty": row["Difficulty"]
        }
        questions[row["Index"]] = question
    
    return questions

questions = load_questions_from_excel("quiz.xlsx")
answer = []

@app.route('/quiz', methods=["GET", "POST"])
def quiz():
    start_time = time.time()
    result.append(start_time)
    stype = session.get('type')
    if request.form.get('button_action') == 'activated':
        end_time = time.time()
        etime = end_time - result[0]
        all_result.append(etime)
        result.clear()
        for question_id, question in questions.items():
            if question['type'] == stype:
                answer.append(request.form.get(f"question_{question_id+1}"))
        return redirect(url_for('final'))
    return render_template("quiz.html", questions=questions, type=stype, result = result)


def save_per_to_excel(list, difficulty, num):

    df = pd.read_excel('ScoreDatabase.xlsx')
    studytime = list[0]/60
    examtime = list[1]/60
    max_user_id = df['id'].max()
    user_id = max_user_id + 1
    user_input = [user_id, difficulty, num, studytime, examtime]
    user_performance = pd.DataFrame([user_input], columns=['id', 'difficulty', 'score', 'studytime', 'examtime'])
    df = pd.concat([df, user_performance], ignore_index=True)
    df.to_excel('ScoreDatabase.xlsx', index=False)    


weak = []
def personalize(id):
    df = pd.read_excel('ScoreDatabase.xlsx')
    for i in range (0, len(df.iloc[:, 0])):
        if (df.loc[i][0] == id):
            x = df.loc[i][1:]
            y_pred = model(torch.from_numpy(transform(x.to_numpy().reshape(1, -1).astype(np.float32))))
            weak.append(round(y_pred.item()))

def load_chat_from_excel(file):
    df = pd.read_excel(file)
    chats = {}
    for _,row in df.iterrows():
        chat = {
            "type": row['Type'],
            "studytype": row['Studytype'],
            "chat": row['Chat']
        }
        chats[row['Index']] = chat
    return chats

chat = load_chat_from_excel('chatbot.xlsx')

def load_user_id():
    df = pd.read_excel('ScoreDatabase.xlsx')
    max_user_id = df['id'].max()
    return max_user_id

@app.route('/final', methods=["POST", "GET"])
def final():
    score = 0
    total_questions = 0
    count = 0
    for question_id, question in questions.items():
        if count >= len(answer):
            break
        user_answer = answer[count]
        difficulty = question["difficulty"]
        if question['type'] == session.get('type'):
            correct_answer = question['correct_answer']
            total_questions += 1
            user_answer = str(user_answer).strip().lower() if user_answer else ""
            correct_answer = str(correct_answer).strip().lower()
            count += 1
            if user_answer == correct_answer:
                score += 1        
    answer.clear()
    save_per_to_excel(all_result, difficulty, score)
    all_result.clear()
    
    user_id = load_user_id()
    personalize(user_id)
    rate = weak[-1]
    studytype = session.get('studytype')
    if rate == 0:
        for chat_id, chats in chat.items():
            if chats['type'] == session.get('type') and studytype == chats['studytype']:
                chat_response = rating(chats['chat'])
                break
    elif rate == 1:
        chat_response = "Bạn đã làm rất tốt và vượt qua bài kiểm tra"

    return render_template('results.html', score=score, chat_response=chat_response, rate=rate, total_questions=total_questions)

if __name__ == "__main__":
    app.run(debug=True)
