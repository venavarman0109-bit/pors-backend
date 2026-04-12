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

@app.route('/check_report_limit', methods=['POST'])
def check_report_limit():
    data = request.json
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT COUNT(*) FROM outturn_reports
        WHERE report_date=%s
    """, (data['date'],))

    count = cur.fetchone()[0]

    cur.close()
    conn.close()

    return jsonify({"count": count})

@app.route('/add_outturn_report', methods=['POST'])
def add_outturn_report():
    data = request.json
    conn = get_connection()
    cur = conn.cursor()

    # Insert main report
    cur.execute("""
        INSERT INTO outturn_reports
        (vessel_name, port, berth, report_date, report_time, agent, created_by, delays, remarks)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        RETURNING id
    """, (
        data['vessel_name'],
        data['port'],
        data['berth'],
        data['date'],
        data['time'],
        data['agent'],
        data['created_by'],
        data['delays'],
        data['remarks']
    ))

    report_id = cur.fetchone()[0]

    # Insert items
    for item in data['items']:
        cur.execute("""
            INSERT INTO outturn_report_items
            (report_id, hatch, gangs, product, lorry_trips, tons)
            VALUES (%s,%s,%s,%s,%s,%s)
        """, (
            report_id,
            item['hatch'],
            item['gangs'],
            item['product'],
            item['lorry_trips'],
            item['tons']
        ))

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"status": "added"})

@app.route('/get_products', methods=['GET'])
def get_products():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id, name FROM products ORDER BY name")
    rows = cur.fetchall()

    result = [{"id": r[0], "name": r[1]} for r in rows]

    cur.close()
    conn.close()

    return jsonify(result)

@app.route('/add_product', methods=['POST'])
def add_product():
    data = request.json

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("INSERT INTO products (name) VALUES (%s)", (data['name'],))
        conn.commit()
    except:
        return jsonify({"status": "error", "message": "Product exists"})

    cur.close()
    conn.close()

    return jsonify({"status": "success"})

@app.route('/delete_product', methods=['POST'])
def delete_product():
    data = request.json

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM products WHERE id=%s", (data['id'],))
    conn.commit()

    cur.close()
    conn.close()

    return jsonify({"status": "deleted"})

@app.route('/get_ports', methods=['GET'])
def get_ports():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id, name FROM ports ORDER BY name")
    rows = cur.fetchall()

    result = [{"id": r[0], "name": r[1]} for r in rows]

    cur.close()
    conn.close()

    return jsonify(result)

@app.route('/add_port', methods=['POST'])
def add_port():
    data = request.json

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("INSERT INTO ports (name) VALUES (%s)", (data['name'],))
        conn.commit()
    except:
        return jsonify({"status": "error", "message": "Port exists"})

    cur.close()
    conn.close()

    return jsonify({"status": "success"})

@app.route('/delete_port', methods=['POST'])
def delete_port():
    data = request.json

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM ports WHERE id=%s", (data['id'],))
    conn.commit()

    cur.close()
    conn.close()

    return jsonify({"status": "deleted"})

@app.route('/get_berths', methods=['GET'])
def get_berths():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT b.id, b.name, p.name
        FROM berths b
        JOIN ports p ON b.port_id = p.id
        ORDER BY p.name
    """)

    rows = cur.fetchall()

    result = [
        {"id": r[0], "name": r[1], "port": r[2]}
        for r in rows
    ]

    cur.close()
    conn.close()

    return jsonify(result)

@app.route('/add_berth', methods=['POST'])
def add_berth():
    data = request.json

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO berths (port_id, name) VALUES (%s, %s)",
        (data['port_id'], data['name'])
    )

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"status": "success"})

@app.route('/delete_berth', methods=['POST'])
def delete_berth():
    data = request.json

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM berths WHERE id=%s", (data['id'],))
    conn.commit()

    cur.close()
    conn.close()

    return jsonify({"status": "deleted"})

@app.route('/get_hatches', methods=['GET'])
def get_hatches():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id, name FROM hatches ORDER BY name")
    rows = cur.fetchall()

    result = [{"id": r[0], "name": r[1]} for r in rows]

    cur.close()
    conn.close()

    return jsonify(result)

@app.route('/add_hatch', methods=['POST'])
def add_hatch():
    data = request.json

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("INSERT INTO hatches (name) VALUES (%s)", (data['name'],))
        conn.commit()
    except:
        return jsonify({"status": "error", "message": "Hatch exists"})

    cur.close()
    conn.close()

    return jsonify({"status": "success"})

@app.route('/delete_hatch', methods=['POST'])
def delete_hatch():
    data = request.json

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM hatches WHERE id=%s", (data['id'],))
    conn.commit()

    cur.close()
    conn.close()

    return jsonify({"status": "deleted"})

# =========================
# 🔄 UPDATE APIs (FIXED)
# =========================

@app.route('/update_product', methods=['POST'])
def update_product():
    data = request.json

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "UPDATE products SET name=%s WHERE id=%s",
        (data['name'], data['id'])
    )

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"status": "updated"})


@app.route('/update_port', methods=['POST'])
def update_port():
    data = request.json

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "UPDATE ports SET name=%s WHERE id=%s",
        (data['name'], data['id'])
    )

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"status": "updated"})


@app.route('/update_hatch', methods=['POST'])
def update_hatch():
    data = request.json

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "UPDATE hatches SET name=%s WHERE id=%s",
        (data['name'], data['id'])
    )

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"status": "updated"})


@app.route('/update_berth', methods=['POST'])
def update_berth():
    data = request.json

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "UPDATE berths SET name=%s, port_id=%s WHERE id=%s",
        (data['name'], data['port_id'], data['id'])
    )

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"status": "updated"})

@app.route('/submit_outturn', methods=['POST'])
def submit_outturn():
    data = request.json

    conn = get_connection()
    cur = conn.cursor()

    # 🔥 Insert report items
    for item in data['items']:
        cur.execute("""
            INSERT INTO shipment_report_items
            (report_id, product, tons, trips)
            VALUES (%s, %s, %s, %s)
        """, (
            data['report_db_id'],
            item['product'],
            item['tons'],
            item['trips']
        ))

        # 🔥 UPDATE LOADED
        cur.execute("""
            UPDATE shipment_products
            SET loaded = loaded + %s
            WHERE shipment_id=%s AND product=%s
        """, (
            item['tons'],
            data['shipment_id'],
            item['product']
        ))

    # 🔥 CHECK COMPLETION
    cur.execute("""
        SELECT COUNT(*) FROM shipment_products
        WHERE shipment_id=%s AND loaded < total_tonnage
    """, (data['shipment_id'],))

    remaining = cur.fetchone()[0]

    if remaining == 0:
        cur.execute("""
            UPDATE shipments SET status='COMPLETED'
            WHERE id=%s
        """, (data['shipment_id'],))

    else:
        cur.execute("""
            UPDATE shipments SET status='ONGOING'
            WHERE id=%s
        """, (data['shipment_id'],))

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"status": "saved"})

@app.route('/get_shipment_progress/<int:shipment_id>', methods=['GET'])
def get_shipment_progress(shipment_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT product, loaded
        FROM shipment_products
        WHERE shipment_id=%s
    """, (shipment_id,))

    data = cur.fetchall()

    result = {row[0]: row[1] for row in data}

    cur.close()
    conn.close()

    return jsonify(result)

@app.route('/get_active_shipments', methods=['GET'])
def get_active_shipments():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, shipment_code, agent, port, berth, status
        FROM shipments
        WHERE status != 'COMPLETED'
        ORDER BY id DESC
    """)

    data = cur.fetchall()

    result = []
    for row in data:
        result.append({
            "id": row[0],
            "shipment_code": row[1],
            "agent": row[2],
            "port": row[3],
            "berth": row[4],
            "status": row[5]
        })

    cur.close()
    conn.close()

    return jsonify(result)

@app.route('/create_shipment', methods=['POST'])
def create_shipment():
    data = request.json

    agent = data["agent"]
    port = data["port"]
    berth = data["berth"]
    products = data["products"]

    conn = get_connection()
    cur = conn.cursor()

    # 🔥 shipment code
    cur.execute("SELECT COUNT(*) FROM shipments")
    count = cur.fetchone()[0] + 1
    shipment_code = f"SHP{str(count).zfill(3)}"

    cur.execute("""
        INSERT INTO shipments (shipment_code, agent, port, berth, status)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
    """, (shipment_code, agent, port, berth, "START"))

    shipment_id = cur.fetchone()[0]

    for p in products:
        cur.execute("""
            INSERT INTO shipment_products 
            (shipment_id, product, total_tonnage, loaded)
            VALUES (%s, %s, %s, %s)
        """, (
            shipment_id,
            p["name"],
            p["tonnage"],
            0
        ))

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({
        "shipment_id": shipment_id,
        "shipment_code": shipment_code
    })

@app.route('/create_report', methods=['POST'])
def create_report():
    data = request.json

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT COUNT(*) FROM shipment_reports
        WHERE shipment_id=%s
    """, (data['shipment_id'],))

    count = cur.fetchone()[0] + 1

    report_id = f"{data['shipment_code']}-{str(count).zfill(2)}"

    cur.execute("""
        INSERT INTO shipment_reports
        (shipment_id, report_no, report_id, date, start_time, end_time)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (
        data['shipment_id'],
        count,
        report_id,
        data['date'],
        data['start_time'],
        data['end_time']
    ))

    report_db_id = cur.fetchone()[0]

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({
        "report_id": report_id,
        "report_db_id": report_db_id
    })


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