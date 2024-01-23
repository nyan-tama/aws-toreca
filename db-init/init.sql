-- テーブルを作成
CREATE TABLE IF NOT EXISTS greetings (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL
);
