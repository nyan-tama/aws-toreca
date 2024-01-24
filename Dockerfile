# Python 3.9のベースイメージを使用
FROM python:3.9

# 作業ディレクトリを設定
WORKDIR /app

# 依存関係ファイルをコンテナにコピー
COPY requirements.txt /app/

# 依存関係をインストール
RUN pip install --no-cache-dir -r requirements.txt

# 環境変数を設定
ENV FLASK_APP=app.py
# デフォルトを本番環境に設定
ENV ENVIRONMENT=production

# Make command line prettier...
RUN echo "alias ls='ls --color=auto'" >> /root/.bashrc
RUN echo "PS1='${debian_chroot:+($debian_chroot)}\[\033[01;32m\]\u@aws-handson\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]\$ '" >> /root/.bashrc

# ENVIRONMENT環境変数のデフォルト値を本番環境に設定
ENV ENVIRONMENT=production

# 開発環境と本番環境の起動コマンドを分岐
CMD if [ "$ENVIRONMENT" = "production" ]; then \
    CMD gunicorn -b :5000 --access-logfile - --log-level info app:app; \
    else \
    flask run --host=0.0.0.0; \
    fi