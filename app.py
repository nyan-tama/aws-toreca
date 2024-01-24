from flask import Flask, render_template, request, redirect, url_for
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
import psycopg2.extras
import os
import boto3
import json

app = Flask(__name__)
auth = HTTPBasicAuth()

# 環境に応じた設定の読み込み
if os.environ.get('ENVIRONMENT') == 'production':
    # 本番環境 - AWS Secrets Managerから設定を読み込む
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId='web-3sou')
    secrets = json.loads(response['SecretString'])

    auth_user = secrets['AUTH_USER']
    auth_pass = secrets['AUTH_PASS']
    db_name = secrets['DB_NAME']
    db_user = secrets['DB_USER']
    db_password = secrets['DB_PASSWORD']
    db_host = secrets.get('DB_HOST')
else:
    # ローカル環境 - ハードコードされた値を使用
    auth_user = 'localuser'
    auth_pass = 'localpass'
    db_name = 'localdb'
    db_user = 'localuser'
    db_password = 'localpassword'
    db_host = 'db'

users = {
    auth_user: generate_password_hash(auth_pass)
}

@auth.verify_password
def verify_password(username, password):
    if username in users and check_password_hash(users.get(username), password):
        return username

# データベース接続設定
def get_db_connection():
    conn = psycopg2.connect(
        dbname=db_name,
        user=db_user,
        password=db_password,
        host=db_host
    )
    return conn

# 以下、Flaskアプリのルートと関数定義...


@app.route('/')
@auth.login_required
def index():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute('SELECT * FROM greetings;')
    greetings = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('index.html', greetings=greetings)

@app.route('/greet', methods=['GET'])
def greet():
    name = request.args.get('name', 'World')
    return f'Hello, {name}!'

@app.route('/greet', methods=['POST'])
def add_greeting():
    name = request.form['name']
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("INSERT INTO greetings (name) VALUES (%s)", (name,))
            conn.commit()
    except psycopg2.DatabaseError as e:
        print(f"Database error: {e}")
        conn.rollback()
    finally:
        conn.close()
    return redirect(url_for('index'))

if __name__ == "__main__":
    app.run(debug=True)
