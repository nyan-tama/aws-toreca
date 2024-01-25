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

def get_parameter(name):
    ssm = boto3.client('ssm')
    parameter = ssm.get_parameter(Name=name, WithDecryption=True)
    return parameter['Parameter']['Value']

def get_rds_endpoint(instance_identifier):
    client = boto3.client('rds', region_name='ap-northeast-1')
    try:
        response = client.describe_db_instances(DBInstanceIdentifier=instance_identifier)
        db_instances = response['DBInstances']
        if len(db_instances) > 0:
            return db_instances[0]['Endpoint']['Address']
    except Exception as e:
        print(f"Error in getting RDS endpoint: {e}")
        return None

# ここでインスタンス識別子を使用してエンドポイントを取得
prod_db_host = get_rds_endpoint('Web3souDbInstance')


# 環境に応じた設定の読み込み
if os.environ.get('ENVIRONMENT') == 'production':
    auth_user = get_parameter('/prod/auth_user')
    auth_pass = get_parameter('/prod/auth_pass')

    db_name = get_parameter('/prod/db_name')
    db_user = get_parameter('/prod/db_user')
    db_password = get_parameter('/prod/db_password')
    db_host = prod_db_host
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
