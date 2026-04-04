from flask import Flask, render_template, request, jsonify
import mysql.connector
import random
from datetime import datetime, timedelta

app = Flask(__name__)

# ─── DB CONNECTION ───────────────────────────────────────────────
def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",        # change to your MySQL password
        database="gigshield"
    )

# ─── PAGES ───────────────────────────────────────────────────────
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/register")
def register_page():
    return render_template("register.html")

@app.route("/policy")
def policy_page():
    return render_template("policy.html")

@app.route("/claims")
def claims_page():
    return render_template("claims.html")

# ─── API: REGISTER WORKER ────────────────────────────────────────
@app.route("/api/register", methods=["POST"])
def register():
    data = request.json
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO workers (name, phone, city, zone, platform)
        VALUES (%s, %s, %s, %s, %s)
    """, (data["name"], data["phone"], data["city"], data["zone"], data["platform"]))
    db.commit()
    worker_id = cursor.lastrowid
    cursor.close()
    db.close()
    return jsonify({"success": True, "worker_id": worker_id})

# ─── API: CALCULATE PREMIUM (Simple ML logic) ────────────────────
@app.route("/api/calculate-premium", methods=["POST"])
def calculate_premium():
    data = request.json
    zone = data.get("zone", "low")
    platform = data.get("platform", "other")

    # Simple rule-based model (you can replace with sklearn later)
    base = 50
    zone_risk = {"high": 30, "medium": 15, "low": 0}
    platform_bonus = {"amazon_flex": 10, "flipkart_ekart": 5}

    premium = base + zone_risk.get(zone, 0) + platform_bonus.get(platform, 0)
    coverage = premium * 10  # 10x coverage

    return jsonify({
        "weekly_premium": premium,
        "coverage_amount": coverage,
        "risk_level": zone
    })

# ─── API: CREATE POLICY ──────────────────────────────────────────
@app.route("/api/create-policy", methods=["POST"])
def create_policy():
    data = request.json
    db = get_db()
    cursor = db.cursor()
    start = datetime.today()
    end = start + timedelta(days=30)
    cursor.execute("""
        INSERT INTO policies (worker_id, plan, weekly_premium, coverage_amount, start_date, end_date, status)
        VALUES (%s, %s, %s, %s, %s, %s, 'active')
    """, (data["worker_id"], data["plan"], data["weekly_premium"], data["coverage_amount"], start, end))
    db.commit()
    cursor.close()
    db.close()
    return jsonify({"success": True})

# ─── API: GET WORKER POLICIES ────────────────────────────────────
@app.route("/api/policies/<int:worker_id>")
def get_policies(worker_id):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM policies WHERE worker_id = %s", (worker_id,))
    policies = cursor.fetchall()
    # Convert dates to string
    for p in policies:
        p["start_date"] = str(p["start_date"])
        p["end_date"] = str(p["end_date"])
    cursor.close()
    db.close()
    return jsonify(policies)

# ─── API: CHECK DISRUPTIONS & AUTO-TRIGGER CLAIMS ────────────────
@app.route("/api/check-disruptions", methods=["POST"])
def check_disruptions():
    data = request.json
    worker_id = data["worker_id"]
    city = data.get("city", "Mumbai")

    # Mock disruption signals (replace with real APIs later)
    disruptions = []

    # Signal 1: Weather (mock)
    weather_risk = random.choice([True, False])
    if weather_risk:
        disruptions.append("Heavy rainfall detected in your zone")

    # Signal 2: AQI (mock)
    aqi = random.randint(100, 400)
    if aqi > 300:
        disruptions.append(f"Hazardous AQI level: {aqi}")

    # Signal 3: Hub closure (mock)
    hub_closed = random.choice([True, False, False])  # less likely
    if hub_closed:
        disruptions.append("Delivery hub reported as closed")

    # If 2+ signals → auto trigger claim
    if len(disruptions) >= 2:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT id FROM policies WHERE worker_id = %s AND status='active' LIMIT 1", (worker_id,))
        policy = cursor.fetchone()
        if policy:
            cursor.execute("""
                INSERT INTO claims (worker_id, policy_id, reason, status, amount, triggered_at)
                VALUES (%s, %s, %s, 'triggered', 500, NOW())
            """, (worker_id, policy["id"], " | ".join(disruptions)))
            db.commit()
        cursor.close()
        db.close()
        return jsonify({"claim_triggered": True, "reasons": disruptions})

    return jsonify({"claim_triggered": False, "reasons": disruptions})

# ─── API: GET CLAIMS ─────────────────────────────────────────────
@app.route("/api/claims/<int:worker_id>")
def get_claims(worker_id):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM claims WHERE worker_id = %s ORDER BY triggered_at DESC", (worker_id,))
    claims = cursor.fetchall()
    for c in claims:
        c["triggered_at"] = str(c["triggered_at"])
    cursor.close()
    db.close()
    return jsonify(claims)

if __name__ == "__main__":
    app.run(debug=True)
