from flask import Flask, request, jsonify
import random
import os
import psycopg2
from datetime import datetime

app = Flask(__name__)

# 🔥 DB CONNECTION
def get_connection():
    return psycopg2.connect(os.environ.get("DATABASE_URL"))
# 🔥 GENERATE STAFF ID
def generate_staff_id(role):
    prefix_map = {
        "System Admin": "SYS",
        "Admin Staff": "ADM",
        "Director": "DIR",
        "Manager": "MGR",
        "Supervisor": "SUP",
        "Tally Clerk": "TC",
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
    conn = None
    cur = None

    try:
        data = request.json

        username = data['username'].strip()
        password = data['password'].strip()

        print("LOGIN:", username, password)

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT role FROM users_v2 
            WHERE LOWER(username)=LOWER(%s) AND password=%s
        """, (username, password))

        result = cur.fetchone()
        print("RESULT:", result)

        if result:
            return jsonify({
                "status": "success",
                "role": result[0]
            })

        return jsonify({"status": "fail"})

    except Exception as e:
        print("LOGIN ERROR:", str(e))
        return jsonify({"status": "error", "message": str(e)})

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


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
    import json

    start_time = data.get("start_time")
    end_time = data.get("end_time")

    if not start_time or not end_time:
        return jsonify({
            "status": "error",
            "message": "Start time and End time are required"
        })

    conn = get_connection()
    cur = conn.cursor()

    try:
        shipment_id = data.get("shipment_id")
        operations = data.get("operations", [])
        delays = data.get("delays", [])
        remarks = data.get("remarks", [])
        vessel_name = data.get("vessel_name", "")

        if not operations:
            return jsonify({"status": "error", "message": "No operations provided"})

        # 🔥 CREATE REPORT ENTRY
        current_date = datetime.now().strftime("%Y-%m-%d")
        created_by = data.get("created_by")
        report_no = data.get("report_no")
        report_code = data.get("report_id")

        cur.execute("""
            INSERT INTO shipment_reports
            (
                shipment_id,
                report_no,
                report_id,
                date,
                start_time,
                end_time,
                delays,
                remarks,
                vessel_name,
                created_by
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            shipment_id,
            report_no,
            report_code,
            current_date,
            start_time,
            end_time,
            json.dumps(delays),
            json.dumps(remarks),
            vessel_name,
            created_by
        ))

        report_id = cur.fetchone()[0]

        # 🔥 PROCESS OPERATIONS
        for op in operations:
            product = op['product']
            hatch = op['hatch']
            tons = float(op['tons'])
            pcs = float(op.get('pcs', 0))
            trips = int(op.get('trips', 0))
            gangs = str(op.get('gangs', ''))
            mode = op.get('mode', 'LORRY')

            if tons <= 0:
                return jsonify({"status": "error", "message": "Invalid tons"})

            # 🔍 CHECK PRODUCT BALANCE
            cur.execute("""
                SELECT total_tonnage, loaded
                FROM shipment_products
                WHERE shipment_id=%s AND product=%s
            """, (shipment_id, product))

            result = cur.fetchone()

            if not result:
                return jsonify({"status": "error", "message": f"{product} not found"})

            total, loaded = result

            if loaded + tons > total:
                return jsonify({
                    "status": "error",
                    "message": f"{product} exceeds total balance"
                })

            # ✅ INSERT OPERATION
            cur.execute("""
                INSERT INTO shipment_report_items
                (report_id, product, hatch, pcs, tons, trips, gangs, mode)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                    report_id,
                    product,
                    hatch,
                    pcs,
                    tons,
                    trips,
                    gangs,
                    mode
                ))

            # 🔄 UPDATE PRODUCT TOTAL
            cur.execute("""
                UPDATE shipment_products
                SET loaded = loaded + %s
                WHERE shipment_id=%s AND product=%s
            """, (
                tons,
                shipment_id,
                product
            ))

        # 🔥 CHECK COMPLETION
        cur.execute("""
            SELECT COUNT(*) FROM shipment_products
            WHERE shipment_id=%s AND loaded < total_tonnage
        """, (shipment_id,))

        remaining = cur.fetchone()[0]
        status = "COMPLETED" if remaining == 0 else "ONGOING"

        cur.execute("""
            UPDATE shipments SET status=%s
            WHERE id=%s
        """, (status, shipment_id))

        conn.commit()

        return jsonify({
            "status": "success",
            "report_id": report_id,
            "shipment_status": status
        })

    except Exception as e:
        import traceback

        conn.rollback()

        print("\n===== SUBMIT OUTTURN ERROR =====")
        print(traceback.format_exc())
        print("================================\n")

        return jsonify({
            "status": "error",
            "message": str(e)
        })

    finally:
        cur.close()
        conn.close()

@app.route('/get_shipment_progress/<int:shipment_id>', methods=['GET'])
def get_shipment_progress(shipment_id):

    conn = get_connection()
    cur = conn.cursor()

    try:

        # ================= PRODUCT TOTALS =================

        cur.execute("""
            SELECT
                sp.product,
                sp.total_tonnage,
                sp.total_pcs,
                sp.loaded,

                COALESCE(SUM(sri.pcs), 0)
            FROM shipment_products sp

            LEFT JOIN shipment_reports sr
                ON sr.shipment_id = sp.shipment_id

            LEFT JOIN shipment_report_items sri
                ON sri.report_id = sr.id
                AND sri.product = sp.product

            WHERE sp.shipment_id = %s

            GROUP BY
                sp.product,
                sp.total_tonnage,
                sp.total_pcs,
                sp.loaded
        """, (shipment_id,))

        product_rows = cur.fetchall()

        progress = {}

        for product, total_tonnage, total_pcs, loaded_tons, loaded_pcs in product_rows:
            progress[product] = {
                "total_tonnage": float(total_tonnage),
                "total_pcs": float(total_pcs),

                "loaded_tons": float(loaded_tons),
                "loaded_pcs": float(loaded_pcs),

                "balance_tons": float(total_tonnage) - float(loaded_tons),
                "balance_pcs": float(total_pcs) - float(loaded_pcs)
            }
        # ================= LAST REPORT =================
        cur.execute("""
            SELECT
                vessel_name
            FROM shipment_reports
            WHERE shipment_id = %s
            ORDER BY id DESC
            LIMIT 1
        """, (shipment_id,))

        last_report = cur.fetchone()

        vessel_name = ""

        if last_report:
            vessel_name = last_report[0] or ""

        # ================= FINAL RESPONSE =================
        return jsonify({
            "progress": progress,
            "vessel_name": vessel_name
        })

    except Exception as e:

        return jsonify({
            "error": str(e)
        })

    finally:
        cur.close()
        conn.close()

@app.route('/get_active_shipments', methods=['POST'])
def get_active_shipments():
    data = request.json
    username = data.get("username")

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT id, shipment_code, agent, port, berth, status
            FROM shipments
            WHERE status != 'COMPLETED'
            AND assigned_clerk = %s
            ORDER BY id DESC
        """, (username,))

        rows = cur.fetchall()

        result = []
        for r in rows:
            result.append({
                "id": r[0],
                "shipment_code": r[1],
                "agent": r[2],
                "port": r[3],
                "berth": r[4],
                "status": r[5]
            })

        return jsonify(result)

    finally:
        cur.close()
        conn.close()

@app.route('/get_full_shipment/<int:shipment_id>', methods=['GET'])
def get_full_shipment(shipment_id):
    conn = get_connection()
    cur = conn.cursor()

    try:
        # =========================
        # 🔥 GET SHIPMENT INFO
        # =========================
        cur.execute("""
            SELECT shipment_code, agent, port, berth, operation_type, supervisor_name, status
            FROM shipments
            WHERE id=%s
        """, (shipment_id,))

        shipment = cur.fetchone()

        if not shipment:
            return jsonify({"error": "Shipment not found"}), 404

        shipment_code, agent, port, berth, operation_type, supervisor_name, status = shipment

        # =========================
        # 🔥 GET PRODUCTS
        # =========================
        cur.execute("""
            SELECT product, total_tonnage, total_pcs, loaded
            FROM shipment_products
            WHERE shipment_id=%s
        """, (shipment_id,))

        product_rows = cur.fetchall()

        # =========================
        # 🔥 GET HATCHES
        # =========================
        cur.execute("""
            SELECT product, hatch
            FROM shipment_hatches
            WHERE shipment_id=%s
        """, (shipment_id,))

        hatch_rows = cur.fetchall()

        # =========================
        # 🔥 BUILD PRODUCT STRUCTURE
        # =========================
        product_map = {}

        for product, total, total_pcs, loaded in product_rows:
            product_map[product] = {
                "name": product,
                "total_tonnage": float(total),
                "total_pcs": float(total_pcs),  # 🔥 ADD THIS
                "total_loaded": float(loaded),
                "balance": float(total) - float(loaded),
                "hatches": []
            }

        for product, hatch in hatch_rows:
            if product in product_map:
                product_map[product]["hatches"].append(hatch)

        # =========================
        # 🔥 FINAL RESPONSE
        # =========================
        return jsonify({
            "shipment_id": shipment_id,
            "shipment_code": shipment_code,
            "agent": agent,
            "port": port,
            "berth": berth,
            "operation_type": operation_type,
            "supervisor_name": supervisor_name,
            "status": status,
            "products": list(product_map.values())
        })

    except Exception as e:
        return jsonify({"error": str(e)})

    finally:
        cur.close()
        conn.close()

@app.route('/create_shipment', methods=['POST'])
def create_shipment():
    import traceback
    from datetime import datetime

    data = request.json

    try:
        conn = get_connection()
        cur = conn.cursor()

        # ================= GET DATA =================
        agent = data.get("agent")
        port = data.get("port")
        berth = data.get("berth")
        operation_type = data.get("operation_type")

        start_date = data.get("start_date")
        start_time = data.get("start_time")

        tally_clerk = data.get("tally_clerk")

        products = data.get("products", [])

        # 🔥 OPTIONAL (AUTO SUPERVISOR FROM USER SESSION)
        supervisor_name = data.get("created_by", "Supervisor")

        # ================= VALIDATION =================
        if not all([agent, port, berth, operation_type, tally_clerk]):
            return jsonify({"error": "Missing required fields"}), 400

        if not products:
            return jsonify({"error": "No products provided"}), 400

        # ================= FORMAT DATETIME =================
        start_datetime = None
        if start_date and start_time:
            try:
                start_datetime = datetime.strptime(
                    f"{start_date} {start_time}",
                    "%Y-%m-%d %H:%M"
                )
            except Exception as e:
                print("DATETIME ERROR:", e)
                start_datetime = None

        # ================= INSERT SHIPMENT =================
        cur.execute("""
            INSERT INTO shipments (
                agent,
                port,
                berth,
                operation_type,
                start_datetime,
                assigned_clerk,
                supervisor_name,
                status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            agent,
            port,
            berth,
            operation_type,
            start_datetime,
            tally_clerk,
            supervisor_name,
            "ONGOING"
        ))

        shipment_id = cur.fetchone()[0]

        shipment_code = f"SHP-{str(shipment_id).zfill(4)}"

        cur.execute("""
            UPDATE shipments
            SET shipment_code=%s
            WHERE id=%s
        """, (shipment_code, shipment_id))

        # ================= PRODUCTS + HATCHES =================
        for p in products:
            product_name = p.get("name")
            total_tonnage = p.get("total_tonnage")

            if total_tonnage is None:
                raise Exception(f"Tonnage missing for product {product_name}")

            # 🔹 PRODUCT TABLE
            total_pcs = p.get("total_pcs", 0)

            cur.execute("""
                INSERT INTO shipment_products
                (shipment_id, product, total_tonnage, total_pcs, loaded)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                shipment_id,
                product_name,
                float(total_tonnage),
                float(total_pcs),  # 🔥 NEW
                0
            ))

            # 🔹 HATCH TABLE
            for hatch in p.get("hatches", []):
                cur.execute("""
                    INSERT INTO shipment_hatches
                    (shipment_id, product, hatch)
                    VALUES (%s, %s, %s)
                """, (
                    shipment_id,
                    product_name,
                    hatch
                ))

        conn.commit()

        return jsonify({
            "shipment_id": shipment_id,
            "shipment_code": shipment_code,
            "status": "success"
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

    finally:
        cur.close()
        conn.close()


@app.route('/get_next_form/<int:shipment_id>')
def get_next_form(shipment_id):

    conn = get_connection()
    cur = conn.cursor()

    try:

        # 🔥 GET SHIPMENT CODE
        cur.execute("""
            SELECT shipment_code
            FROM shipments
            WHERE id = %s
        """, (shipment_id,))

        shipment = cur.fetchone()

        if not shipment:
            return jsonify({"error": "Shipment not found"})

        shipment_code = shipment[0]

        # 🔥 COUNT EXISTING REPORTS
        cur.execute("""
            SELECT COUNT(*)
            FROM shipment_reports
            WHERE shipment_id = %s
        """, (shipment_id,))

        count = cur.fetchone()[0]

        next_no = count + 1

        report_code = f"{shipment_code}-{next_no:02d}"

        from datetime import datetime, timedelta

        # 🔥 GET LAST REPORT END TIME
        cur.execute("""
            SELECT end_time
            FROM shipment_reports
            WHERE shipment_id = %s
            ORDER BY id DESC
            LIMIT 1
        """, (shipment_id,))

        last = cur.fetchone()

        if last and last[0]:

            # Convert string → datetime
            start_dt = datetime.strptime(
                last[0],
                "%Y-%m-%d %H:%M"
            )
        else:
            # FIRST REPORT
            cur.execute("""
                SELECT start_datetime
                FROM shipments
                WHERE id = %s
            """, (shipment_id,))

            shipment_start = cur.fetchone()

            start_dt = (
                shipment_start[0]
                if shipment_start and shipment_start[0]
                else datetime.now()
            )

        # 🔥 AUTO +8 HOURS
        end_dt = start_dt + timedelta(hours=8)

        return jsonify({
            "report_no": next_no,
            "report_id": report_code,

            # TEMPORARY BACKWARD COMPATIBILITY
            "form_no": next_no,
            "form_code": report_code,

            "start_time": start_dt.strftime("%Y-%m-%d %H:%M"),
            "end_time": end_dt.strftime("%Y-%m-%d %H:%M")
        })

    except Exception as e:
        return jsonify({"error": str(e)})

    finally:
        cur.close()
        conn.close()

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

@app.route('/get_tally_clerks', methods=['GET'])
def get_tally_clerks():
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT username FROM users_v2
            WHERE role ILIKE '%tally%'
        """)

        clerks = [r[0] for r in cur.fetchall()]

        return jsonify({"clerks": clerks})

    finally:
        cur.close()
        conn.close()

@app.route('/get_setup_data', methods=['GET'])
def get_setup_data():
    conn = get_connection()
    cur = conn.cursor()

    try:
        # AGENTS
        cur.execute("""
            SELECT username FROM users_v2
            WHERE role ILIKE '%agent%'
        """)
        agents = [r[0] for r in cur.fetchall()]

        # PORTS
        cur.execute("SELECT name FROM ports ORDER BY name")
        ports = [r[0] for r in cur.fetchall()]

        return jsonify({
            "agents": agents,
            "ports": ports
        })

    finally:
        cur.close()
        conn.close()

@app.route('/get_berths/<port>', methods=['GET'])
def get_berths_by_port(port):
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT b.name
            FROM berths b
            JOIN ports p ON b.port_id = p.id
            WHERE p.name=%s
        """, (port,))

        berths = [r[0] for r in cur.fetchall()]

        return jsonify({"berths": berths})

    finally:
        cur.close()
        conn.close()

@app.route('/get_last_report/<int:shipment_id>')
def get_last_report(shipment_id):

    conn = get_connection()
    cur = conn.cursor()

    try:

        cur.execute("""
            SELECT vessel_name
            FROM shipment_reports
            WHERE shipment_id = %s
            ORDER BY id DESC
            LIMIT 1
        """, (shipment_id,))

        row = cur.fetchone()

        if not row:
            return jsonify({})

        return jsonify({
            "vessel_name": row[0] or ""
        })

    except Exception as e:
        return jsonify({"error": str(e)})

    finally:
        cur.close()
        conn.close()

@app.route('/get_all_shipments', methods=['GET'])
def get_all_shipments():

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, shipment_code, agent, port, berth, operation_type, status
        FROM shipments
        WHERE status != 'DELETED'
        ORDER BY id DESC
    """)

    rows = cur.fetchall()

    result = []
    for r in rows:
        result.append({
            "id": r[0],
            "shipment_code": r[1],
            "agent": r[2],
            "port": r[3],
            "berth": r[4],
            "operation_type": r[5],
            "status": r[6]
        })

    cur.close()
    conn.close()

    return jsonify(result)

def has_reports(cur, shipment_id):
    cur.execute("""
        SELECT COUNT(*) FROM shipment_reports
        WHERE shipment_id = %s
    """, (shipment_id,))
    return cur.fetchone()[0] > 0

@app.route('/get_shipment_edit_details/<int:shipment_id>', methods=['GET'])
def get_shipment_edit_details(shipment_id):
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT id, shipment_code, agent, port, berth, operation_type, assigned_clerk, status
            FROM shipments
            WHERE id = %s
        """, (shipment_id,))

        row = cur.fetchone()

        if not row:
            return jsonify({
                "status": "error",
                "message": "Shipment not found"
            }), 404

        return jsonify({
            "id": row[0],
            "shipment_code": row[1] or "",
            "agent": row[2] or "",
            "port": row[3] or "",
            "berth": row[4] or "",
            "operation_type": row[5] or "",
            "assigned_clerk": row[6] or "",
            "status": row[7] or "",
            "has_reports": has_reports(cur, shipment_id)
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

    finally:
        cur.close()
        conn.close()

@app.route('/update_shipment', methods=['POST'])
def update_shipment():
    data = request.json
    conn = get_connection()
    cur = conn.cursor()

    try:
        shipment_id = data.get("shipment_id")

        if not shipment_id:
            return jsonify({
                "status": "error",
                "message": "Shipment ID missing"
            }), 400

        cur.execute("SELECT id FROM shipments WHERE id=%s", (shipment_id,))
        exists = cur.fetchone()

        if not exists:
            return jsonify({
                "status": "error",
                "message": "Shipment not found"
            }), 404

        report_exists = has_reports(cur, shipment_id)

        if not report_exists:
            cur.execute("""
                UPDATE shipments
                SET agent=%s,
                    port=%s,
                    berth=%s,
                    operation_type=%s,
                    assigned_clerk=%s
                WHERE id=%s
            """, (
                data.get("agent"),
                data.get("port"),
                data.get("berth"),
                data.get("operation_type"),
                data.get("assigned_clerk"),
                shipment_id
            ))
            edit_mode = "full"
        else:
            cur.execute("""
                UPDATE shipments
                SET assigned_clerk=%s
                WHERE id=%s
            """, (
                data.get("assigned_clerk"),
                shipment_id
            ))
            edit_mode = "limited"

        conn.commit()

        return jsonify({
            "status": "updated",
            "mode": edit_mode
        })

    except Exception as e:
        conn.rollback()
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

    finally:
        cur.close()
        conn.close()

@app.route('/delete_shipment', methods=['POST'])
def delete_shipment():

    data = request.json
    conn = get_connection()
    cur = conn.cursor()

    try:
        shipment_id = data.get("shipment_id")

        cur.execute("""
            UPDATE shipments
            SET status = 'DELETED'
            WHERE id = %s
        """, (shipment_id,))

        conn.commit()

        return jsonify({"status": "deleted"})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

    finally:
        cur.close()
        conn.close()

@app.route('/get_outturn_reports', methods=['POST'])
def get_outturn_reports():

    data = request.json

    username = data.get("username")
    role = data.get("role")

    conn = get_connection()
    cur = conn.cursor()

    try:

        # =========================================
        # 🔥 ADMIN → VIEW ALL REPORTS
        # =========================================

        admin_roles = [
            "System Admin",
            "Admin Staff",
            "Director",
            "Manager",
            "Supervisor"
        ]

        if role in admin_roles:

            cur.execute("""
                SELECT
                    sr.id,
                    sr.report_id,
                    s.shipment_code,
                    s.agent,
                    sr.vessel_name,
                    sr.date,
                    sr.start_time,
                    sr.end_time,
                    sr.created_by,
                    s.status

                FROM shipment_reports sr

                JOIN shipments s
                    ON sr.shipment_id = s.id

                ORDER BY sr.id DESC
            """)

        # =========================================
        # 🔥 TALLY CLERK → ONLY OWN REPORTS
        # =========================================

        elif "tally" in role.lower() or "clerk" in role.lower():

            cur.execute("""
                SELECT
                    sr.id,
                    sr.report_id,
                    s.shipment_code,
                    s.agent,
                    sr.vessel_name,
                    sr.date,
                    sr.start_time,
                    sr.end_time,
                    sr.created_by,
                    s.status

                FROM shipment_reports sr

                JOIN shipments s
                    ON sr.shipment_id = s.id

                WHERE LOWER(sr.created_by) = LOWER(%s)

                ORDER BY sr.id DESC
            """, (username,))

        # =========================================
        # 🔥 AGENT → ONLY THEIR AGENT REPORTS
        # =========================================

        else:

            cur.execute("""
                SELECT
                    sr.id,
                    sr.report_id,
                    s.shipment_code,
                    s.agent,
                    sr.vessel_name,
                    sr.date,
                    sr.start_time,
                    sr.end_time,
                    sr.created_by,
                    s.status

                FROM shipment_reports sr

                JOIN shipments s
                    ON sr.shipment_id = s.id

                WHERE LOWER(s.agent) = LOWER(%s)

                ORDER BY sr.id DESC
            """, (username,))

        rows = cur.fetchall()

        result = []

        for r in rows:

            result.append({
                "id": r[0],
                "report_id": r[1],
                "shipment_code": r[2],
                "agent": r[3],
                "vessel_name": r[4],
                "date": str(r[5]),
                "start_time": str(r[6]),
                "end_time": str(r[7]),
                "created_by": r[8],
                "status": r[9]
            })

        return jsonify(result)

    except Exception as e:

        return jsonify({
            "status": "error",
            "message": str(e)
        })

    finally:
        cur.close()
        conn.close()

@app.route('/get_report_details/<int:report_db_id>', methods=['GET'])
def get_report_details(report_db_id):

    import json

    conn = get_connection()
    cur = conn.cursor()

    try:

        # =========================================
        # REPORT + SHIPMENT INFO
        # =========================================

        cur.execute("""
            SELECT
                sr.id,
                sr.report_no,
                sr.report_id,
                sr.shipment_id,
                sr.date,
                sr.start_time,
                sr.end_time,
                sr.delays,
                sr.remarks,
                sr.vessel_name,
                sr.created_by,

                s.shipment_code,
                s.agent,
                s.port,
                s.berth,
                s.operation_type,
                s.status

            FROM shipment_reports sr

            JOIN shipments s
                ON sr.shipment_id = s.id

            WHERE sr.id = %s
        """, (report_db_id,))

        report = cur.fetchone()

        if not report:
            return jsonify({"error": "Report not found"})

        (
            db_id,
            report_no,
            report_code,
            shipment_id,
            report_date,
            start_time,
            end_time,
            delays,
            remarks,
            vessel_name,
            created_by,
            shipment_code,
            agent,
            port,
            berth,
            operation_type,
            status
        ) = report

        # =========================================
        # OPERATIONS
        # =========================================

        cur.execute("""
            SELECT
                product,
                hatch,
                pcs,
                tons,
                trips,
                gangs,
                mode

            FROM shipment_report_items

            WHERE report_id = %s
        """, (db_id,))

        operation_rows = cur.fetchall()

        operations = []

        for row in operation_rows:

            operations.append({
                "product": row[0],
                "hatch": row[1],
                "pcs": float(row[2]),
                "tons": float(row[3]),
                "trips": row[4],
                "gangs": row[5],
                "mode": row[6],
                "pcs_balance": 0,
                "tons_balance": 0
            })

        # =========================================
        # PRODUCTS
        # =========================================

        cur.execute("""
            SELECT
                product,
                total_tonnage,
                total_pcs,
                loaded

            FROM shipment_products

            WHERE shipment_id = %s
        """, (shipment_id,))

        product_rows = cur.fetchall()

        products = []

        loaded_total = 0

        for p in product_rows:

            loaded_total += float(p[3])

            products.append({
                "name": p[0],
                "total_tonnage": float(p[1]),
                "total_pcs": float(p[2]),
                "loaded": float(p[3])
            })

        shipment_data = {
            "shipment_code": shipment_code,
            "agent": agent,
            "port": port,
            "berth": berth,
            "operation_type": operation_type,
            "status": status,
            "products": products,
            "loaded_tons": loaded_total,
            "vessel_name": vessel_name
        }

        return jsonify({
            "shipment_id": shipment_id,
            "shipment_code": shipment_code,

            "form_no": report_no,
            "form_code": report_code,

            "start_time": start_time,
            "end_time": end_time,

            "operations": operations,
            "shipment_data": shipment_data,

            "delays": json.loads(delays) if delays else [],
            "remarks": json.loads(remarks) if remarks else [],

            "current_user": created_by
        })

    except Exception as e:

        return jsonify({
            "status": "error",
            "message": str(e)
        })

    finally:
        cur.close()
        conn.close()

@app.route('/get_shipments_by_agent', methods=['POST'])
def get_shipments_by_agent():
    data = request.json
    agent = data.get("agent")

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT id, shipment_code, port, berth, status
            FROM shipments
            WHERE LOWER(agent) = LOWER(%s)
              AND status != 'DELETED'
            ORDER BY id DESC
        """, (agent,))

        rows = cur.fetchall()

        result = []
        for r in rows:
            result.append({
                "id": r[0],
                "shipment_code": r[1],
                "port": r[2],
                "berth": r[3],
                "status": r[4]
            })

        return jsonify(result)

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

    finally:
        cur.close()
        conn.close()


@app.route('/get_reports_by_shipment/<int:shipment_id>', methods=['GET'])
def get_reports_by_shipment(shipment_id):
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT
                id,
                report_no,
                report_id,
                date,
                start_time,
                end_time,
                vessel_name,
                created_by
            FROM shipment_reports
            WHERE shipment_id = %s
            ORDER BY id DESC
        """, (shipment_id,))

        rows = cur.fetchall()

        result = []
        for r in rows:
            result.append({
                "id": r[0],
                "report_no": r[1],
                "report_id": r[2],
                "date": str(r[3]),
                "start_time": str(r[4]),
                "end_time": str(r[5]),
                "vessel_name": r[6] or "",
                "created_by": r[7] or ""
            })

        return jsonify(result)

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

    finally:
        cur.close()
        conn.close()

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