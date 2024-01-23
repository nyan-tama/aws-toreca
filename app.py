from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

load_dotenv() 

auth = HTTPBasicAuth()

auth_user = os.environ.get('AUTH_USER')
auth_pass = os.environ.get('AUTH_PASS')

users = {
    auth_user: generate_password_hash(auth_pass)
}


@auth.verify_password
def verify_password(username, password):
    if username in users and \
            check_password_hash(users.get(username), password):
        return username

app = Flask(__name__)

# データベース接続設定
def get_db_connection():
    conn = psycopg2.connect(
        dbname="exampledb",
        user="exampleuser",
        password="examplepass",
        host="db"
    )
    return conn

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
