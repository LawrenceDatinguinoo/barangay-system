import os
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date

# optional Pillow for thumbnails
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

# optional DateEntry (calendar)
try:
    from tkcalendar import DateEntry
    DATEPICKER_AVAILABLE = True
except Exception:
    DATEPICKER_AVAILABLE = False

class StreetFrame(ttk.Frame):
    """Street / Purok search-only UI showing residents for a matched barangay street."""
    def __init__(self, parent, db=None, *args, **kwargs):
        super().__init__(parent, padding=14, *args, **kwargs)
        self.db = db

        self.header = ttk.Label(self, text="Street Directory", style='StreetHeader.TLabel')
        self.header.pack(anchor="w")
        self.subheader = ttk.Label(self, text="Find residents by street, purok, or partial address", style='StreetSub.TLabel')
        self.subheader.pack(anchor="w", pady=(0, 10))

        self.top = ttk.Frame(self, style='StreetCard.TFrame', padding=10)
        self.top.pack(fill="x", pady=(0,8))

        ttk.Label(self.top, text="Search Street (exact or partial):", style='Street.TLabel').pack(side="left")
        self.search_var = tk.StringVar()
        # Combobox values are loaded from the streets table when available
        self.search_cb = ttk.Combobox(self.top, textvariable=self.search_var, values=[], width=40, style='Street.TCombobox')
        self.search_cb.state(["!readonly"])  # allow typing; remove this line to force readonly
        self.search_cb.set("") 
        self.search_cb.pack(side="left", padx=6)

        ttk.Button(self.top, text="Search Street", style='Street.TButton', command=self.search_street).pack(side="left", padx=6)
        ttk.Button(self.top, text="Export Results", style='Street.TButton', command=self.export_results).pack(side="left", padx=6)

        # status labels: Residents count and average length of stay
        self.status = ttk.Frame(self, style='Street.TFrame')
        self.status.pack(fill="x", pady=(6,0))
        # use module-level 'tk' already imported at top
        self.count_var = tk.StringVar(value="Residents: 0")
        self.count_lbl = ttk.Label(self.status, textvariable=self.count_var, style='StreetMetric.TLabel')
        self.count_lbl.pack(side="left", padx=(4,20))

        cols = ("ID", "Name", "Date of Stay", "Length Of Stay")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=12, style='Street.Treeview')
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=160, anchor="w")
        self.tree.pack(fill="both", expand=True)

        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        vsb.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=vsb.set)

    def load_street_values(self, values):
        """Populate the combobox with street names from the database."""
        try:
            self.search_cb.configure(values=values or [])
        except Exception:
            pass

    def set_theme(self, theme):
        """Apply a light/dark theme to this StreetFrame."""
        if theme == 'dark':
            bg = '#071337'
            fg = '#D8E2F5'
            card_bg = '#1A2947'
            text_bg = '#122448'
            input_bg = '#364869'
            accent = '#2F6FF3'
        else:
            bg = '#ffffff'
            fg = '#000000'
            card_bg = '#F1F5FF'
            text_bg = '#ffffff'
            input_bg = '#ffffff'
            accent = '#2f85d0'

        try:
            style = ttk.Style(self)
            style.configure('Street.TFrame', background=bg)
            style.configure('Street.TLabel', background=card_bg, foreground=fg)
            style.configure('StreetCard.TFrame', background=card_bg)
            style.configure('StreetHeader.TLabel', background=bg, foreground=fg, font=('Segoe UI', 14, 'bold'))
            style.configure('StreetSub.TLabel', background=bg, foreground='#8EA2C6' if theme == 'dark' else '#4B5F83', font=('Segoe UI', 10))
            style.configure('StreetMetric.TLabel', background=bg, foreground=fg, font=('Segoe UI', 10, 'bold'))
            style.configure('Street.TButton', background=accent, foreground='#ffffff', padding=(10, 6), font=('Segoe UI', 9, 'bold'))
            style.map('Street.TButton', background=[('active', '#3B82F6' if theme == 'dark' else '#4C97DB')])
            style.configure('Street.TCombobox', fieldbackground=input_bg, foreground=fg)
            style.configure('Street.Treeview', background=text_bg, fieldbackground=text_bg, foreground=fg, rowheight=28)
            style.configure('Street.Treeview.Heading', background=card_bg, foreground=fg, font=('Segoe UI', 9, 'bold'))
            self.configure(style='Street.TFrame')
            self.top.configure(style='StreetCard.TFrame')
            self.tree.configure(style='Street.Treeview')
        except Exception:
            try:
                self.configure(background=bg)
            except Exception:
                pass

        try:
            self.tree.configure(background=text_bg, foreground=fg)
        except Exception:
            pass

    def _rows_from_query(self, sql, params=None):
        if not self.db:
            messagebox.showerror("DB Error", "No database connection provided.")
            return []
        ok = self.db.execute_query(sql, params)
        if not ok:
            return []
        return self.db.cursor.fetchall()

    def _duration_years(self, start_date):
        if not start_date:
            return ""
        if isinstance(start_date, str):
            try:
                start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            except Exception:
                return ""
        if not isinstance(start_date, date):
            return ""
        days = (date.today() - start_date).days
        years = days // 365
        return years

    def populate_tree(self, rows):
        """Populate the treeview with rows and compute Years from the length-start date.

        The expected incoming row layout is:
        (barangay_id, full_name, date_of_birth, street_purok, length_of_stay)

        We will display: ID, Name, Length Start, Years
        where Length Start is taken from `length_of_stay` if present, otherwise a sensible fallback.
        """
        # clear existing rows
        for iid in self.tree.get_children():
            self.tree.delete(iid)

        # (no average length maintained anymore)

        for row in rows:
            # safe extraction with fallbacks
            bid = row[0] if len(row) > 0 else ""
            name = row[1] if len(row) > 1 else ""

            # prefer length_of_stay (index 4) as the starting date; fall back to index 2 if needed
            length_start_val = ""
            if len(row) > 4 and row[4] is not None:
                length_start_val = row[4]
            elif len(row) > 2 and row[2] is not None:
                length_start_val = row[2]

            # Format length start for display (handle date objects)
            try:
                if hasattr(length_start_val, "strftime"):
                    length_start = length_start_val.strftime("%Y-%m-%d")
                else:
                    length_start = str(length_start_val)
            except Exception:
                length_start = str(length_start_val)

            # compute years based on the start date
            years = self._duration_years(length_start_val)
            self.tree.insert("", "end", values=(bid, name, length_start, years))

        # update status: resident count only
        try:
            count = len(rows)
            self.count_var.set(f"Residents: {count}")
        except Exception:
            try:
                self.count_var.set("Residents: 0")
            except Exception:
                pass

    def search_street(self):
        term = self.search_var.get().strip()
        if not term:
            messagebox.showinfo("Input", "Choose or type a Purok / street to search.")
            return

        rows = []
        if self.db and hasattr(self.db, "get_street_search_rows"):
            try:
                rows = self.db.get_street_search_rows(term)
            except Exception:
                rows = []

        if not rows:
            messagebox.showinfo("No Street", "No matching street found in barangay streets.")
            # clear tree/list if you have a clear function
            try:
                self.clear_tree()
            except Exception:
                pass
            return

        # populate treeview with rows (implement populate_tree according to your tree columns)
        try:
            self.populate_tree(rows)
        except Exception:
            # fallback: simple clear+insert
            for r in self.tree.get_children():
                self.tree.delete(r)
            for row in rows:
                self.tree.insert("", "end", values=row)

    def export_results(self):
        import csv
        from tkinter import filedialog, messagebox

        # collect rows currently shown in the treeview
        rows = [self.tree.item(i, "values") for i in self.tree.get_children()]
        if not rows:
            messagebox.showinfo("Export", "No data to export.")
            return

        fn = filedialog.asksaveasfilename(defaultextension=".csv",
                                          filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if not fn:
            return

        try:
            with open(fn, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                # write header
                writer.writerow(["ID", "Name", "Date of Stay", "Length Of Stay"])
                # write rows (safe index checks) - Length Start should map to index 4 (length_of_stay), purok to index 3
                for r in rows:
                    writer.writerow([
                        r[0] if len(r) > 0 else "",
                        r[1] if len(r) > 1 else "",
                        r[4] if len(r) > 4 else (r[2] if len(r) > 2 else ""),
                        r[3] if len(r) > 3 else ""
                    ])
            messagebox.showinfo("Export", f"Exported {len(rows)} rows to:\n{fn}")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))