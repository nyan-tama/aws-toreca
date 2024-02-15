from flask import Flask, render_template, request, redirect, url_for, make_response
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
import psycopg2.extras
import os
import boto3
import json
from concurrent.futures import ThreadPoolExecutor
import pdfkit
from pdf2image import convert_from_path
from io import BytesIO
from pdf2image import convert_from_path, convert_from_bytes

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
    auth_secret = get_secret('auth')
    auth_user = auth_secret['username']
    auth_pass = auth_secret['password']
    
    db_secret = get_secret('prod_db') #prod_db本番の正確なsecretsに合わす必要あり
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

# Bedrockにリクエストを送信する関数
def request_bedrock(prompt):
    bedrock_runtime = boto3.client(
        service_name='bedrock-runtime', 
        region_name='us-east-1'
    )
    
    modelId = 'anthropic.claude-v2'
    accept = 'application/json'
    contentType = 'application/json'

    body = json.dumps({
        "prompt": prompt,
        "max_tokens_to_sample": 200,
        "temperature": 0.9,
        "top_k": 150,
        "top_p": 0.7
    })

    response = bedrock_runtime.invoke_model(
        body=body, 
        modelId=modelId, 
        accept=accept, 
        contentType=contentType
    )

    response_body = json.loads(response.get('body').read())
    return response_body


def request_image_bedrock(prompt):
    client = boto3.client('bedrock-runtime',region_name='us-east-1')

    response = client.invoke_model(
        modelId='stability.stable-diffusion-xl-v1',
        body=json.dumps({
            'text_prompts': [
                {
                    "text": prompt
                }
            ],
            "cfg_scale": 5,
            "seed": 30,
            "steps": 120
        }),
        contentType='application/json'
    )

    response_body = json.loads(response.get("body").read())
    return response_body

def translate_text(text, source_language_code, target_language_code):
    translate_client = boto3.client('translate')
    response = translate_client.translate_text(
        Text=text,
        SourceLanguageCode=source_language_code,
        TargetLanguageCode=target_language_code
    )
    return response['TranslatedText']

def upload_file_to_s3(bucket_name, file_path, object_name):
    """
    指定されたS3バケットにファイルをアップロードする関数。
    """
    s3_client = boto3.client('s3')
    with open(file_path, 'rb') as file:
        s3_client.upload_fileobj(file, bucket_name, object_name)

def convert_pdf_to_images_and_upload(pdf_content, bucket_name):
    """
    PDFコンテンツ（BytesIO）を画像に変換し、S3にアップロードする関数。
    """
    # BytesIOオブジェクトからバイト列を取得
    pdf_bytes = pdf_content.getvalue()

    # バイト列からPDFを画像に変換
    images = convert_from_bytes(pdf_bytes)
    s3_client = boto3.client('s3')

    for i, image in enumerate(images):
        # BytesIOオブジェクトに画像を保存
        img_byte_arr = BytesIO()
        image.save(img_byte_arr, format='JPEG')
        img_byte_arr.seek(0)
        
        object_name = f"image_{i}.jpg"
        
        # S3にアップロード
        s3_client.upload_fileobj(img_byte_arr, bucket_name, object_name)
        print(f"Uploaded {object_name} to S3 bucket {bucket_name}.")

# Bedrockを利用します
@app.route('/bedrock')
def bedrock():
    role_setting = "西洋ファンタジー専門家です"
    user_request = "立派な顎を持ち岩も噛み砕く"

    prompt1 = (
        "Human: あたなたは{role}。ユーザーは{monster}というモンスターをリクエストしています。ファーストネーム・ミドルネームを持つ人間のようなモンスターの名前を生成し、<answer></answer>タグに出力してください。\n"
        "Assistant: "
    ).format(role=role_setting, monster=user_request)
    response1 = request_bedrock(prompt1)
    monster_name = response1['completion'].strip(" <answer></answer>")
    
    prompt2 = (
        "Human: あたなたは{role}。ユーザーは{monster}というモンスターをリクエストしています。レベルを10段階で数値にして生成してくれます。『1,2,3,4,5,6,7,8,9,10』の中から設定に合わせて選んでください。レベルは小さいほど弱く、大きほど強いです。論理的に考え、モンスターのレベルを<answer></answer>タグに数値で出力してください。</answer>以降の解説は入りません\n"
        "Assistant: "
    ).format(role=role_setting, monster=user_request)
    response2 = request_bedrock(prompt2)
    monster_level = response2['completion'].strip(" <answer></answer>")

    prompt3 = (
        "Human: あたなたは{role}。ユーザーは{monster}というモンスターをリクエストしています。属性を『火、水、風、土、光、闇』の中から設定に合わせて選んでください。選んだ属性を<answer></answer>タグに出力してください。</answer>以降の解説は入りません\n"
        "Assistant: "
    ).format(role=role_setting, monster=user_request)
    response3 = request_bedrock(prompt3)
    monster_element = response3['completion'].strip(" <answer></answer>")
    
    prompt4 = (
        "Human: あたなたは{role}。ユーザーは{monster}というモンスターをリクエストしています。{monster_name}というモンスターの名前、モンスターの属性である{monster_element}を資料にし、モンスターの特殊能力と特殊能力の説明を<answer>【特殊能力】：特殊能力の説明</answer>タグに100文字以内で出力してください。\n"
        "Assistant: "
    ).format(role=role_setting, monster=user_request, monster_name=monster_name, monster_element=monster_element)
    response4 = request_bedrock(prompt4)
    monster_ability = response4['completion'].strip(" <answer></answer>")
    
    prompt5 = (
        "Human: あたなたは{role}。ユーザーは{monster}というモンスターをリクエストしています。{monster_name}というモンスターの名前、モンスターの属性である{monster_element}、モンスターの特殊能力である{monster_ability}を資料にし、モンスターのバックグラウンドがわかる悲しく恐ろしい伝説の言い伝えのエピソードを<answer></answer>タグに100文字以内でお願いします。\n"
        "Assistant: "
    ).format(role=role_setting, monster=user_request, monster_name=monster_name, monster_element=monster_element, monster_ability=monster_ability)
    response5 = request_bedrock(prompt5)
    monster_episode = response5['completion'].strip(" <answer></answer>")

    # 画像生成
    prompt6 = "あたなたは{role}。油絵風のリアルなモンスターの絵を描いて下さい。色はたくさん使って下さい。絵の背景にはモンスターのエピソードである{monster_episode}を反映させます。ユーザーは{monster}というモンスターをリクエストしています。モンスターは名前は{monster_name}、モンスターの属性である{monster_element}で、モンスターのポーズはモンスターの特殊能力である{monster_ability}を参考に描いて下さい。".format(
        role=role_setting,
        monster=user_request,
        monster_name=monster_name,
        monster_element=monster_element,
        monster_ability=monster_ability,
        monster_episode=monster_episode
    )
    # 日本語のプロンプトを英語に翻訳
    en_prompt6 = translate_text(prompt6, 'ja', 'en')
    # 英訳したプロンプトでイメージをリクエスト
    with ThreadPoolExecutor() as executor:
        generate_image_future = executor.submit(request_image_bedrock, en_prompt6)
        generate_image = generate_image_future.result()

    # Base64エンコーディングされたイメージデータを取得
    image_data = generate_image['artifacts'][0]['base64']  # 必要に応じて構造を確認してください

    # HTMLをレンダリング
    rendered = render_template('show_monster.html', 
        response1 = monster_name,
        response2 = monster_level,
        response3 = monster_element,
        response4 = monster_ability,
        response5 = monster_episode,
        response6 = image_data
    )
    # PDFに変換
    pdf = pdfkit.from_string(rendered, False)

    # PDFコンテンツをBytesIOオブジェクトに変換
    pdf_content = BytesIO(pdf)

    # PDFを画像に変換し、S3にアップロード
    bucket_name = 'elasticbeanstalk-ap-northeast-1-891377145933'
    convert_pdf_to_images_and_upload(pdf_content, bucket_name)

    return 'PDF converted to images and uploaded to S3 successfully!'


# 以下、Flaskアプリの動作確認用
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
