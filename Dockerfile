# Python 3.9のベースイメージを使用
FROM python:3.9

# 作業ディレクトリを設定
WORKDIR /app

# 依存関係をコピー

COPY requirements.txt .

# 依存関係をインストール
RUN pip install --no-cache-dir -r requirements.txt

# PostgreSQLクライアント（psql）をインストール
RUN apt-get update && \
    apt-get install -y postgresql-client && \
    rm -rf /var/lib/apt/lists/*
    
# 環境変数を設定
ENV FLASK_APP=app.py
# デフォルトを本番環境に設定
ENV ENVIRONMENT=production
# AWSのデフォルトリージョンを設定
ENV AWS_DEFAULT_REGION=ap-northeast-1  

# Make command line prettier...
RUN echo "alias ls='ls --color=auto'" >> /root/.bashrc
RUN echo "PS1='${debian_chroot:+($debian_chroot)}\[\033[01;32m\]\u@flask-container\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]\$ '" >> /root/.bashrc

# ENVIRONMENT環境変数のデフォルト値を本番環境に設定
ENV ENVIRONMENT=production

# 開発環境と本番環境の起動コマンドを分岐
CMD /bin/sh -c 'if [ "$ENVIRONMENT" = "production" ]; then \
                    gunicorn -b :5000 --access-logfile - --log-level info app:app; \
                else \
                    flask run --host=0.0.0.0; \
                fi'
