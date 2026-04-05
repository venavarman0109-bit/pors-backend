from flask import Flask, request, jsonify
import psycopg2

app = Flask(__name__)

# 🔥 IMPORTANT: connection created per request (no more locks)
def get_connection():
    return psycopg2.connect(
        host="aws-1-ap-southeast-1.pooler.supabase.com",
        database="postgres",
        user="postgres.iedizehssmyerdbwxcly",
        password="U4uesWPqV1GXXsdX",
        port="6543"
    )

# Health check
@app.route('/')
def home():
    return "PORS Backend Running ✅"

# 🔐 LOGIN
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT role FROM users_v2 WHERE username=%s AND password=%s",
        (data['username'], data['password'])
    )

    result = cur.fetchone()

    if result:
        # update login time
        cur.execute(
            "UPDATE users_v2 SET login_time = NOW() WHERE username=%s",
            (data['username'],)
        )
        conn.commit()

        cur.close()
        conn.close()

        return jsonify({
            "status": "success",
            "role": result[0]
        })

    cur.close()
    conn.close()
    return jsonify({"status": "fail"})


# ➕ ADD USER
@app.route('/add_user', methods=['POST'])
def add_user():
    data = request.json
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO users_v2 (staff_id, username, password, role, email, contact)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            data['staff_id'],
            data['username'],
            data['password'],
            data['role'],
            data['email'],
            data['contact']
        )
    )

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"status": "added"})


# 👥 GET USERS (with login/logout time)
@app.route('/get_users', methods=['GET'])
def get_users():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT username, role, login_time, logout_time
        FROM users_v2
        ORDER BY username
    """)

    users = cur.fetchall()

    result = []
    for u in users:
        result.append({
            "username": u[0],
            "role": u[1],
            "login_time": str(u[2]) if u[2] else "-",
            "logout_time": str(u[3]) if u[3] else "-"
        })

    cur.close()
    conn.close()

    return jsonify(result)

@app.route('/get_users_full', methods=['GET'])
def get_users_full():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT staff_id, username, role, email, contact
        FROM users_v2
        ORDER BY username
    """)

    users = cur.fetchall()

    result = []
    for u in users:
        result.append({
            "staff_id": u[0],
            "username": u[1],
            "role": u[2],
            "email": u[3],
            "contact": u[4]
        })

    cur.close()
    conn.close()

    return jsonify(result)

# 🔓 LOGOUT
@app.route('/logout', methods=['POST'])
def logout():
    data = request.json
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "UPDATE users_v2 SET logout_time = NOW() WHERE username=%s",
        (data['username'],)
    )

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"status": "logged_out"})


if __name__ == "__main__":
    app.run()