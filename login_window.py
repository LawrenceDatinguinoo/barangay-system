import tkinter as tk
from tkinter import messagebox, ttk
import webbrowser


class LoginWindow(tk.Toplevel):
    """
    Secure and polished login window for Populace Resident Information System.
    Credentials are validated via the login_callback passed from ResidentApp (main.py).
    """

    def __init__(self, master, login_callback):
        super().__init__(master)
        self.master = master
        self.login_callback = login_callback
        self.withdraw()

        self.title("Populace — System Login")
        self.geometry("520x620")
        self.resizable(False, False)
        self.grab_set()
        self.configure(bg="#071337")

        # ── Styles ──────────────────────────────────────────────
        style = ttk.Style(self)
        try:
            style.theme_use('clam')
        except Exception:
            pass

        style.configure('Login.TFrame',    background='#071337')
        style.configure('Card.TFrame',     background='#1A2947')
        style.configure('TLabel',          background='#071337', foreground='#CBD5E1',
                                           font=('Segoe UI', 10))
        style.configure('Card.TLabel',     background='#1A2947', foreground='#CBD5E1',
                                           font=('Segoe UI', 10))
        style.configure('Title.TLabel',    background='#071337', foreground='#F8FAFC',
                   font=('Segoe UI', 18, 'bold'))
        style.configure('Sub.TLabel',      background='#071337', foreground='#7C8CAA',
                   font=('Segoe UI', 11))
        style.configure('FieldLabel.TLabel', background='#1A2947', foreground='#A8B6CC',
                   font=('Segoe UI', 10))
        style.configure('Login.TEntry',    fieldbackground='#364869', foreground='#EAF1FF',
                   borderwidth=0, font=('Segoe UI', 11), padding=10)
        style.map('Login.TEntry',          fieldbackground=[('focus', '#40567C')])
        style.configure('Login.TButton',   font=('Segoe UI', 13, 'bold'), borderwidth=0,
                                           relief='flat', padding=12,
                                           background='#2563EB', foreground='white')
        style.map('Login.TButton',         background=[('active', '#3B82F6')])
        style.configure('Ghost.TButton',   font=('Segoe UI', 10), borderwidth=0,
                                           relief='flat', padding=6,
                           background='#071337', foreground='#4D5F84')
        style.map('Ghost.TButton',         foreground=[('active', '#8EA2C6')],
                           background=[('active', '#071337')])
        style.configure('Show.TButton',    font=('Segoe UI', 9), borderwidth=0,
                                           relief='flat', padding=4,
                           background='#364869', foreground='#A8B6CC')
        style.map('Show.TButton',          background=[('active', '#40567C')])

        # ── Root grid ────────────────────────────────────────────
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ── Outer frame ──────────────────────────────────────────
        outer = ttk.Frame(self, style='Login.TFrame', padding='30 24')
        outer.grid(row=0, column=0, sticky='nsew')
        outer.grid_columnconfigure(0, weight=1)

        # ── Logo / header ────────────────────────────────────────
        logo_frame = ttk.Frame(outer, style='Login.TFrame')
        logo_frame.grid(row=0, column=0, pady=(0, 10))

        badge = tk.Label(logo_frame, text='P', font=('Segoe UI', 18, 'bold'),
             fg='#F8FAFC', bg='#2F6FF3', width=2, relief='flat', padx=8, pady=5)
        badge.pack(side='left', padx=(0, 10))

        hdr = ttk.Frame(logo_frame, style='Login.TFrame')
        hdr.pack(side='left')
        ttk.Label(hdr, text='Populace', style='Title.TLabel').pack(anchor='w')
        ttk.Label(hdr, text='Resident Information System', style='Sub.TLabel').pack(anchor='w')

        # Divider
        tk.Frame(outer, bg='#2B3E63', height=1).grid(row=1, column=0, sticky='ew', pady=16)

        # ── Card frame ───────────────────────────────────────────
        card = ttk.Frame(outer, style='Card.TFrame', padding='24 22')
        card.grid(row=2, column=0, sticky='ew')
        card.grid_columnconfigure(0, weight=1)

        tk.Label(card, text='Sign in to your account',
               font=('Segoe UI', 15, 'bold'),
             bg='#1A2947', fg='#F1F5F9').grid(row=0, column=0, sticky='w', pady=(0, 18))

        # Username field
        ttk.Label(card, text='USERNAME', style='FieldLabel.TLabel').grid(
            row=1, column=0, sticky='w', pady=(0, 4))
        self.username_entry = ttk.Entry(card, style='Login.TEntry', width=34)
        self.username_entry.grid(row=2, column=0, sticky='ew', pady=(0, 14))

        # Password field + show/hide toggle
        ttk.Label(card, text='PASSWORD', style='FieldLabel.TLabel').grid(
            row=3, column=0, sticky='w', pady=(0, 4))

        pw_frame = ttk.Frame(card, style='Card.TFrame')
        pw_frame.grid(row=4, column=0, sticky='ew', pady=(0, 6))
        pw_frame.grid_columnconfigure(0, weight=1)

        self.password_entry = ttk.Entry(pw_frame, style='Login.TEntry', show='*', width=28)
        self.password_entry.grid(row=0, column=0, sticky='ew')

        self._pw_visible = False
        self.show_btn = ttk.Button(pw_frame, text='Show', style='Show.TButton',
                                   command=self._toggle_password)
        self.show_btn.grid(row=0, column=1, padx=(6, 0))

        # Error label (hidden until needed)
        self.error_var = tk.StringVar(value='')
        tk.Label(card, textvariable=self.error_var,
                  fg='#FCA5A5', bg='#1A2947',
                font=('Segoe UI', 9), anchor='w').grid(
            row=5, column=0, sticky='w', pady=(0, 10))

        # Login button
        self.login_btn = ttk.Button(card, text='LOGIN', style='Login.TButton',
                                    command=self.attempt_login)
        self.login_btn.grid(row=6, column=0, sticky='ew', pady=(10, 0))

        # Forgot password
        ttk.Button(outer, text='Forgot password?', style='Ghost.TButton',
                   command=self.forgot_password).grid(row=3, column=0, pady=(16, 0))

        # Footer
        ttk.Label(outer, text='Barangay Management System  •  SDG 11',
                  style='Sub.TLabel').grid(row=4, column=0, pady=(20, 0))

        # ── Bind Enter key ───────────────────────────────────────
        self.bind('<Return>', lambda e: self.attempt_login())

        # ── Center on screen ─────────────────────────────────────
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f'+{(sw - w) // 2}+{(sh - h) // 2}')
        self.deiconify()
        self.username_entry.focus_set()

        try:
            self.protocol('WM_DELETE_WINDOW', self.on_closing)
        except Exception:
            pass

    # ── Helpers ──────────────────────────────────────────────────

    def _toggle_password(self):
        self._pw_visible = not self._pw_visible
        self.password_entry.config(show='' if self._pw_visible else '*')
        self.show_btn.config(text='Hide' if self._pw_visible else 'Show')

    def _set_error(self, msg=''):
        self.error_var.set(msg)

    # ── Actions ──────────────────────────────────────────────────

    def attempt_login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get()

        if not username or not password:
            self._set_error('Please enter both username and password.')
            return

        self._set_error('')
        self.login_btn.config(state='disabled', text='Signing in...')
        self.update()

        try:
            # Delegate to main.py's login_callback (username: admin, password: password)
            success = self.login_callback(username, password)
        except Exception as e:
            success = False
            print(f'[Login] callback error: {e}')

        if success:
            try:
                self.grab_release()
            except Exception:
                pass
            self.destroy()
            try:
                if hasattr(self.master, 'deiconify'):
                    self.master.deiconify()
                self.master.lift()
                self.master.focus_force()
                if hasattr(self.master, 'start_app'):
                    self.master.start_app()
            except Exception as e:
                print(f'[Login] startup error: {e}')
        else:
            self._set_error('Invalid username or password. Please try again.')
            self.password_entry.delete(0, tk.END)
            self.login_btn.config(state='normal', text='LOGIN')
            self.password_entry.focus_set()

    def forgot_password(self):
        url = 'https://forms.gle/5AFm5CbKcap6kf3R6'
        try:
            webbrowser.open_new_tab(url)
        except Exception:
            messagebox.showinfo('Forgot Password',
                                f'Please visit this link to reset your password:\n{url}')

    def on_closing(self):
        if messagebox.askokcancel('Exit', 'Are you sure you want to close the application?'):
            try:
                self.master.destroy()
            except Exception:
                pass
