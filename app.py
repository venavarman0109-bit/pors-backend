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
        password="U6j4GsQKY9P1VtBX",
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
        "Tele Clerk": "TC",
        "Agent": "AGT"
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

    if not data.get("username") or not data.get("password"):
        return jsonify({"status": "fail"})

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


# ➕ ADD USER
@app.route('/add_user', methods=['POST'])
def add_user():
    data = request.json

    # 🔥 Validation
    required_fields = ["username", "password", "role"]
    for field in required_fields:
        if not data.get(field):
            return jsonify({"status": "error", "message": f"{field} missing"})

    conn = get_connection()
    cur = conn.cursor()

    try:
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
                data.get('email', ''),
                data.get('contact', '')
            )
        )

        conn.commit()

        return jsonify({
            "status": "added",
            "staff_id": staff_id
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

    finally:
        cur.close()
        conn.close()


# 👥 VIEW USERS (ACTIVITY)
@app.route('/get_users', methods=['GET'])
def get_users():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT staff_id, username, role, login_time, logout_time
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
            "login_time": str(u[3]) if u[3] else "-",
            "logout_time": str(u[4]) if u[4] else "-"
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

    cur.execute("SELECT role FROM users_v2 WHERE staff_id=%s", (data['staff_id'],))
    result = cur.fetchone()

    if not result:
        return jsonify({"status": "error"})

    if result[0] == "System Admin":
        return jsonify({"status": "forbidden"})

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
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT role FROM users_v2 WHERE staff_id=%s", (data['staff_id'],))
    result = cur.fetchone()

    if not result:
        return jsonify({"status": "error"})

    if result[0] == "System Admin":
        return jsonify({"status": "forbidden"})

    new_password = ''.join(random.choices('0123456789', k=6))

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

    cur.execute("SELECT role FROM users_v2 WHERE staff_id=%s", (data['staff_id'],))
    result = cur.fetchone()

    if not result:
        return jsonify({"status": "error"})

    if result[0] == "System Admin":
        return jsonify({"status": "forbidden"})

    cur.execute("DELETE FROM users_v2 WHERE staff_id=%s", (data['staff_id'],))

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"status": "deleted"})


# 👤 MY ACCOUNT
@app.route('/get_my_account', methods=['POST'])
def get_my_account():
    data = request.json

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT email, contact
        FROM users_v2
        WHERE username=%s
    """, (data['username'],))

    user = cur.fetchone()

    cur.close()
    conn.close()

    if user:
        return jsonify({
            "email": user[0],
            "contact": user[1]
        })

    return jsonify({"error": "User not found"}), 404

@app.route('/change_password', methods=['POST'])
def change_password():
    data = request.json
    conn = get_connection()
    cur = conn.cursor()

    # Check current password
    cur.execute(
        "SELECT password FROM users_v2 WHERE username=%s",
        (data['username'],)
    )
    result = cur.fetchone()

    if not result:
        return jsonify({"status": "error"})

    if result[0] != data['old_password']:
        return jsonify({"status": "wrong_password"})

    # Update new password
    cur.execute(
        "UPDATE users_v2 SET password=%s WHERE username=%s",
        (data['new_password'], data['username'])
    )

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"status": "updated"})

@app.route('/update_my_account', methods=['POST'])
def update_my_account():
    data = request.json
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE users_v2
        SET email=%s, contact=%s
        WHERE username=%s
    """, (
        data['email'],
        data['contact'],
        data['username']
    ))

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"status": "updated"})

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