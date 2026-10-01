from flask import Flask, request, jsonify, render_template
import sqlite3
from datetime import datetime

app = Flask(__name__)

DATABASE = "assistance.db"


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# =========================================================
# INITIALIZE DATABASE
# =========================================================

def init_database():
    conn = get_db()
    cursor = conn.cursor()

    # Requests table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            brgy TEXT NOT NULL,
            latitude REAL,
            longitude REAL,
            request_type TEXT NOT NULL,
            story TEXT,
            members INTEGER DEFAULT 1,
            priority TEXT DEFAULT 'Medium',
            status TEXT DEFAULT 'Pending',
            volunteer_id INTEGER,
            created_at TEXT NOT NULL
        )
    """)

    # Volunteers table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS volunteers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            skill TEXT NOT NULL,
            area TEXT NOT NULL,
            latitude REAL,
            longitude REAL,
            tasks INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():
    return render_template("index.html")


# =========================================================
# GET ALL REQUESTS
# =========================================================

@app.route("/api/requests", methods=["GET"])
def get_requests():

    conn = get_db()

    rows = conn.execute("""
        SELECT
            r.*,
            v.name AS volunteer_name
        FROM requests r
        LEFT JOIN volunteers v
        ON r.volunteer_id = v.id
        ORDER BY r.id DESC
    """).fetchall()

    conn.close()

    requests = []

    for row in rows:
        requests.append({
            "id": row["id"],
            "name": row["name"],
            "phone": row["phone"],
            "brgy": row["brgy"],
            "coords": [
                row["latitude"],
                row["longitude"]
            ] if row["latitude"] is not None and row["longitude"] is not None else None,
            "type": row["request_type"],
            "story": row["story"],
            "members": row["members"],
            "priority": row["priority"],
            "status": row["status"],
            "vol": row["volunteer_name"] or "",
            "volunteer_id": row["volunteer_id"],
            "date": row["created_at"]
        })

    return jsonify(requests)


# =========================================================
# ADD REQUEST
# =========================================================

@app.route("/api/requests", methods=["POST"])
def add_request():

    data = request.get_json()

    if not data:
        return jsonify({
            "success": False,
            "message": "No data received."
        }), 400

    name = data.get("name", "").strip()
    phone = data.get("phone", "").strip()
    brgy = data.get("brgy", "").strip()
    request_type = data.get("type", "").strip()
    story = data.get("story", "").strip()
    members = data.get("members", 1)
    priority = data.get("priority", "Medium")

    coords = data.get("coords")

    latitude = None
    longitude = None

    if coords and len(coords) >= 2:
        latitude = coords[0]
        longitude = coords[1]

    if not name or not phone or not brgy or not request_type:
        return jsonify({
            "success": False,
            "message": "Please complete all required fields."
        }), 400

    conn = get_db()

    cursor = conn.execute("""
        INSERT INTO requests
        (
            name,
            phone,
            brgy,
            latitude,
            longitude,
            request_type,
            story,
            members,
            priority,
            status,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        name,
        phone,
        brgy,
        latitude,
        longitude,
        request_type,
        story,
        members,
        priority,
        "Pending",
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()

    request_id = cursor.lastrowid

    conn.close()

    return jsonify({
        "success": True,
        "message": "Assistance request submitted successfully.",
        "id": request_id
    })


# =========================================================
# GET ALL VOLUNTEERS
# =========================================================

@app.route("/api/volunteers", methods=["GET"])
def get_volunteers():

    conn = get_db()

    rows = conn.execute("""
        SELECT *
        FROM volunteers
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    volunteers = []

    for row in rows:
        volunteers.append({
            "id": row["id"],
            "name": row["name"],
            "phone": row["phone"],
            "skill": row["skill"],
            "area": row["area"],
            "coords": [
                row["latitude"],
                row["longitude"]
            ] if row["latitude"] is not None and row["longitude"] is not None else None,
            "tasks": row["tasks"]
        })

    return jsonify(volunteers)


# =========================================================
# ADD VOLUNTEER
# =========================================================

@app.route("/api/volunteers", methods=["POST"])
def add_volunteer():

    data = request.get_json()

    if not data:
        return jsonify({
            "success": False,
            "message": "No data received."
        }), 400

    name = data.get("name", "").strip()
    phone = data.get("phone", "").strip()
    skill = data.get("skill", "").strip()
    area = data.get("area", "").strip()

    coords = data.get("coords")

    latitude = None
    longitude = None

    if coords and len(coords) >= 2:
        latitude = coords[0]
        longitude = coords[1]

    if not name or not phone or not skill or not area:
        return jsonify({
            "success": False,
            "message": "Please complete all required fields."
        }), 400

    conn = get_db()

    cursor = conn.execute("""
        INSERT INTO volunteers
        (
            name,
            phone,
            skill,
            area,
            latitude,
            longitude,
            tasks,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        name,
        phone,
        skill,
        area,
        latitude,
        longitude,
        0,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()

    volunteer_id = cursor.lastrowid

    conn.close()

    return jsonify({
        "success": True,
        "message": "Volunteer registered successfully.",
        "id": volunteer_id
    })


# =========================================================
# DASHBOARD STATISTICS
# =========================================================

@app.route("/api/dashboard", methods=["GET"])
def dashboard():

    conn = get_db()

    total_requests = conn.execute("""
        SELECT COUNT(*) FROM requests
    """).fetchone()[0]

    total_volunteers = conn.execute("""
        SELECT COUNT(*) FROM volunteers
    """).fetchone()[0]

    completed = conn.execute("""
        SELECT COUNT(*)
        FROM requests
        WHERE status = 'Done'
    """).fetchone()[0]

    urgent = conn.execute("""
        SELECT COUNT(*)
        FROM requests
        WHERE priority = 'High'
        AND status != 'Done'
    """).fetchone()[0]

    pending = conn.execute("""
        SELECT COUNT(*)
        FROM requests
        WHERE status = 'Pending'
    """).fetchone()[0]

    ongoing = conn.execute("""
        SELECT COUNT(*)
        FROM requests
        WHERE status = 'Ongoing'
    """).fetchone()[0]

    conn.close()

    return jsonify({
        "requests": total_requests,
        "volunteers": total_volunteers,
        "done": completed,
        "urgent": urgent,
        "pending": pending,
        "ongoing": ongoing
    })


# =========================================================
# ASSIGN VOLUNTEER TO REQUEST
# =========================================================

@app.route("/api/requests/<int:request_id>/assign", methods=["PUT"])
def assign_volunteer(request_id):

    data = request.get_json()

    if not data:
        return jsonify({
            "success": False,
            "message": "No data received."
        }), 400

    volunteer_id = data.get("volunteer_id")

    if not volunteer_id:
        return jsonify({
            "success": False,
            "message": "Volunteer ID is required."
        }), 400

    conn = get_db()

    volunteer = conn.execute("""
        SELECT *
        FROM volunteers
        WHERE id = ?
    """, (volunteer_id,)).fetchone()

    if not volunteer:
        conn.close()

        return jsonify({
            "success": False,
            "message": "Volunteer not found."
        }), 404

    request_row = conn.execute("""
        SELECT *
        FROM requests
        WHERE id = ?
    """, (request_id,)).fetchone()

    if not request_row:
        conn.close()

        return jsonify({
            "success": False,
            "message": "Request not found."
        }), 404

    conn.execute("""
        UPDATE requests
        SET volunteer_id = ?,
            status = 'Approved'
        WHERE id = ?
    """, (volunteer_id, request_id))

    conn.execute("""
        UPDATE volunteers
        SET tasks = tasks + 1
        WHERE id = ?
    """, (volunteer_id,))

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "message": "Volunteer assigned successfully."
    })


# =========================================================
# CHANGE REQUEST STATUS
# =========================================================

@app.route("/api/requests/<int:request_id>/status", methods=["PUT"])
def update_status(request_id):

    data = request.get_json()

    if not data:
        return jsonify({
            "success": False,
            "message": "No data received."
        }), 400

    status = data.get("status")

    allowed_statuses = [
        "Pending",
        "Approved",
        "Ongoing",
        "Done"
    ]

    if status not in allowed_statuses:
        return jsonify({
            "success": False,
            "message": "Invalid status."
        }), 400

    conn = get_db()

    request_row = conn.execute("""
        SELECT *
        FROM requests
        WHERE id = ?
    """, (request_id,)).fetchone()

    if not request_row:
        conn.close()

        return jsonify({
            "success": False,
            "message": "Request not found."
        }), 404

    conn.execute("""
        UPDATE requests
        SET status = ?
        WHERE id = ?
    """, (status, request_id))

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "message": "Request status updated.",
        "status": status
    })


# =========================================================
# DELETE REQUEST
# =========================================================

@app.route("/api/requests/<int:request_id>", methods=["DELETE"])
def delete_request(request_id):

    conn = get_db()

    request_row = conn.execute("""
        SELECT *
        FROM requests
        WHERE id = ?
    """, (request_id,)).fetchone()

    if not request_row:
        conn.close()

        return jsonify({
            "success": False,
            "message": "Request not found."
        }), 404

    conn.execute("""
        DELETE FROM requests
        WHERE id = ?
    """, (request_id,))

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "message": "Request deleted successfully."
    })


# =========================================================
# DELETE VOLUNTEER
# =========================================================

@app.route("/api/volunteers/<int:volunteer_id>", methods=["DELETE"])
def delete_volunteer(volunteer_id):

    conn = get_db()

    volunteer = conn.execute("""
        SELECT *
        FROM volunteers
        WHERE id = ?
    """, (volunteer_id,)).fetchone()

    if not volunteer:
        conn.close()

        return jsonify({
            "success": False,
            "message": "Volunteer not found."
        }), 404

    # Remove volunteer assignment from requests
    conn.execute("""
        UPDATE requests
        SET volunteer_id = NULL
        WHERE volunteer_id = ?
    """, (volunteer_id,))

    # Delete volunteer
    conn.execute("""
        DELETE FROM volunteers
        WHERE id = ?
    """, (volunteer_id,))

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "message": "Volunteer deleted successfully."
    })


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":
    init_database()

    print("--------------------------------------------")
    print(" ASSISTANCE & VOLUNTEER MANAGEMENT SYSTEM")
    print("--------------------------------------------")
    print("Server running at:")
    print("http://127.0.0.1:5000")
    print("--------------------------------------------")

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )