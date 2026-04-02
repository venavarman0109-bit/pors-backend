from flask import Flask, request, jsonify
import psycopg2

app = Flask(__name__)

conn = psycopg2.connect(
    host="aws-1-ap-southeast-1.pooler.supabase.com",
    database="postgres",
    user="postgres.iedizehssmyerdbwxcly",
    password="TX2AxtqBzSXl7xYP",
    port="6543"
)

@app.route('/')
def home():
    return "PORS Backend Running ✅"

@app.route('/login', methods=['POST'])
def login():
    data = request.json

    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM users WHERE username=%s AND password=%s",
        (data['username'], data['password'])
    )

    user = cur.fetchone()

    if user:
        return jsonify({"status": "success", "role": user[3]})
    else:
        return jsonify({"status": "fail"})

@app.route('/add_user', methods=['POST'])
def add_user():
    data = request.json

    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
        (data['username'], data['password'], data['role'])
    )

    conn.commit()

    return jsonify({"status": "added"})

if __name__ == '__main__':
    app.run(debug=True)