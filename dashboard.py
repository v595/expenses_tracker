import customtkinter as ctk
import tkinter as tk

# =========================
# APP SETTINGS
# =========================

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

app = ctk.CTk()

app.geometry("1400x800")
app.title("FinancePro SaaS Dashboard")

# =========================
# MAIN BACKGROUND
# =========================

main_bg = "#0f172a"
card_bg = "#111827"
neon_blue = "#38bdf8"
purple = "#8b5cf6"

app.configure(fg_color=main_bg)

# =========================
# SIDEBAR
# =========================

sidebar = ctk.CTkFrame(
    app,
    width=240,
    fg_color="#111827",
    corner_radius=0
)

sidebar.pack(side="left", fill="y")

logo = ctk.CTkLabel(
    sidebar,
    text="💰 FinancePro",
    font=("Poppins", 30, "bold"),
    text_color=neon_blue
)

logo.pack(pady=40)

menu_items = [
    "📊 Dashboard",
    "💳 Expenses",
    "📈 Analytics",
    "📁 Reports",
    "⚙ Settings"
]

for item in menu_items:

    btn = ctk.CTkButton(
        sidebar,
        text=item,
        height=50,
        fg_color="transparent",
        hover_color="#1e293b",
        anchor="w",
        font=("Poppins", 16),
        corner_radius=12
    )

    btn.pack(fill="x", padx=20, pady=8)

# =========================
# MAIN CONTENT
# =========================

main = ctk.CTkFrame(
    app,
    fg_color=main_bg
)

main.pack(
    side="right",
    fill="both",
    expand=True
)

# =========================
# TOPBAR
# =========================

topbar = ctk.CTkFrame(
    main,
    fg_color="transparent"
)

topbar.pack(fill="x", padx=30, pady=20)

title = ctk.CTkLabel(
    topbar,
    text="Dashboard",
    font=("Poppins", 38, "bold")
)

title.pack(side="left")

profile = ctk.CTkLabel(
    topbar,
    text="👤",
    font=("Arial", 34)
)

profile.pack(side="right")

# =========================
# CARDS
# =========================

cards_frame = ctk.CTkFrame(
    main,
    fg_color="transparent"
)

cards_frame.pack(fill="x", padx=30)

def create_card(parent, title, value, icon):

    card = ctk.CTkFrame(
        parent,
        width=320,
        height=180,
        fg_color=card_bg,
        corner_radius=25,
        border_width=1,
        border_color="#1e293b"
    )

    card.pack(side="left", padx=15)

    # ICON

    icon_label = ctk.CTkLabel(
        card,
        text=icon,
        font=("Arial", 45),
        text_color=neon_blue
    )

    icon_label.place(x=220, y=25)

    # TITLE

    title_label = ctk.CTkLabel(
        card,
        text=title,
        font=("Poppins", 18),
        text_color="#94a3b8"
    )

    title_label.place(x=25, y=40)

    # VALUE

    value_label = ctk.CTkLabel(
        card,
        text=value,
        font=("Poppins", 34, "bold")
    )

    value_label.place(x=25, y=85)

    # HOVER EFFECT

    def on_enter(e):
        card.configure(border_color=neon_blue)

    def on_leave(e):
        card.configure(border_color="#1e293b")

    card.bind("<Enter>", on_enter)
    card.bind("<Leave>", on_leave)

create_card(cards_frame, "Total Expense", "₹25,000", "💰")
create_card(cards_frame, "Transactions", "120", "📈")
create_card(cards_frame, "Savings", "₹8,500", "💎")

# =========================
# FORM SECTION
# =========================

form_section = ctk.CTkFrame(
    main,
    fg_color=card_bg,
    corner_radius=25,
    border_width=1,
    border_color="#1e293b"
)

form_section.pack(
    fill="x",
    padx=30,
    pady=30
)

form_title = ctk.CTkLabel(
    form_section,
    text="Add New Expense",
    font=("Poppins", 28, "bold")
)

form_title.pack(anchor="w", padx=25, pady=20)

form_frame = ctk.CTkFrame(
    form_section,
    fg_color="transparent"
)

form_frame.pack(padx=20, pady=20)

# INPUTS

name_entry = ctk.CTkEntry(
    form_frame,
    width=250,
    height=45,
    placeholder_text="Expense Name",
    corner_radius=15
)

name_entry.grid(row=0, column=0, padx=10)

amount_entry = ctk.CTkEntry(
    form_frame,
    width=250,
    height=45,
    placeholder_text="Amount",
    corner_radius=15
)

amount_entry.grid(row=0, column=1, padx=10)

category = ctk.CTkOptionMenu(
    form_frame,
    values=[
        "Food",
        "Travel",
        "Shopping",
        "Bills"
    ],
    width=220,
    height=45,
    corner_radius=15
)

category.grid(row=0, column=2, padx=10)

# BUTTON

add_btn = ctk.CTkButton(
    form_frame,
    text="Add Expense",
    width=180,
    height=45,
    corner_radius=15,
    fg_color=neon_blue,
    hover_color=purple,
    text_color="black",
    font=("Poppins", 15, "bold")
)

add_btn.grid(row=0, column=3, padx=10)

# =========================
# PREMIUM TABLE
# =========================

table_section = ctk.CTkFrame(
    main,
    fg_color=card_bg,
    corner_radius=25,
    border_width=1,
    border_color="#1e293b"
)

table_section.pack(
    fill="both",
    expand=True,
    padx=30,
    pady=10
)

table_title = ctk.CTkLabel(
    table_section,
    text="Recent Expenses",
    font=("Poppins", 28, "bold")
)

table_title.pack(anchor="w", padx=25, pady=20)

# TABLE HEADERS

headers = [
    "ID",
    "Name",
    "Amount",
    "Category",
    "Date"
]

header_frame = ctk.CTkFrame(
    table_section,
    fg_color="transparent"
)

header_frame.pack(fill="x", padx=20)

for i, h in enumerate(headers):

    label = ctk.CTkLabel(
        header_frame,
        text=h,
        font=("Poppins", 15, "bold"),
        text_color=neon_blue,
        width=180
    )

    label.grid(row=0, column=i, padx=5, pady=10)

# SAMPLE ROWS

for row in range(5):

    row_frame = ctk.CTkFrame(
        table_section,
        fg_color="#1e293b",
        corner_radius=15,
        height=55
    )

    row_frame.pack(fill="x", padx=20, pady=8)

    data = [
        str(row + 1),
        "Netflix",
        "₹499",
        "Entertainment",
        "19-05-2026"
    ]

    for i, item in enumerate(data):

        cell = ctk.CTkLabel(
            row_frame,
            text=item,
            width=180,
            font=("Poppins", 14)
        )

        cell.grid(row=0, column=i, padx=5, pady=15)

# =========================
# RUN APP
# =========================

app.mainloop()