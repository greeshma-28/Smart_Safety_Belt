from flask import Flask, render_template, request, jsonify, redirect, session
import sqlite3

app = Flask(__name__)

# Session ke liye secret key
app.secret_key = "astrsafe_secret_key_2026"


# =========================
# DATABASE
# =========================

def create_database():
    conn = sqlite3.connect("safety_belt.db")
    cursor = conn.cursor()

    # USERS TABLE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    # EMERGENCIES TABLE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS emergencies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            latitude REAL,
            longitude REAL,
            status TEXT,
            date_time TEXT
        )
    """)

    # TRUSTED CONTACTS TABLE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trusted_contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT,
            mobile TEXT
        )
    """)

    conn.commit()
    conn.close()


# =========================
# HOME
# =========================

@app.route("/")
def home():
    return render_template("index.html")


# =========================
# LOGIN
# =========================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("safety_belt.db")
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, name, username
            FROM users
            WHERE username = ? AND password = ?
        """, (username, password))

        user = cursor.fetchone()

        conn.close()

        if user:

            # Store logged-in user's ID
            session["user_id"] = user[0]
            session["user_name"] = user[1]
            session["username"] = user[2]

            return redirect("/dashboard")

        else:
            return "Invalid Username or Password!"

    return render_template("login.html")


# =========================
# REGISTER / CREATE ACCOUNT
# =========================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("safety_belt.db")
        cursor = conn.cursor()

        try:

            cursor.execute("""
                INSERT INTO users (name, username, password)
                VALUES (?, ?, ?)
            """, (name, username, password))

            conn.commit()
            conn.close()

            return redirect("/login")

        except sqlite3.IntegrityError:

            conn.close()

            return "Username already exists. Please choose another username."

    return render_template("register.html")


# =========================
# LOGOUT
# =========================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")


# =========================
# DASHBOARD
# =========================

@app.route("/dashboard")
def dashboard():

    # Check login
    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]

    conn = sqlite3.connect("safety_belt.db")
    cursor = conn.cursor()

    # Count only this user's emergencies
    cursor.execute("""
        SELECT COUNT(*)
        FROM emergencies
        WHERE user_id = ?
    """, (user_id,))

    emergency_count = cursor.fetchone()[0]

    # Recent emergencies of this user
    cursor.execute("""
        SELECT *
        FROM emergencies
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 5
    """, (user_id,))

    recent_emergencies = cursor.fetchall()

    # Latest emergency of this user
    cursor.execute("""
        SELECT status
        FROM emergencies
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 1
    """, (user_id,))

    latest_emergency = cursor.fetchone()

    conn.close()

    return render_template(
        "dashboard.html",
        emergency_count=emergency_count,
        recent_emergencies=recent_emergencies,
        latest_emergency=latest_emergency
    )


# =========================
# TRUSTED CONTACTS
# =========================

@app.route("/contacts", methods=["GET", "POST"])
def contacts():

    # Check login
    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]

    conn = sqlite3.connect("safety_belt.db")
    cursor = conn.cursor()

    if request.method == "POST":

        name = request.form["name"]
        mobile = request.form["mobile"]

        cursor.execute("""
            INSERT INTO trusted_contacts
            (user_id, name, mobile)
            VALUES (?, ?, ?)
        """, (user_id, name, mobile))

        conn.commit()

    # Get only this user's contacts
    cursor.execute("""
        SELECT *
        FROM trusted_contacts
        WHERE user_id = ?
        ORDER BY id DESC
    """, (user_id,))

    contacts = cursor.fetchall()

    conn.close()

    return render_template(
        "contacts.html",
        contacts=contacts
    )


# =========================
# DELETE CONTACT
# =========================

@app.route("/delete_contact/<int:contact_id>", methods=["POST"])
def delete_contact(contact_id):

    # Check login
    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]

    conn = sqlite3.connect("safety_belt.db")
    cursor = conn.cursor()

    # Delete only if contact belongs to logged-in user
    cursor.execute("""
        DELETE FROM trusted_contacts
        WHERE id = ? AND user_id = ?
    """, (contact_id, user_id))

    conn.commit()
    conn.close()

    return redirect("/contacts")


# =========================
# EMERGENCY HISTORY
# =========================

@app.route("/history")
def history():

    # Check login
    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]

    conn = sqlite3.connect("safety_belt.db")
    cursor = conn.cursor()

    # Get only this user's emergencies
    cursor.execute("""
        SELECT *
        FROM emergencies
        WHERE user_id = ?
        ORDER BY id DESC
    """, (user_id,))

    emergencies = cursor.fetchall()

    conn.close()

    return render_template(
        "history.html",
        emergencies=emergencies
    )


# =========================
# ABOUT
# =========================

@app.route("/about")
def about():
    return render_template("about.html")


# =========================
# SOS / EMERGENCY SIMULATION
# =========================

@app.route("/sos", methods=["POST"])
def sos():

    # Check login
    if "user_id" not in session:
        return jsonify({
            "status": "error",
            "message": "User not logged in"
        }), 401

    user_id = session["user_id"]

    data = request.get_json()

    if not data:
        return jsonify({
            "status": "error",
            "message": "No emergency data received"
        }), 400

    latitude = data.get("latitude")
    longitude = data.get("longitude")

    if latitude is None or longitude is None:
        return jsonify({
            "status": "error",
            "message": "Location not available"
        }), 400

    conn = sqlite3.connect("safety_belt.db")
    cursor = conn.cursor()

    # Get only this user's trusted contacts
    cursor.execute("""
        SELECT name, mobile
        FROM trusted_contacts
        WHERE user_id = ?
    """, (user_id,))

    trusted_contacts = cursor.fetchall()

    # Emergency message for simulation
    alert_message = (
        f"EMERGENCY! Location: "
        f"https://www.google.com/maps?q={latitude},{longitude}"
    )

    # Show information in VS Code terminal
    print("\n==============================")
    print("      EMERGENCY DETECTED")
    print("==============================")
    print("User ID:", user_id)
    print("Latitude:", latitude)
    print("Longitude:", longitude)
    print("Trusted Contacts:", trusted_contacts)
    print("Alert Message:", alert_message)
    print("==============================\n")

    # Save emergency for THIS USER
    cursor.execute("""
        INSERT INTO emergencies
        (user_id, latitude, longitude, status, date_time)
        VALUES (?, ?, ?, ?, datetime('now'))
    """, (
        user_id,
        latitude,
        longitude,
        "Emergency Detected"
    ))

    conn.commit()
    conn.close()

    return jsonify({
        "status": "Emergency Detected",
        "message": "Emergency saved successfully",
        "latitude": latitude,
        "longitude": longitude
    })


# =========================
# CREATE DATABASE
# =========================

create_database()


# =========================
# RUN APPLICATION
# =========================

if __name__ == "__main__":
    app.run(debug=True)