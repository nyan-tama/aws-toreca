
# アプリケーション名
よくある3層構造のWEBアプリケーションです。
このアプリケーションはFlaskを使用し、PostgreSQLデータベースに挨拶を保存するシンプルなWebアプリケーションです。

## 特徴

- FlaskベースのWebアプリケーション
- PostgreSQLデータベースを使用
- Dockerで容易にセットアップ可能

## 始め方

### 前提条件

- Dockerがインストールされていること
- Docker Composeが利用可能であること

### インストール手順

1. プロジェクトをクローンする：

git clone https://github.com/nyan-tama/aws-flask.git

2. Docker Composeを使用してアプリケーションとデータベースを起動する：

cd aws-flask
docker-compose up

※Docker内に入って作業する場合
docker-compose up -d
docker-compose exec web bash

※Dockerfileを修正した場合は更新後に起動
docker-compose build --no-cache
docker-compose up

3. アプリケーションが起動したら、ブラウザで `http://localhost:5000` にアクセスする。
開発環境におけるベーシック認証情報
id: localuser
pass: localpass

### 使用方法

#### 新しい挨拶の追加

1. ブラウザで `http://localhost:5000` にアクセスする。
2. 表示されたフォームに挨拶の名前を入力し、`Submit` ボタンをクリックする。
3. 入力した挨拶が下のリストに表示される。

#### 挨拶リストの表示

- トップページにアクセスすると、データベースに保存されているすべての挨拶が表示されます。

## 技術スタック

- フロントエンド：HTML, CSS
- バックエンド：Flask (Python)
- データベース：PostgreSQL
- コンテナ化：Docker, Docker Compose



## 本番環境の場合
- app.pyの下記箇所を修正
db_secret = get_secret('prod_db') #prod_dbはAWSのシークレットマネージャの名前に変更する必要あり

docker build -t aws-flask .
起動＆docker内に入る
docker run -it --rm --name flask-container -p 80:5000 -v "$(pwd)":/app aws-flask /bin/bash



### DB初期テーブル作成
```
psql \
-h rdsエンドポイント \
-U postgres \
-d flask_db

パスワードを聞かれるので、AWSのシークレットマネージャにある値を入力
```

```
CREATE TABLE IF NOT EXISTS greetings (
id SERIAL PRIMARY KEY,
name VARCHAR(255) NOT NULL
);
```

```
\dt
\q
```

dockerからexitコマンドで終了
下記コマンドで再度起動
docker run --rm --name flask-container -p 80:5000 -v "$(pwd)":/app aws-flask

以上でhttp接続までは完了
AWSのALB（ロードバランサ）のDNSアドレスから動作確認可能

### SSLおよび独自ドメイン対応
-
-
-