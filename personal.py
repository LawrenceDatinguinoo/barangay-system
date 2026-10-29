import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, date

# optional Pillow for better image support
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

class PersonalFrame(ttk.Frame):
    """Personal card (photo + vertical fields). Search-only — fills from residents table."""
    def __init__(self, parent, db=None, *args, **kwargs):
        super().__init__(parent, padding=14, *args, **kwargs)
        self.db = db
        self.photo_image = None

        self.header = ttk.Label(self, text="Personal Card", style='PersonalHeader.TLabel')
        self.header.pack(anchor="w")
        self.subheader = ttk.Label(self, text="Search resident details and preview profile summary", style='PersonalSub.TLabel')
        self.subheader.pack(anchor="w", pady=(0, 8))

        self.top = ttk.Frame(self, style='PersonalCard.TFrame', padding=10)
        self.top.pack(fill="x", pady=(0,8))
        ttk.Label(self.top, text="Search Name (partial):", style='Personal.TLabel').pack(side="left")
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(self.top, textvariable=self.search_var, width=40, style='Personal.TEntry')
        self.search_entry.pack(side="left", padx=6)
        ttk.Button(self.top, text="Search", style='Personal.TButton', command=self.search_person).pack(side="left", padx=6)
        ttk.Button(self.top, text="Clear", style='Personal.TButton', command=self.clear_card).pack(side="left", padx=6)
        ttk.Button(self.top, text="Export Card", style='Personal.TButton', command=self.export_card).pack(side="left", padx=6)

        body = ttk.Frame(self, style='Personal.TFrame')
        body.pack(fill="both", expand=True)

        # left: photo + fields vertically
        left = ttk.Frame(body, style='PersonalCard.TFrame', padding=10)
        left.pack(side="left", fill="y", padx=(0,20))

        # right: other info panel so it's visible without scrolling far down
        right = ttk.Frame(body, style='PersonalCard.TFrame', padding=10)
        right.pack(side="left", fill="both", expand=True)

        self.photo_label = ttk.Label(left, text="No Photo", relief="solid", width=20, anchor="center")
        self.photo_label.pack(pady=(0,8))
        self._set_placeholder_photo()

        # fields as requested
        def add_label_entry(parent, label_text):
            ttk.Label(parent, text=label_text, style='Personal.TLabel').pack(anchor="w")
            e = ttk.Entry(parent, width=40, style='Personal.TEntry')
            e.pack(anchor="w", pady=(0,6))
            return e

        self.name_entry = add_label_entry(left, "Name:")
        ttk.Label(left, text="Age:", style='Personal.TLabel').pack(anchor="w")
        self.age_lbl = ttk.Label(left, text="", relief="sunken", width=20)
        self.age_lbl.pack(anchor="w", pady=(0,6))

        self.street_entry = add_label_entry(left, "Street:")
        self.contact_entry = add_label_entry(left, "Contact:")
        self.status_entry = add_label_entry(left, "Status:")

        ttk.Separator(left, orient="horizontal").pack(fill="x", pady=6)

        # Place "Other info" in the right panel so it's immediately visible
        ttk.Label(right, text="Other info:", style='Personal.TLabel').pack(anchor="w")
        self.other_text = tk.Text(right, width=50, height=12)
        self.other_text.pack(fill="both", expand=True, pady=(0,6))

    def set_theme(self, theme):
        """Apply a light/dark theme to this PersonalFrame."""
        if theme == 'dark':
            bg = '#071337'
            fg = '#D8E2F5'
            card_bg = '#1A2947'
            text_bg = '#122448'
            input_text_fg = '#EAF1FF'
            input_bg = '#364869'
            accent = '#2F6FF3'
        else:
            bg = '#ffffff'
            fg = '#000000'
            card_bg = '#F1F5FF'
            text_bg = '#ffffff'
            input_text_fg = fg
            input_bg = text_bg
            accent = '#2f85d0'

        try:
            style = ttk.Style(self)
            style.configure('Personal.TFrame', background=bg)
            style.configure('Personal.TLabel', background=card_bg, foreground=fg)
            style.configure('PersonalCard.TFrame', background=card_bg)
            style.configure('PersonalHeader.TLabel', background=bg, foreground=fg, font=('Segoe UI', 14, 'bold'))
            style.configure('PersonalSub.TLabel', background=bg, foreground='#8EA2C6' if theme == 'dark' else '#4B5F83', font=('Segoe UI', 10))
            style.configure('Personal.TButton', background=accent, foreground='#ffffff', padding=(10, 6), font=('Segoe UI', 9, 'bold'))
            style.map('Personal.TButton', background=[('active', '#3B82F6' if theme == 'dark' else '#4C97DB')])
            
            # Apply dedicated entry style for this panel
            style.configure('Personal.TEntry', fieldbackground=input_bg, background=input_bg, foreground=input_text_fg)

            self.configure(style='Personal.TFrame')
            self.top.configure(style='PersonalCard.TFrame')
        except Exception:
            try:
                self.configure(background=bg)
            except Exception:
                pass

        # update tk.Text background/foreground (uses dark theme colors for text box)
        try:
            self.other_text.configure(background=text_bg, foreground=fg, insertbackground=fg)
        except Exception:
            pass

        # update photo label background if it's a plain widget
        try:
            self.photo_label.configure(background=bg)
        except Exception:
            pass
            
        # update search and form entries (ttk.Entry widgets)
        try:
            for entry in (getattr(self, 'search_entry', None), self.name_entry, self.street_entry, self.contact_entry, self.status_entry):
                if not entry:
                    continue
                try:
                    # 1. ttk widgets: apply TEntry style (already configured above)
                    try:
                        entry.configure(style='Personal.TEntry')
                    except Exception:
                        pass
                        
                    # 2. Force inner entry widgets (tk.Entry components inside ttk.Entry)
                    for child in entry.winfo_children():
                        try:
                            if child.winfo_class().lower() in ('entry', 'tkentry'):
                                # This forces the black text and white background for readability
                                child.configure(background=input_bg, foreground=input_text_fg, insertbackground=input_text_fg)
                        except Exception:
                            pass
                            
                    # 3. Last fallback: try configuring the entry widget itself
                    try:
                        entry.configure(background=input_bg, foreground=input_text_fg)
                    except Exception:
                        pass
                except Exception:
                    pass
        except Exception:
            pass

    def _set_placeholder_photo(self):
        if PIL_AVAILABLE:
            img = Image.new("RGB", (150, 180), (220, 220, 220))
            self.photo_image = ImageTk.PhotoImage(img)
            self.photo_label.config(image=self.photo_image, text="")
        else:
            self.photo_label.config(text="No Photo\n(install Pillow)", image="")

    def _load_photo(self, path):
        try:
            if not os.path.exists(path):
                return False
            if PIL_AVAILABLE:
                img = Image.open(path)
                img.thumbnail((150,180))
                self.photo_image = ImageTk.PhotoImage(img)
                self.photo_label.config(image=self.photo_image, text="")
                return True
            else:
                # limited Tk support
                im = tk.PhotoImage(file=path)
                self.photo_image = im
                self.photo_label.config(image=self.photo_image, text="")
                return True
        except Exception:
            return False

    def _compute_age(self, dob_str):
        if not dob_str:
            return ""
        try:
            dt = datetime.strptime(str(dob_str), "%Y-%m-%d").date()
            return (date.today() - dt).days // 365
        except Exception:
            return ""

    def _rows_from_query(self, sql, params=None):
        if not self.db:
            messagebox.showerror("DB Error", "No database connection provided.")
            return []
        ok = self.db.execute_query(sql, params)
        if not ok:
            return []
        return self.db.cursor.fetchall()

    def search_person(self):
        term = self.search_var.get().strip()
        if not term:
            messagebox.showinfo("Input", "Enter a name to search.")
            return

        rows = []
        if self.db and hasattr(self.db, "get_person_search_rows"):
            try:
                rows = self.db.get_person_search_rows(term)
            except Exception:
                rows = []

        if not rows:
            sql = """
                SELECT barangay_id, full_name, date_of_birth, street_purok, complete_address,
                       contact_info, residency_status, occupation
                FROM residents
                WHERE LOWER(full_name) LIKE LOWER(%s)
                ORDER BY full_name
            """
            rows = self._rows_from_query(sql, (f"%{term}%",))
        if not rows:
            messagebox.showinfo("No results", "No resident found.")
            return

        if len(rows) == 1:
            self._fill_card(rows[0])
            return

        # multiple -> chooser
        chooser = tk.Toplevel(self)
        chooser.title("Select person")
        chooser.geometry("400x300")
        lb = tk.Listbox(chooser)
        lb.pack(fill="both", expand=True, padx=6, pady=6)
        for r in rows:
            lb.insert("end", f"{r[0]} - {r[1]}")

        def on_pick(event=None):
            sel = lb.curselection()
            if not sel:
                return
            idx = sel[0]
            chooser.destroy()
            self._fill_card(rows[idx])

        btn_frame = ttk.Frame(chooser)
        btn_frame.pack(fill="x", padx=6, pady=6)
        ttk.Button(btn_frame, text="Select", command=on_pick).pack(side="left")
        ttk.Button(btn_frame, text="Cancel", command=chooser.destroy).pack(side="right")
        lb.bind("<Double-Button-1>", on_pick)

    def _fill_card(self, row):
        # row indices: 0:id,1:full_name,2:dob,3:street_purok,4:complete_address,5:contact_info,6:residency_status,7:occupation
        self.name_entry.delete(0, tk.END); self.name_entry.insert(0, row[1] or "")
        dob = str(row[2]) if row[2] else ""
        self.age_lbl.config(text=str(self._compute_age(dob)))
        self.street_entry.delete(0, tk.END); self.street_entry.insert(0, row[3] or "")
        self.contact_entry.delete(0, tk.END); self.contact_entry.insert(0, row[5] or "")
        self.status_entry.delete(0, tk.END); self.status_entry.insert(0, row[6] or "")

        other = []
        if row[4]:
            other.append(f"Address: {row[4]}")
        if row[7]:
            other.append(f"Occupation: {row[7]}")
        self.other_text.delete("1.0", tk.END)
        self.other_text.insert("1.0", "\n".join(other))

        # load photo only from ./photos/<id>.* (no DB column assumed)
        loaded = False
        photos_dir = os.path.join(os.path.dirname(__file__), "photos")
        for ext in (".jpg", ".jpeg", ".png", ".gif"):
            p = os.path.join(photos_dir, f"{row[0]}{ext}")
            if os.path.exists(p) and self._load_photo(p):
                loaded = True
                break
        if not loaded:
            self._set_placeholder_photo()

    def clear_card(self):
        for w in (self.name_entry, self.street_entry, self.contact_entry, self.status_entry):
            w.delete(0, tk.END)
        self.age_lbl.config(text="")
        self.other_text.delete("1.0", tk.END)
        self.search_var.set("")
        self._set_placeholder_photo()

    def export_card(self):
        # export current card info (simple XLSX/CSV)
        card = [
            ("Name", self.name_entry.get().strip()),
            ("Age", self.age_lbl.cget("text")),
            ("Street", self.street_entry.get().strip()),
            ("Contact", self.contact_entry.get().strip()),
            ("Status", self.status_entry.get().strip()),
            ("Other", self.other_text.get("1.0", tk.END).strip())
        ]
        path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel","*.xlsx"),("CSV","*.csv")])
        if not path:
            return
        try:
            try:
                # Import openpyxl dynamically to avoid static import errors when the package isn't installed
                import importlib
                openpyxl = importlib.import_module('openpyxl')
                Workbook = getattr(openpyxl, 'Workbook', None)
                if Workbook is None:
                    raise ImportError("openpyxl Workbook not available")
                wb = Workbook()
                ws = wb.active
                ws.append(("Field", "Value"))
                for k, v in card:
                    ws.append((k, v))
                wb.save(path)
                messagebox.showinfo("Export", f"Exported card to {path}")
                return
            except Exception:
                import csv
                with open(path, "w", newline='', encoding="utf-8") as f:
                    w = csv.writer(f)
                    w.writerow(("Field", "Value"))
                    for k, v in card:
                        w.writerow((k, v))
                messagebox.showinfo("Export", f"Exported card to {path}")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))