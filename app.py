from flask import Flask, request, jsonify
import psycopg2
import os

app = Flask(__name__)

# ✅ Use environment variables (IMPORTANT for Render)
conn = psycopg2.connect(
    host="aws-1-ap-southeast-1.pooler.supabase.com",
    database="postgres",
    user="postgres.iedizehssmyerdbwxcly",
    password="b0v2fTpnzvOJwz7W",
    port="6543"
)

# ✅ Health check (VERY IMPORTANT)
@app.route('/')
def home():
    return "PORS Backend Running ✅"

# 🔐 LOGIN
@app.route('/login', methods=['POST'])
def login():
    data = request.json

    cur = conn.cursor()
    cur.execute(
        "SELECT role FROM users WHERE username=%s AND password=%s",
        (data['username'], data['password'])
    )

    result = cur.fetchone()

    if result:
        return jsonify({
            "status": "success",
            "role": result[0]
        })
    else:
        return jsonify({"status": "fail"})

# ➕ ADD USER
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

# ✅ IMPORTANT FOR RENDER
if __name__ == "__main__":
    app.run()