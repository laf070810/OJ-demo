from forms import LoginForm, SubmitForm
from model import User
from judge import check
from flask import Flask, request, render_template, redirect, url_for
from flask_wtf.csrf import CsrfProtect
from flask_login import login_user, login_required
from flask_login import LoginManager, current_user
from flask_login import logout_user
import os
import json
import time
import threading

app = Flask(__name__)
app.secret_key = os.urandom(24)
PROBLEM_FILE = './data/problems.json'
ATTEMPTS_FILE = './data/attempts.json'
USER_CODE_DIR = './user_code/'
with open(PROBLEM_FILE, encoding='utf-8') as f:
    problems = json.load(f)
with open(ATTEMPTS_FILE, encoding='utf-8') as f:
    attempts = json.load(f)
next_run_id = max([int(i) for i in attempts.keys()]) + 1
LANGUAGE_IDX2NAME = {'0': ('G++', '.cpp'), '1': ('GCC', ".c")}
LANGUAGE_NAME2IDX = {'G++': '0', '.cpp': '0', 'GCC': '1', '.c': '1'}

# use login manager to manage session
login_manager = LoginManager()
login_manager.session_protection = 'strong'
login_manager.login_view = 'login'
login_manager.init_app(app=app)

# csrf protection
csrf = CsrfProtect()
csrf.init_app(app)


# 这个callback函数用于reload User object，根据session中存储的user id
@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(
            request.args.get('next') or url_for('problem_list'))

    form = LoginForm()
    if form.validate_on_submit():
        user_name = request.form.get('username', None)
        password = request.form.get('password', None)
        remember_me = request.form.get('remember_me', False)
        user = User(user_name)
        if user.verify_password(password):
            login_user(user, remember=remember_me)
            return redirect(
                request.args.get('next') or url_for('problem_list'))
        else:
            return render_template(
                'login.html', form=form, message='Bad username or password')
    return render_template('login.html', form=form)


@app.route('/')
@app.route('/problem_list')
@login_required
def problem_list():
    update_problems()
    return render_template(
        'problem_list.html',
        username=current_user.username,
        problems=problems.values())


@app.route('/problem')
@login_required
def problem():
    return render_template(
        'problem.html',
        username=current_user.username,
        problem=problems.get(request.args.get('id')))


@app.route('/submit', methods=['GET', 'POST'])
@login_required
def submit():
    global next_run_id

    form = SubmitForm()
    if form.validate_on_submit():
        problem_id = int(request.form.get('problem_id', ''))
        code = request.form.get('source', '')
        language = request.form.get('language', '')
        if not os.path.exists(USER_CODE_DIR + current_user.username + '/'):
            os.mkdir(USER_CODE_DIR + current_user.username)
        with open(USER_CODE_DIR + current_user.username + '/' + str(next_run_id) + LANGUAGE_IDX2NAME[language][1], 'w', encoding='utf-8') as f:
            f.writelines(code.split('\n'))

        attempts[str(next_run_id)] = {
            'run_id': next_run_id,
            "user_id": current_user.username,
            "problem_id": problem_id,
            "result": "Judging",
            "memory": "***",
            "time": "***",
            "language": LANGUAGE_IDX2NAME[language][0],
            "code_length": str(len(code)) + 'B',
            "submit_time": time.strftime('%Y-%m-%d %H:%M:%S')
        }
        with open(ATTEMPTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(attempts, f, indent=4)
        threading.Thread(target=judge, args=[next_run_id]).start()

        next_run_id += 1
        return redirect(url_for('usr_status', id=current_user.username))

    return render_template(
        'submit.html',
        form=form,
        username=current_user.username,
        problem_id=request.args.get('id'))


@app.route('/problem_status')
@login_required
def prob_status():
    update_problems()
    problem_status = get_problem_status(int(request.args.get('id')))
    return render_template(
        'problem_status.html',
        username=current_user.username,
        attempts=problem_status.values())


@app.route('/user_status')
@login_required
def usr_status():
    user_status = get_user_status(request.args.get('id'))
    return render_template(
        'user_status.html',
        username=current_user.username,
        attempts=user_status.values())


@app.route('/show_source')
@login_required
def show_source():
    run_id = request.args.get('run_id')
    user_id = attempts[run_id]['user_id']
    language = attempts[run_id]['language']
    if attempts[run_id]['user_id'] != current_user.username:
        return 'Permission Denied'

    with open(USER_CODE_DIR + current_user.username + '/' + run_id + LANGUAGE_IDX2NAME[LANGUAGE_NAME2IDX[language]][1], encoding='utf-8') as f:
        # 注意replace的顺序
        return f.read().replace('&', '&amp;').replace(' ', '&nbsp;').replace(
            '<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace(
                "'", '&qpos;').replace('\n', '<br/>')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


def get_problem_status(problem_id: int) -> dict:
    problem_status = {}
    for attempt in attempts.values():
        if attempt['problem_id'] == problem_id:
            problem_status[str(attempt['run_id'])] = attempt
    return problem_status


def get_user_status(user_id: str) -> dict:
    user_status = {}
    for attempt in attempts.values():
        if attempt['user_id'] == user_id:
            user_status[str(attempt['run_id'])] = attempt
    return user_status


def update_problems():
    ac_num = {}
    submit_num = {}

    for attempt in attempts.values():
        problem_id = attempt['problem_id']
        submit_num[problem_id] = submit_num.get(problem_id, 0) + 1
        if attempt['result'] == 'Accepted':
            ac_num[problem_id] = ac_num.get(problem_id, 0) + 1

    for problem_id in problems.keys():
        problems[problem_id]['submit_num'] = submit_num.get(int(problem_id), 0)
        problems[problem_id]['ac_num'] = ac_num.get(int(problem_id), 0)
        if submit_num.get(int(problem_id), 0) != 0:
            problems[problem_id]['ratio'] = (
                ac_num.get(int(problem_id), 0) * 100) // submit_num.get(
                    int(problem_id), 0)
        else:
            problems[problem_id]['ratio'] = 0

    with open(PROBLEM_FILE, 'w', encoding='utf-8') as f:
        json.dump(problems, f, indent=4)


def judge(run_id: int):
    language = attempts[str(run_id)]['language']
    user_id = attempts[str(run_id)]['user_id']
    problem_id = attempts[str(run_id)]['problem_id']
    time_limit = int(''.join(list(filter(str.isdigit, problems[str(problem_id)]['time_limit']))))
    memory_limit = int(''.join(list(filter(str.isdigit, problems[str(problem_id)]['memory_limit']))))

    status, time, memory = check(USER_CODE_DIR + user_id + '/' + str(run_id) + LANGUAGE_IDX2NAME[LANGUAGE_NAME2IDX[language]][1], problem_id, time_limit, memory_limit)

    if status[0] == 'Compilation Error':
        attempts[str(run_id)]['result'] = 'Compilation Error'
        attempts[str(run_id)]['time'] = time[0]
        attempts[str(run_id)]['memory'] = memory[0]

    for i in range(len(status)):
        if status[i] != 'Accepted':
            attempts[str(run_id)]['result'] = status[i]
            attempts[str(run_id)]['time'] = time[i]
            attempts[str(run_id)]['memory'] = memory[i]

            with open(ATTEMPTS_FILE, 'w', encoding='utf-8') as f:
                json.dump(attempts, f, indent=4)
            return

    attempts[str(run_id)]['result'] = 'Accepted'
    attempts[str(run_id)]['memory'] = time[0]
    attempts[str(run_id)]['time'] = memory[0]
    with open(ATTEMPTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(attempts, f, indent=4)


if __name__ == '__main__':
    app.run()
