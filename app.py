from flask import Flask, request, jsonify
import psycopg2

app = Flask(__name__)

conn = psycopg2.connect(
    host="aws-1-ap-southeast-1.pooler.supabase.com",
    database="postgres",
    user="postgres.iedizehssmyerdbwxcly",
    password="U4uesWPqV1GXXsdX",
    port="6543"
)

# ✅ Health check
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
        """
        INSERT INTO users (staff_id, username, password, role, email, contact)
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

    return jsonify({"status": "added"})


# 👥 GET USERS (✅ CORRECT POSITION)
@app.route('/get_users', methods=['GET'])
def get_users():
    cur = conn.cursor()
    cur.execute("""
        SELECT staff_id, username, role, email, contact
        FROM users
        ORDER BY staff_id
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

    return jsonify(result)


# ✅ IMPORTANT FOR RENDER
if __name__ == "__main__":
    app.run()