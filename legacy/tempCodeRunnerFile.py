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