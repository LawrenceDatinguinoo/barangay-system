import tkinter as tk
from tkinter import ttk


class DashboardFrame(ttk.Frame):
    """Modern dashboard view fed by database aggregates."""

    def __init__(self, parent, db=None, *args, **kwargs):
        super().__init__(parent, padding=14, *args, **kwargs)
        self.db = db
        self.metric_vars = {
            "residents": tk.StringVar(value="0"),
            "zones": tk.StringVar(value="0"),
            "users": tk.StringVar(value="0"),
        }

        self.header_wrap = ttk.Frame(self, style="Dash.TFrame")
        self.header_wrap.pack(fill="x", pady=(0, 10))

        self.title_lbl = ttk.Label(self.header_wrap, text="Dashboard", style="DashHeader.TLabel")
        self.title_lbl.pack(side="left")

        self.subtitle_lbl = ttk.Label(
            self.header_wrap,
            text="Live overview from your resident database",
            style="DashSub.TLabel",
        )
        self.subtitle_lbl.pack(side="left", padx=(10, 0))

        self.refresh_btn = ttk.Button(
            self.header_wrap, text="Refresh Data", style="Dash.TButton", command=self.refresh_data
        )
        self.refresh_btn.pack(side="right")

        self.cards_wrap = ttk.Frame(self, style="Dash.TFrame")
        self.cards_wrap.pack(fill="x", pady=(0, 10))

        self.card_1 = self._make_card(self.cards_wrap, "Total Residents", self.metric_vars["residents"])
        self.card_2 = self._make_card(self.cards_wrap, "Zones / Purok", self.metric_vars["zones"])
        self.card_3 = self._make_card(self.cards_wrap, "System Users", self.metric_vars["users"])

        self.card_1.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.card_2.pack(side="left", fill="x", expand=True, padx=8)
        self.card_3.pack(side="left", fill="x", expand=True, padx=(8, 0))

        table_wrap = ttk.Frame(self, style="DashCard.TFrame", padding=12)
        table_wrap.pack(fill="both", expand=True)

        ttk.Label(table_wrap, text="System Users", style="DashSection.TLabel").pack(anchor="w", pady=(0, 8))

        cols = ("username", "role", "source")
        self.users_tree = ttk.Treeview(table_wrap, columns=cols, show="headings", height=12, style="Dash.Treeview")
        self.users_tree.heading("username", text="Username")
        self.users_tree.heading("role", text="Role")
        self.users_tree.heading("source", text="Source")
        self.users_tree.column("username", width=240, anchor="w")
        self.users_tree.column("role", width=120, anchor="w")
        self.users_tree.column("source", width=180, anchor="w")
        self.users_tree.pack(side="left", fill="both", expand=True)

        y_scroll = ttk.Scrollbar(table_wrap, orient="vertical", command=self.users_tree.yview)
        y_scroll.pack(side="right", fill="y")
        self.users_tree.configure(yscrollcommand=y_scroll.set)

    def _make_card(self, parent, label, value_var):
        card = ttk.Frame(parent, style="DashCard.TFrame", padding=12)
        ttk.Label(card, text=label, style="DashCardTitle.TLabel").pack(anchor="w")
        ttk.Label(card, textvariable=value_var, style="DashMetric.TLabel").pack(anchor="w", pady=(8, 0))
        return card

    def set_theme(self, theme):
        if theme == "dark":
            bg = "#0B1220"
            panel = "#111C33"
            fg = "#D9E4FF"
            sub = "#8CA0C8"
            accent = "#3B82F6"
            table_bg = "#0E1930"
        else:
            bg = "#EEF2F8"
            panel = "#FFFFFF"
            fg = "#0F172A"
            sub = "#64748B"
            accent = "#2563EB"
            table_bg = "#FFFFFF"

        style = ttk.Style(self)
        style.configure("Dash.TFrame", background=bg)
        style.configure("DashCard.TFrame", background=panel)
        style.configure("DashHeader.TLabel", background=bg, foreground=fg, font=("Segoe UI", 18, "bold"))
        style.configure("DashSub.TLabel", background=bg, foreground=sub, font=("Segoe UI", 10))
        style.configure("DashSection.TLabel", background=panel, foreground=fg, font=("Segoe UI", 12, "bold"))
        style.configure("DashCardTitle.TLabel", background=panel, foreground=sub, font=("Segoe UI", 10))
        style.configure("DashMetric.TLabel", background=panel, foreground=fg, font=("Segoe UI", 24, "bold"))
        style.configure("Dash.TButton", background=accent, foreground="#FFFFFF", font=("Segoe UI", 9, "bold"), padding=(10, 6))
        style.map("Dash.TButton", background=[("active", "#4C97DB")])

        style.configure("Dash.Treeview", background=table_bg, fieldbackground=table_bg, foreground=fg, rowheight=28)
        style.configure("Dash.Treeview.Heading", background=panel, foreground=fg, font=("Segoe UI", 9, "bold"))

        self.configure(style="Dash.TFrame")
        self.header_wrap.configure(style="Dash.TFrame")
        self.cards_wrap.configure(style="Dash.TFrame")

    def refresh_data(self):
        if not self.db:
            return

        stats = self.db.get_dashboard_metrics()
        self.metric_vars["residents"].set(str(stats.get("total_residents", 0)))
        self.metric_vars["zones"].set(str(stats.get("total_zones", 0)))
        self.metric_vars["users"].set(str(stats.get("total_users", 0)))

        for row_id in self.users_tree.get_children():
            self.users_tree.delete(row_id)

        for row in self.db.get_dashboard_users_preview():
            self.users_tree.insert("", "end", values=row)
