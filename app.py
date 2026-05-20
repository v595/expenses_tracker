from flask import Flask, render_template, request, redirect, send_file
import sqlite3
from datetime import datetime
from collections import defaultdict
from io import BytesIO

# PDF EXPORT
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle
)

from reportlab.lib import colors

# =========================
# FLASK APP
# =========================

app = Flask(__name__)

DATABASE = "expenses.db"

# =========================
# DATABASE CONNECTION
# =========================

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# =========================
# CREATE TABLE
# =========================

conn = get_db_connection()
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    amount REAL NOT NULL,
    category TEXT NOT NULL,
    date TEXT NOT NULL
)
""")

conn.commit()
conn.close()

# =========================
# HOME PAGE
# =========================

@app.route("/")
def home():

    conn = get_db_connection()
    cursor = conn.cursor()

    # GET ALL EXPENSES
    cursor.execute("""
    SELECT * FROM expenses
    ORDER BY id DESC
    """)

    expenses = cursor.fetchall()

    # =========================
    # TOTAL EXPENSE
    # =========================

    cursor.execute("""
    SELECT SUM(amount) FROM expenses
    """)

    total_result = cursor.fetchone()[0]
    total = total_result if total_result else 0

    # =========================
    # TOTAL TRANSACTIONS
    # =========================

    cursor.execute("""
    SELECT COUNT(*) FROM expenses
    """)

    transactions = cursor.fetchone()[0]

    # =========================
    # TOTAL CATEGORIES
    # =========================

    cursor.execute("""
    SELECT COUNT(DISTINCT category) FROM expenses
    """)

    categories = cursor.fetchone()[0]

    # =========================
    # CATEGORY SPENDING
    # =========================

    cursor.execute("""
    SELECT category, SUM(amount)
    FROM expenses
    GROUP BY category
    """)

    category_data = cursor.fetchall()

    category_labels = [row[0] for row in category_data]
    category_amounts = [row[1] for row in category_data]

    # =========================
    # MONTHLY GRAPH DATA
    # =========================

    monthly_data = defaultdict(float)

    for expense in expenses:

        amount = expense["amount"]
        date_str = expense["date"]

        try:
            date_obj = datetime.strptime(date_str, "%d-%m-%Y")
            month = date_obj.strftime("%b %Y")
            monthly_data[month] += amount
        except:
            pass

    months = list(monthly_data.keys())
    monthly_totals = list(monthly_data.values())

    # =========================
    # BUDGET SYSTEM
    # =========================

    budget = 20000

    budget_percent = min(
        round((total / budget) * 100, 2),
        100
    )

    conn.close()

    # =========================
    # RENDER PAGE
    # =========================

    return render_template(
        "index.html",
        expenses=expenses,
        total=round(total, 2),
        transactions=transactions,
        categories=categories,
        budget=budget,
        budget_percent=budget_percent,
        category_labels=category_labels,
        category_amounts=category_amounts,
        months=months,
        monthly_totals=monthly_totals
    )

# =========================
# ADD EXPENSE
# =========================

@app.route("/add", methods=["POST"])
def add_expense():

    try:

        name = request.form["name"]
        amount = float(request.form["amount"])
        category = request.form["category"]

        date = datetime.now().strftime("%d-%m-%Y")

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO expenses
        (name, amount, category, date)
        VALUES (?, ?, ?, ?)
        """, (
            name,
            amount,
            category,
            date
        ))

        conn.commit()
        conn.close()

    except Exception as e:
        print("ERROR:", e)

    return redirect("/")

# =========================
# DELETE EXPENSE
# =========================

@app.route("/delete/<int:id>")
def delete_expense(id):

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    DELETE FROM expenses
    WHERE id=?
    """, (id,))

    conn.commit()
    conn.close()

    return redirect("/")

# =========================
# EXPORT PDF
# =========================

@app.route("/export/pdf")
def export_pdf():

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT * FROM expenses
    ORDER BY id DESC
    """)

    expenses = cursor.fetchall()
    conn.close()

    # CREATE PDF IN MEMORY
    buffer = BytesIO()

    doc = SimpleDocTemplate(buffer)

    elements = []

    # TABLE DATA
    data = [[
        "ID",
        "Name",
        "Amount",
        "Category",
        "Date"
    ]]

    # ADD ROWS
    for expense in expenses:

        data.append([
            expense["id"],
            expense["name"],
            f"₹{expense['amount']}",
            expense["category"],
            expense["date"]
        ])

    # CREATE TABLE
    table = Table(data)

    # TABLE STYLE
    style = TableStyle([

        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#38bdf8")),

        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),

        ('GRID', (0, 0), (-1, -1), 1, colors.black),

        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),

        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),

        ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke)

    ])

    table.setStyle(style)

    elements.append(table)

    # BUILD PDF
    doc.build(elements)

    buffer.seek(0)

    # SEND PDF
    return send_file(
        buffer,
        as_attachment=True,
        download_name="expense_report.pdf",
        mimetype="application/pdf"
    )

# =========================
# RUN SERVER
# =========================

if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5001,
        debug=True
    )