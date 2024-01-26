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

# AWS Secrets Managerからシークレットを取得
def get_secret(secret_name, region_name='ap-northeast-1'):
    client = boto3.client('secretsmanager', region_name=region_name)
    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
    except Exception as e:
        print(f"Error in getting secret: {e}")
        return None

    if 'SecretString' in get_secret_value_response:
        secret = get_secret_value_response['SecretString']
        return json.loads(secret)
    else:
        return None


# 環境に応じた設定の読み込み
if os.environ.get('ENVIRONMENT') == 'production':
    # 認証情報の取得
    auth_secret = get_secret('prod/auth')
    auth_user = auth_secret['username']
    auth_pass = auth_secret['password']
    
    db_secret = get_secret('DBCredentials')
    db_name = db_secret['dbname']
    db_user = db_secret['username']
    db_password = db_secret['password']
    db_host= db_secret['host']
    

else:
    # ローカル環境 - ハードコードされた値を使用
    auth_user = 'localuser'
    auth_pass = 'localpass'
    
    db_name = 'localdb'
    db_user = 'localuser'
    db_password = 'localpassword'
    db_host = 'localhost'

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
