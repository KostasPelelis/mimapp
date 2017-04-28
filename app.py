import json
from flask import Flask, request, render_template, make_response, redirect
import tokenlib
from functools import wraps
from imap import MailClient

app = Flask(__name__)
sessions = {}


class ComplexJSONEncoder(json.JSONEncoder):

    def default(self, obj):
        if hasattr(obj, 'JSONrepr'):
            return obj.JSONrepr()
        else:
            return json.JSONEncoder.default(self, obj)


def login_required(controller):

    @wraps(controller)
    def wrapper(*args, **kwargs):
        try:
            session_id = sessions[request.cookies['sessionId']]
            return controller(session_id, *args, **kwargs)
        except KeyError:
            return redirect('/')

    return wrapper


@app.route('/login', methods=['POST'])
def login():
    try:
        username = request.form['username']
        password = request.form['password']
        server = request.form['server']
    except KeyError:
        return "Incorrect Form"

    config = {
        'username': username,
        'password': password,
        'server': server,
        'port': 143,
        'mailboxes': ['INBOX', 'Security', 'Phabricator', ]
    }
    global sessions
    client = MailClient(config)
    session = client.create_session()
    session_id = "{0}@{1}".format(username, server)
    sessions[session_id] = session
    resp = make_response(redirect('/home'))
    resp.set_cookie('sessionId', session_id)
    return resp


@app.route('/home')
@login_required
def home(session):
    session.get_mails()
    print(session.folders)
    return render_template('home.html', folders=session.folders)


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')


if __name__ == "__main__":
    app.run(debug=True)
