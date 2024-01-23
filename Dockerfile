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

# Make command line prettier...
RUN echo "alias ls='ls --color=auto'" >> /root/.bashrc
RUN echo "PS1='${debian_chroot:+($debian_chroot)}\[\033[01;32m\]\u@aws-handson\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]\$ '" >> /root/.bashrc

# アプリケーションを実行
CMD ["flask", "run", "--host=0.0.0.0"]
