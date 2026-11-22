import os, json, sqlite3, datetime, re
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("DATABASE_PATH", os.path.join(APP_DIR, "beast.db"))
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-before-production")

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      email TEXT UNIQUE NOT NULL,
      password_hash TEXT NOT NULL,
      company TEXT DEFAULT 'My Company',
      industry TEXT DEFAULT 'E-commerce & D2C',
      created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS tasks (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      agent TEXT NOT NULL,
      description TEXT DEFAULT '',
      status TEXT DEFAULT 'Queued',
      priority TEXT DEFAULT 'Medium',
      created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS approvals (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      detail TEXT DEFAULT '',
      risk TEXT DEFAULT 'Medium',
      status TEXT DEFAULT 'Pending',
      created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS activity (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      message TEXT NOT NULL,
      kind TEXT DEFAULT 'info',
      created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS brain_notes (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      note TEXT NOT NULL,
      created_at TEXT NOT NULL
    );
    """)
    if conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 0:
        now = datetime.datetime.utcnow().isoformat()
        demo_tasks = [
          ("Analyse competitor pricing", "Market Researcher", "Compare public pricing and positioning.", "Running", "High"),
          ("Draft 7-day content plan", "Growth Marketer", "Prepare a channel-wise content calendar.", "Queued", "Medium"),
          ("Review uncontacted leads", "Sales Agent", "Prioritise leads and draft follow-ups.", "Queued", "High"),
          ("Summarise customer feedback", "Customer Analyst", "Group recurring customer complaints.", "Completed", "Low"),
        ]
        conn.executemany("INSERT INTO tasks(title,agent,description,status,priority,created_at) VALUES(?,?,?,?,?,?)",
                         [(*x, now) for x in demo_tasks])
        demo_approvals = [
          ("Send follow-up campaign", "Draft campaign to 24 opted-in leads. No message will be sent until a real email integration is connected.", "Medium", "Pending"),
          ("Increase ad budget by 10%", "Simulation recommendation only. Review actual ROAS and cash flow before any spend change.", "High", "Pending"),
        ]
        conn.executemany("INSERT INTO approvals(title,detail,risk,status,created_at) VALUES(?,?,?,?,?)",
                         [(*x, now) for x in demo_approvals])
        conn.executemany("INSERT INTO activity(message,kind,created_at) VALUES(?,?,?)", [
          ("BEAST workspace initialised with demo data.", "success", now),
          ("Customer feedback summary completed.", "info", now),
          ("Two actions are waiting for your approval.", "warning", now)
        ])
    conn.commit()
    conn.close()

def current_user():
    if not session.get("user_id"):
        return None
    conn = db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
    conn.close()
    return user

def log(message, kind="info"):
    conn = db()
    conn.execute("INSERT INTO activity(message,kind,created_at) VALUES(?,?,?)",
                 (message, kind, datetime.datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def get_ai_response(prompt, user):
    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key and OpenAI:
        try:
            client = OpenAI(api_key=api_key)
            company = user["company"] if user else "Demo Company"
            industry = user["industry"] if user else "E-commerce & D2C"
            response = client.chat.completions.create(
                model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
                messages=[
                    {"role":"system","content":(
                        "You are BEAST OS, a practical business operations copilot. "
                        "Give concise, structured, actionable advice. Never claim you executed an external action. "
                        "Separate facts, assumptions, and recommendations. Ask for approval before external actions. "
                        f"Company: {company}. Industry: {industry}.")},
                    {"role":"user","content":prompt}
                ],
                temperature=0.4
            )
            return response.choices[0].message.content
        except Exception as e:
            return "AI provider error: " + str(e) + "\n\nYou can still use the built-in demo planner below."
    return rule_based_response(prompt)

def rule_based_response(prompt):
    p = prompt.lower()
    if any(w in p for w in ["sales", "revenue", "customer", "acquire", "growth"]):
        return ("## BEAST growth plan\n\n"
        "1. **Diagnose:** Review the last 30 days of traffic, leads, conversion rate, average order value and gross margin.\n"
        "2. **Find the bottleneck:** Identify the weakest stage in the funnel before spending more.\n"
        "3. **Prioritise:** Follow up with high-intent leads, improve the top landing page and test one offer.\n"
        "4. **Run a controlled experiment:** Set a budget cap, target metric and 7-day review window.\n"
        "5. **Measure:** Compare incremental gross profit, not just clicks or revenue.\n\n"
        "**Approval required:** Any campaign send, customer contact or budget change must be reviewed by a human. "
        "This is a demo recommendation; no external action has been performed.")
    if any(w in p for w in ["competitor", "market", "opportunity", "research"]):
        return ("## Opportunity research plan\n\n"
        "1. Define the customer segment and geography.\n"
        "2. Collect public competitor pricing, product claims and customer reviews.\n"
        "3. Group recurring complaints into unmet needs.\n"
        "4. Score each opportunity by pain intensity, willingness to pay, competition and ease of testing.\n"
        "5. Interview 5 potential customers before building.\n\n"
        "Connect approved data sources to replace this illustrative plan with evidence.")
    if any(w in p for w in ["cash", "finance", "profit", "cost", "expense"]):
        return ("## Financial control plan\n\n"
        "1. Separate revenue, gross profit and cash collected.\n"
        "2. List recurring costs, upcoming bills and unpaid invoices.\n"
        "3. Identify subscriptions with no recent usage.\n"
        "4. Forecast cash for 4, 8 and 12 weeks using conservative assumptions.\n"
        "5. Require owner approval for payments, transfers and budget changes.\n\n"
        "No bank or accounting data is connected in this demo.")
    return ("## BEAST analysis\n\n"
    "I have converted your request into a practical starting workflow:\n\n"
    "1. Clarify the business outcome and deadline.\n"
    "2. Gather the relevant company data and constraints.\n"
    "3. Identify the highest-impact bottleneck.\n"
    "4. Create a small, measurable experiment.\n"
    "5. Request approval before any external action.\n\n"
    "Add an `OPENAI_API_KEY` environment variable on Render to enable AI-generated responses. "
    "Without it, BEAST uses this built-in demo planner.")

@app.route("/")
def index():
    user = current_user()
    if not user:
        return render_template("landing.html")
    conn = db()
    tasks = conn.execute("SELECT * FROM tasks ORDER BY id DESC LIMIT 8").fetchall()
    approvals = conn.execute("SELECT * FROM approvals ORDER BY id DESC LIMIT 6").fetchall()
    activity = conn.execute("SELECT * FROM activity ORDER BY id DESC LIMIT 7").fetchall()
    counts = {
      "tasks": conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0],
      "running": conn.execute("SELECT COUNT(*) FROM tasks WHERE status='Running'").fetchone()[0],
      "pending": conn.execute("SELECT COUNT(*) FROM approvals WHERE status='Pending'").fetchone()[0],
      "completed": conn.execute("SELECT COUNT(*) FROM tasks WHERE status='Completed'").fetchone()[0]
    }
    conn.close()
    return render_template("dashboard.html", user=user, tasks=tasks, approvals=approvals, activity=activity, counts=counts)

@app.route("/signup", methods=["GET","POST"])
def signup():
    if request.method == "POST":
        email = request.form.get("email","").strip().lower()
        password = request.form.get("password","")
        company = request.form.get("company","My Company").strip() or "My Company"
        industry = request.form.get("industry","E-commerce & D2C")
        if len(password) < 8:
            flash("Password must be at least 8 characters.", "error")
            return render_template("auth.html", mode="signup")
        try:
            conn = db()
            cur = conn.execute("INSERT INTO users(email,password_hash,company,industry,created_at) VALUES(?,?,?,?,?)",
                (email, generate_password_hash(password), company, industry, datetime.datetime.utcnow().isoformat()))
            session["user_id"] = cur.lastrowid
            conn.commit()
            conn.close()
            log("Workspace created for " + company, "success")
            return redirect(url_for("index"))
        except sqlite3.IntegrityError:
            flash("An account with this email already exists.", "error")
    return render_template("auth.html", mode="signup")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email","").strip().lower()
        password = request.form.get("password","")
        conn = db()
        user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        conn.close()
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            return redirect(url_for("index"))
        flash("Invalid email or password.", "error")
    return render_template("auth.html", mode="login")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/api/command", methods=["POST"])
def command():
    user = current_user()
    if not user: return jsonify({"error":"Please log in."}), 401
    prompt = request.json.get("prompt","").strip()
    if not prompt: return jsonify({"error":"Enter a command."}), 400
    answer = get_ai_response(prompt, user)
    log("Command analysed: " + prompt[:100], "info")
    # Convert the command into a proposed task, not an external action.
    conn = db()
    conn.execute("INSERT INTO tasks(title,agent,description,status,priority,created_at) VALUES(?,?,?,?,?,?)",
      ("Review: " + prompt[:72], "BEAST Planner", "AI-generated recommendation is available in Command Center.", "Queued", "Medium", datetime.datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()
    return jsonify({"answer":answer, "mode":"AI" if os.environ.get("OPENAI_API_KEY") else "Demo planner"})

@app.route("/api/task", methods=["POST"])
def add_task():
    if not current_user(): return jsonify({"error":"Please log in."}), 401
    data = request.json
    title = (data.get("title") or "").strip()
    if not title: return jsonify({"error":"Task title is required."}), 400
    conn = db()
    conn.execute("INSERT INTO tasks(title,agent,description,status,priority,created_at) VALUES(?,?,?,?,?,?)",
      (title, data.get("agent","Operations Agent"), data.get("description",""), "Queued", data.get("priority","Medium"), datetime.datetime.utcnow().isoformat()))
    conn.commit(); conn.close()
    log("New task created: " + title, "success")
    return jsonify({"ok":True})

@app.route("/api/task/<int:task_id>/status", methods=["POST"])
def task_status(task_id):
    if not current_user(): return jsonify({"error":"Please log in."}), 401
    status = request.json.get("status")
    if status not in ["Queued","Running","Completed","Blocked"]: return jsonify({"error":"Invalid status."}), 400
    conn = db(); conn.execute("UPDATE tasks SET status=? WHERE id=?", (status,task_id)); conn.commit(); conn.close()
    log(f"Task #{task_id} marked {status}.", "info")
    return jsonify({"ok":True})

@app.route("/api/approval/<int:approval_id>", methods=["POST"])
def approval_action(approval_id):
    if not current_user(): return jsonify({"error":"Please log in."}), 401
    action = request.json.get("action")
    if action not in ["Approved","Rejected"]: return jsonify({"error":"Invalid action."}), 400
    conn = db()
    row = conn.execute("SELECT title FROM approvals WHERE id=?", (approval_id,)).fetchone()
    conn.execute("UPDATE approvals SET status=? WHERE id=?", (action,approval_id))
    conn.commit(); conn.close()
    if row: log(f"Approval {action.lower()}: {row['title']}. Note: approval is recorded only; no external integration is connected.", "warning" if action=="Rejected" else "success")
    return jsonify({"ok":True, "note":"Decision recorded. No external action was executed."})

@app.route("/api/brain", methods=["POST"])
def brain():
    if not current_user(): return jsonify({"error":"Please log in."}), 401
    note = request.json.get("note","").strip()
    if not note: return jsonify({"error":"Note is empty."}), 400
    conn=db(); conn.execute("INSERT INTO brain_notes(note,created_at) VALUES(?,?)",(note,datetime.datetime.utcnow().isoformat())); conn.commit(); conn.close()
    log("Business Brain updated with a new company note.", "success")
    return jsonify({"ok":True})

@app.route("/api/simulator", methods=["POST"])
def simulator():
    if not current_user(): return jsonify({"error":"Please log in."}), 401
    data=request.json
    revenue=max(0,float(data.get("revenue",0)))
    growth=float(data.get("growth",0))/100
    margin=float(data.get("margin",0))/100
    months=max(1,min(36,int(data.get("months",12))))
    projected=revenue*((1+growth)**months)
    profit=projected*margin
    return jsonify({"revenue":round(projected,2),"profit":round(profit,2),"change":round((projected-revenue)/revenue*100,1) if revenue else 0,
                    "disclaimer":"Illustrative scenario based only on your assumptions. Not a forecast or financial advice."})

@app.route("/opportunities")
def opportunities():
    if not current_user(): return redirect(url_for("login"))
    return render_template("module.html", user=current_user(), section="opportunities")

@app.route("/workforce")
def workforce():
    if not current_user(): return redirect(url_for("login"))
    return render_template("module.html", user=current_user(), section="workforce")

@app.route("/brain")
def brain_page():
    if not current_user(): return redirect(url_for("login"))
    conn=db(); notes=conn.execute("SELECT * FROM brain_notes ORDER BY id DESC").fetchall(); conn.close()
    return render_template("module.html", user=current_user(), section="brain", notes=notes)

@app.route("/revenue")
def revenue():
    if not current_user(): return redirect(url_for("login"))
    return render_template("module.html", user=current_user(), section="revenue")

@app.route("/simulator")
def simulator_page():
    if not current_user(): return redirect(url_for("login"))
    return render_template("module.html", user=current_user(), section="simulator")

@app.route("/settings")
def settings():
    if not current_user(): return redirect(url_for("login"))
    return render_template("module.html", user=current_user(), section="settings")

@app.route("/health")
def health():
    return {"status":"ok","product":"BEAST OS","company":"NEXORA"}

init_db()
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
