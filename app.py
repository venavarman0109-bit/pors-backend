from flask import Flask, request, jsonify
import psycopg2
import random

app = Flask(__name__)

# 🔥 DB CONNECTION
def get_connection():
    return psycopg2.connect(
        host="aws-1-ap-southeast-1.pooler.supabase.com",
        database="postgres",
        user="postgres.iedizehssmyerdbwxcly",
        password="U4uesWPqV1GXXsdX",
        port="6543"
    )

# 🔥 GENERATE STAFF ID
def generate_staff_id(role):
    prefix_map = {
        "System Admin": "SYS",
        "Admin Staff": "ADM",
        "Director": "DIR",
        "Manager": "MGR",
        "Supervisor": "SUP",
        "Tele Clerk": "TC"
    }

    prefix = prefix_map.get(role, "USR")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT staff_id FROM users_v2
        WHERE staff_id LIKE %s
        ORDER BY staff_id DESC LIMIT 1
    """, (prefix + "%",))

    last = cur.fetchone()

    if last:
        number = int(last[0].replace(prefix, "")) + 1
    else:
        number = 1

    cur.close()
    conn.close()

    return f"{prefix}{str(number).zfill(3)}"


# 🟢 HEALTH
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


# ➕ ADD USER (🔥 FIXED)
@app.route('/add_user', methods=['POST'])
def add_user():
    data = request.json
    conn = get_connection()
    cur = conn.cursor()

    staff_id = generate_staff_id(data['role'])

    cur.execute(
        """
        INSERT INTO users_v2 (staff_id, username, password, role, email, contact)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            staff_id,
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

    return jsonify({"status": "added", "staff_id": staff_id})


# 👥 VIEW USERS (ACTIVITY)
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


# 👥 FULL USERS (MANAGE PAGE)
@app.route('/get_users_full', methods=['GET'])
def get_users_full():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT staff_id, username, role, email, contact, updated_by
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
            "contact": u[4],
            "updated_by": u[5] if u[5] else "-"
        })

    cur.close()
    conn.close()

    return jsonify(result)

# ✏️ UPDATE USER
@app.route('/update_user', methods=['POST'])
def update_user():
    data = request.json
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE users_v2
        SET username=%s, role=%s, email=%s, contact=%s, updated_by=%s
        WHERE staff_id=%s
    """, (
        data['username'],
        data['role'],
        data['email'],
        data['contact'],
        data['updated_by'],
        data['staff_id']
    ))

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"status": "updated"})


# 🔑 RESET PASSWORD
@app.route('/reset_password', methods=['POST'])
def reset_password():
    data = request.json

    new_password = ''.join(random.choices('0123456789', k=6))

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE users_v2 SET password=%s WHERE staff_id=%s
    """, (new_password, data['staff_id']))

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({
        "status": "reset",
        "new_password": new_password
    })


# ❌ DELETE USER
@app.route('/delete_user', methods=['POST'])
def delete_user():
    data = request.json

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM users_v2 WHERE staff_id=%s", (data['staff_id'],))

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"status": "deleted"})


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