from flask import Flask, render_template, request, redirect, url_for, session, send_file, jsonify
import sqlite3
from datetime import datetime
from collections import defaultdict
from io import BytesIO
import hashlib
import os

# PDF
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.jinja_env.globals.update(zip=zip)

DATABASE = "expenses.db"

# =========================
# DATABASE SETUP
# =========================

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        monthly_budget REAL DEFAULT 20000,
        savings_goal REAL DEFAULT 50000,
        created_at TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        amount REAL NOT NULL,
        category TEXT NOT NULL,
        expense_type TEXT NOT NULL DEFAULT 'personal',
        split_with TEXT,
        split_amount REAL,
        date TEXT NOT NULL,
        notes TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS savings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        note TEXT,
        date TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)

    conn.commit()
    conn.close()

init_db()

# =========================
# HELPERS
# =========================

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

def get_user_stats(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE id=?", (user_id,))
    user = cursor.fetchone()

    cursor.execute("SELECT * FROM expenses WHERE user_id=? ORDER BY id DESC", (user_id,))
    expenses = cursor.fetchall()

    cursor.execute("SELECT SUM(amount) FROM expenses WHERE user_id=?", (user_id,))
    total_result = cursor.fetchone()[0]
    total = total_result if total_result else 0

    cursor.execute("SELECT COUNT(*) FROM expenses WHERE user_id=?", (user_id,))
    transactions = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT category) FROM expenses WHERE user_id=?", (user_id,))
    categories = cursor.fetchone()[0]

    cursor.execute("""
        SELECT category, SUM(amount) FROM expenses WHERE user_id=?
        GROUP BY category
    """, (user_id,))
    category_data = cursor.fetchall()

    cursor.execute("""
        SELECT expense_type, SUM(amount) FROM expenses WHERE user_id=?
        GROUP BY expense_type
    """, (user_id,))
    type_data = cursor.fetchall()

    # Monthly data
    monthly_data = defaultdict(float)
    for expense in expenses:
        date_str = expense["date"]
        try:
            date_obj = datetime.strptime(date_str, "%d-%m-%Y")
            month = date_obj.strftime("%b %Y")
            monthly_data[month] += expense["amount"]
        except:
            pass

    # Savings
    cursor.execute("SELECT SUM(amount) FROM savings WHERE user_id=?", (user_id,))
    savings_result = cursor.fetchone()[0]
    total_savings = savings_result if savings_result else 0

    conn.close()

    budget = user["monthly_budget"]
    savings_goal = user["savings_goal"]

    # Current month expenses
    current_month = datetime.now().strftime("%m-%Y")
    month_total = sum(
        e["amount"] for e in expenses
        if e["date"][3:] == current_month
    )

    budget_percent = min(round((month_total / budget) * 100, 1), 100) if budget > 0 else 0
    savings_percent = min(round((total_savings / savings_goal) * 100, 1), 100) if savings_goal > 0 else 0

    category_labels = [row[0] for row in category_data]
    category_amounts = [float(row[1]) for row in category_data]
    type_labels = [row[0] for row in type_data]
    type_amounts = [float(row[1]) for row in type_data]

    months = list(monthly_data.keys())
    monthly_totals = [float(v) for v in monthly_data.values()]

    return {
        "user": user,
        "expenses": expenses,
        "total": round(total, 2),
        "month_total": round(month_total, 2),
        "transactions": transactions,
        "categories": categories,
        "budget": budget,
        "budget_percent": budget_percent,
        "savings_goal": savings_goal,
        "total_savings": round(total_savings, 2),
        "savings_percent": savings_percent,
        "category_labels": category_labels,
        "category_amounts": category_amounts,
        "type_labels": type_labels,
        "type_amounts": type_amounts,
        "months": months,
        "monthly_totals": monthly_totals,
    }

# =========================
# AUTH ROUTES
# =========================

@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        email = request.form["email"].strip()
        password = hash_password(request.form["password"])
        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE email=? AND password=?", (email, password)).fetchone()
        conn.close()
        if user:
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            return redirect(url_for("dashboard"))
        else:
            error = "Invalid email or password. Please try again."
    return render_template("login.html", error=error)

@app.route("/signup", methods=["GET", "POST"])
def signup():
    error = None
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip()
        password = hash_password(request.form["password"])
        budget = float(request.form.get("budget", 20000))
        savings_goal = float(request.form.get("savings_goal", 50000))
        created_at = datetime.now().strftime("%d-%m-%Y")
        try:
            conn = get_db_connection()
            conn.execute(
                "INSERT INTO users (name, email, password, monthly_budget, savings_goal, created_at) VALUES (?,?,?,?,?,?)",
                (name, email, password, budget, savings_goal, created_at)
            )
            conn.commit()
            user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
            conn.close()
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            return redirect(url_for("dashboard"))
        except sqlite3.IntegrityError:
            error = "Email already registered. Please login."
    return render_template("signup.html", error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# =========================
# DASHBOARD
# =========================

@app.route("/dashboard")
@login_required
def dashboard():
    stats = get_user_stats(session["user_id"])
    return render_template("dashboard.html", **stats)

# =========================
# ADD EXPENSE
# =========================

@app.route("/add", methods=["POST"])
@login_required
def add_expense():
    try:
        name = request.form["name"]
        amount = float(request.form["amount"])
        category = request.form["category"]
        expense_type = request.form.get("expense_type", "personal")
        split_with = request.form.get("split_with", "")
        notes = request.form.get("notes", "")
        date = datetime.now().strftime("%d-%m-%Y")

        split_amount = None
        if expense_type == "roommate" and split_with:
            split_amount = round(amount / 2, 2)

        conn = get_db_connection()
        conn.execute(
            "INSERT INTO expenses (user_id, name, amount, category, expense_type, split_with, split_amount, date, notes) VALUES (?,?,?,?,?,?,?,?,?)",
            (session["user_id"], name, amount, category, expense_type, split_with, split_amount, date, notes)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print("ERROR:", e)
    return redirect(url_for("dashboard"))

# =========================
# DELETE EXPENSE
# =========================

@app.route("/delete/<int:id>")
@login_required
def delete_expense(id):
    conn = get_db_connection()
    conn.execute("DELETE FROM expenses WHERE id=? AND user_id=?", (id, session["user_id"]))
    conn.commit()
    conn.close()
    return redirect(url_for("dashboard"))

# =========================
# ADD SAVINGS
# =========================

@app.route("/add_savings", methods=["POST"])
@login_required
def add_savings():
    try:
        amount = float(request.form["savings_amount"])
        note = request.form.get("savings_note", "")
        date = datetime.now().strftime("%d-%m-%Y")
        conn = get_db_connection()
        conn.execute("INSERT INTO savings (user_id, amount, note, date) VALUES (?,?,?,?)",
                     (session["user_id"], amount, note, date))
        conn.commit()
        conn.close()
    except Exception as e:
        print("ERROR:", e)
    return redirect(url_for("dashboard"))

# =========================
# UPDATE BUDGET
# =========================

@app.route("/update_budget", methods=["POST"])
@login_required
def update_budget():
    try:
        budget = float(request.form["budget"])
        savings_goal = float(request.form["savings_goal"])
        conn = get_db_connection()
        conn.execute("UPDATE users SET monthly_budget=?, savings_goal=? WHERE id=?",
                     (budget, savings_goal, session["user_id"]))
        conn.commit()
        conn.close()
    except Exception as e:
        print("ERROR:", e)
    return redirect(url_for("dashboard"))

# =========================
# VOICE ENTRY API
# =========================

@app.route("/api/voice_add", methods=["POST"])
@login_required
def voice_add():
    data = request.json
    try:
        name = data.get("name", "Voice Entry")
        amount = float(data.get("amount", 0))
        category = data.get("category", "Other")
        expense_type = data.get("expense_type", "personal")
        date = datetime.now().strftime("%d-%m-%Y")
        if amount <= 0:
            return jsonify({"success": False, "error": "Invalid amount"})
        conn = get_db_connection()
        conn.execute(
            "INSERT INTO expenses (user_id, name, amount, category, expense_type, split_with, split_amount, date, notes) VALUES (?,?,?,?,?,?,?,?,?)",
            (session["user_id"], name, amount, category, expense_type, "", None, date, "Added via voice")
        )
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": f"Added ₹{amount} for {name}"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# =========================
# EXPORT PDF
# =========================

@app.route("/export/pdf")
@login_required
def export_pdf():
    stats = get_user_stats(session["user_id"])
    expenses = stats["expenses"]
    user = stats["user"]

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=30, leftMargin=30,
        topMargin=30, bottomMargin=30
    )

    styles = getSampleStyleSheet()
    elements = []

    # ---- STYLES ----
    title_style = ParagraphStyle("title", parent=styles["Title"],
        fontSize=22, textColor=colors.HexColor("#1e293b"),
        spaceAfter=4, alignment=TA_CENTER)
    subtitle_style = ParagraphStyle("subtitle", parent=styles["Normal"],
        fontSize=10, textColor=colors.HexColor("#64748b"),
        spaceAfter=2, alignment=TA_CENTER)
    section_style = ParagraphStyle("section", parent=styles["Heading2"],
        fontSize=13, textColor=colors.HexColor("#0f172a"),
        spaceBefore=14, spaceAfter=6,
        borderPad=4)
    normal_style = ParagraphStyle("norm", parent=styles["Normal"],
        fontSize=9, textColor=colors.HexColor("#334155"))
    label_style = ParagraphStyle("label", parent=styles["Normal"],
        fontSize=9, textColor=colors.HexColor("#64748b"))
    value_style = ParagraphStyle("value", parent=styles["Normal"],
        fontSize=11, textColor=colors.HexColor("#0f172a"), fontName="Helvetica-Bold")

    # ---- HEADER ----
    elements.append(Paragraph("💰 FinancePro", title_style))
    elements.append(Paragraph("Expense Report", subtitle_style))
    elements.append(Paragraph(f"Generated for: {user['name']}  |  {datetime.now().strftime('%d %B %Y, %I:%M %p')}", subtitle_style))
    elements.append(Spacer(1, 10))
    elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#3b82f6")))
    elements.append(Spacer(1, 12))

    # ---- SUMMARY CARDS ----
    elements.append(Paragraph("Summary Overview", section_style))

    summary_data = [
        [
            Paragraph("Total Spent", label_style),
            Paragraph("This Month", label_style),
            Paragraph("Monthly Budget", label_style),
            Paragraph("Total Savings", label_style),
        ],
        [
            Paragraph(f"₹{stats['total']:,.2f}", value_style),
            Paragraph(f"₹{stats['month_total']:,.2f}", value_style),
            Paragraph(f"₹{stats['budget']:,.2f}", value_style),
            Paragraph(f"₹{stats['total_savings']:,.2f}", value_style),
        ],
    ]
    summary_table = Table(summary_data, colWidths=[130, 130, 130, 130])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f1f5f9")),
        ('BACKGROUND', (0,1), (-1,1), colors.HexColor("#ffffff")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#e2e8f0")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('ROUNDEDCORNERS', [4,4,4,4]),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 16))

    # Budget progress
    budget_pct = stats["budget_percent"]
    bar_color = colors.HexColor("#22c55e") if budget_pct < 70 else (colors.HexColor("#f59e0b") if budget_pct < 90 else colors.HexColor("#ef4444"))
    elements.append(Paragraph(f"Budget Usage: {budget_pct}%  (₹{stats['month_total']:,.2f} / ₹{stats['budget']:,.2f})", normal_style))
    bar_data = [[""]]
    bar_table = Table(bar_data, colWidths=[520 * budget_pct / 100], rowHeights=[12])
    bar_table.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), bar_color)]))
    elements.append(bar_table)
    elements.append(Spacer(1, 4))
    bg_bar = Table([[""]], colWidths=[520], rowHeights=[12])
    bg_bar.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#e2e8f0"))]))

    elements.append(Spacer(1, 16))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e2e8f0")))

    # ---- CATEGORY BREAKDOWN ----
    elements.append(Paragraph("Spending by Category", section_style))
    if stats["category_labels"]:
        cat_header = [
            Paragraph("Category", ParagraphStyle("h", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=9, textColor=colors.white)),
            Paragraph("Amount (₹)", ParagraphStyle("h", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=9, textColor=colors.white, alignment=TA_RIGHT)),
            Paragraph("% of Total", ParagraphStyle("h", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=9, textColor=colors.white, alignment=TA_RIGHT)),
        ]
        cat_rows = [cat_header]
        cat_colors_list = ["#3b82f6","#8b5cf6","#22c55e","#f59e0b","#ef4444","#06b6d4","#ec4899","#14b8a6"]
        for i, (label, amount) in enumerate(zip(stats["category_labels"], stats["category_amounts"])):
            pct = round(amount / stats["total"] * 100, 1) if stats["total"] > 0 else 0
            cat_rows.append([
                Paragraph(label, normal_style),
                Paragraph(f"₹{amount:,.2f}", ParagraphStyle("r", parent=styles["Normal"], fontSize=9, alignment=TA_RIGHT)),
                Paragraph(f"{pct}%", ParagraphStyle("r", parent=styles["Normal"], fontSize=9, alignment=TA_RIGHT)),
            ])
        cat_table = Table(cat_rows, colWidths=[260, 130, 130])
        cat_style = [
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1e293b")),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
            ('ALIGN', (1,0), (-1,-1), 'RIGHT'),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ]
        for i in range(1, len(cat_rows)):
            if i % 2 == 0:
                cat_style.append(('BACKGROUND', (0,i), (-1,i), colors.HexColor("#f8fafc")))
        cat_table.setStyle(TableStyle(cat_style))
        elements.append(cat_table)

    elements.append(Spacer(1, 16))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e2e8f0")))

    # ---- EXPENSE TABLE ----
    elements.append(Paragraph("All Transactions", section_style))

    type_colors = {
        "personal": colors.HexColor("#3b82f6"),
        "roommate": colors.HexColor("#8b5cf6"),
        "house": colors.HexColor("#22c55e"),
        "shared": colors.HexColor("#f59e0b"),
    }

    header = [
        Paragraph("#", ParagraphStyle("h", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=8, textColor=colors.white)),
        Paragraph("Name", ParagraphStyle("h", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=8, textColor=colors.white)),
        Paragraph("Amount", ParagraphStyle("h", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=8, textColor=colors.white, alignment=TA_RIGHT)),
        Paragraph("Category", ParagraphStyle("h", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=8, textColor=colors.white)),
        Paragraph("Type", ParagraphStyle("h", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=8, textColor=colors.white)),
        Paragraph("Date", ParagraphStyle("h", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=8, textColor=colors.white)),
    ]

    rows = [header]
    small = ParagraphStyle("sm", parent=styles["Normal"], fontSize=8, textColor=colors.HexColor("#334155"))
    small_r = ParagraphStyle("smr", parent=styles["Normal"], fontSize=8, textColor=colors.HexColor("#334155"), alignment=TA_RIGHT)

    for expense in expenses:
        rows.append([
            Paragraph(str(expense["id"]), small),
            Paragraph(expense["name"][:28], small),
            Paragraph(f"₹{expense['amount']:,.2f}", small_r),
            Paragraph(expense["category"], small),
            Paragraph(expense["expense_type"].title(), small),
            Paragraph(expense["date"], small),
        ])

    exp_table = Table(rows, colWidths=[30, 160, 80, 80, 75, 75])
    exp_style = [
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1e293b")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('ALIGN', (2,0), (2,-1), 'RIGHT'),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]
    for i in range(1, len(rows)):
        if i % 2 == 0:
            exp_style.append(('BACKGROUND', (0,i), (-1,i), colors.HexColor("#f8fafc")))
    exp_table.setStyle(TableStyle(exp_style))
    elements.append(exp_table)

    elements.append(Spacer(1, 20))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0")))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph("Generated by FinancePro Expense Tracker", subtitle_style))

    doc.build(elements)
    buffer.seek(0)

    filename = f"FinancePro_Report_{datetime.now().strftime('%d%m%Y')}.pdf"
    return send_file(buffer, as_attachment=True, download_name=filename, mimetype="application/pdf")

# =========================
# RUN
# =========================

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)
