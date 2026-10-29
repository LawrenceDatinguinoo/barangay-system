import os
import hashlib
import shutil
import time
import tkinter as tk
from tkinter import messagebox, ttk, filedialog

import mysql.connector
import sqlite3
from pathlib import Path

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

try:
    from tkcalendar import DateEntry
    DATEPICKER_AVAILABLE = True
except Exception:
    DATEPICKER_AVAILABLE = False


class DOBWidget(ttk.Frame):
    def __init__(self, master, start_year=None, end_year=None, **kwargs):
        super().__init__(master, **kwargs)
        import datetime
        today = datetime.date.today()
        cy = today.year
        if end_year is None:
            end_year = cy
        if start_year is None:
            start_year = cy - 120

        days = [str(d) for d in range(1, 32)]
        months = [f"{m:02d}" for m in range(1, 13)]
        years = [str(y) for y in range(end_year, start_year - 1, -1)]

        self.day_cb = ttk.Combobox(self, values=days, width=4, state='readonly')
        self.month_cb = ttk.Combobox(self, values=months, width=6, state='readonly')
        self.year_cb = ttk.Combobox(self, values=years, width=6, state='readonly')

        self.day_cb.pack(side='left', padx=(0,3))
        self.month_cb.pack(side='left', padx=(0,3))
        self.year_cb.pack(side='left')

        self.is_dob_widget = True

    def get(self):
        d = self.day_cb.get().strip()
        m = self.month_cb.get().strip()
        y = self.year_cb.get().strip()
        if not (d and m and y):
            return ""
        try:
            di = int(d)
            return f"{y}-{int(m):02d}-{di:02d}"
        except Exception:
            return ""

    def set_date(self, date_str):
        try:
            if not date_str:
                self.day_cb.set(""); self.month_cb.set(""); self.year_cb.set("")
                return
            parts = str(date_str).split("-")
            if len(parts) >= 3:
                y, m, d = parts[0], parts[1], parts[2]
                if ' ' in d:
                    d = d.split(' ')[0]
                self.day_cb.set(str(int(d)))
                self.month_cb.set(f"{int(m):02d}")
                self.year_cb.set(str(int(y)))
        except Exception:
            pass

    def bind(self, sequence=None, func=None, add=None):
        try:
            self.day_cb.bind(sequence, func, add=add)
            self.month_cb.bind(sequence, func, add=add)
            self.year_cb.bind(sequence, func, add=add)
        except Exception:
            pass


try:
    from login_window import LoginWindow
except Exception:
    class LoginWindow:
        def __init__(self, master, callback):
            self.master = master
            self.callback = callback
            self.top = tk.Toplevel(master)
            self.top.title("Login")
            tk.Label(self.top, text="User: admin, Pass: password").pack(pady=10)
            ttk.Button(self.top, text="Login", command=self.login).pack(pady=10)

        def login(self):
            if self.callback("admin", "password"):
                self.top.destroy()
                self.master.start_app()


try:
    from street import StreetFrame
except Exception:
    class StreetFrame(ttk.Frame):
        def __init__(self, master, db=None, **kwargs):
            super().__init__(master, **kwargs)
            ttk.Label(self, text="Street/Purok/Zone Management").pack(padx=20, pady=20)
            self.db = db
        def set_theme(self, theme):
            pass


try:
    from personal import PersonalFrame
except Exception:
    class PersonalFrame(ttk.Frame):
        def __init__(self, master, db=None, **kwargs):
            super().__init__(master, **kwargs)
            ttk.Label(self, text="Personal Management").pack(padx=20, pady=20)
            self.db = db
        def set_theme(self, theme):
            pass


try:
    from dashboard import DashboardFrame
except Exception:
    class DashboardFrame(ttk.Frame):
        def __init__(self, master, db=None, **kwargs):
            super().__init__(master, **kwargs)
            ttk.Label(self, text="Dashboard").pack(padx=20, pady=20)
            self.db = db
        def set_theme(self, theme):
            pass
        def refresh_data(self):
            pass


class ResidentDB:
    """Handles all database connection and CRUD operations."""

    def __init__(self, host="localhost", user="root", password="", database="populace_db"):
        self.config = {
            "host": host,
            "user": user,
            "password": password,
            "database": database,
        }
        self.conn = None
        self.cursor = None
        self.last_error = None
        self.use_sqlite = False
        self.sqlite_path = Path(__file__).parent / "populace_local.db"
        self.allow_sqlite_fallback = True

    def connect(self):
        """Open the main database connection and fall back to sqlite if needed."""
        try:
            self.conn = mysql.connector.connect(**self.config)
            self.cursor = self.conn.cursor(buffered=True)
            self.use_sqlite = False
            self.ensure_schema()
            return
        except Exception as err:
            self.last_error = str(err)
            self.conn = None
            self.cursor = None
            if self.allow_sqlite_fallback:
                try:
                    self.init_sqlite_db()
                    self.conn = sqlite3.connect(str(self.sqlite_path))
                    self.cursor = self.conn.cursor()
                    self.use_sqlite = True
                    try:
                        self.conn.execute("PRAGMA foreign_keys = ON;")
                    except Exception:
                        pass
                    return
                except Exception as sqlite_err:
                    self.last_error = str(sqlite_err)
                    self.conn = None
                    self.cursor = None

    def close(self):
        try:
            if self.cursor:
                self.cursor.close()
            if self.conn:
                self.conn.close()
        except Exception:
            pass
        finally:
            self.conn = None
            self.cursor = None

    def execute_query(self, query, params=None, commit=False):
        """Execute a query and return True on success."""
        if not self.conn:
            self.connect()
        if not self.conn:
            return False

        try:
            if self.use_sqlite:
                sql = query.replace("%s", "?")
                if params is None:
                    self.cursor.execute(sql)
                else:
                    self.cursor.execute(sql, params)
            else:
                if params is None:
                    self.cursor.execute(query)
                else:
                    self.cursor.execute(query, params)

            if commit:
                self.conn.commit()
            return True
        except Exception as err:
            self.last_error = str(err)
            try:
                messagebox.showerror("DB Query Error", f"{err}\nSQL: {query}\nParams: {params}")
            except Exception:
                pass
            return False

    def init_sqlite_db(self):
        """Create a minimal sqlite schema used by the app if it doesn't exist."""
        p = self.sqlite_path
        p.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(p))
        try:
            cur = conn.cursor()
            cur.execute("PRAGMA foreign_keys = ON;")
            cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'staff',
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """)
            cur.execute("""
            CREATE TABLE IF NOT EXISTS streets (
                street_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                zone TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """)
            cur.execute("""
            CREATE TABLE IF NOT EXISTS residents (
                barangay_id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                date_of_birth DATE,
                gender TEXT,
                civil_status TEXT,
                place_of_birth TEXT,
                contact_info TEXT,
                occupation TEXT,
                street_id INTEGER,
                street_purok TEXT,
                complete_address TEXT,
                household_id TEXT,
                residency_status TEXT,
                length_of_stay DATE,
                photo_path TEXT NOT NULL DEFAULT '',
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (street_id) REFERENCES streets (street_id)
            );
            """)
            cur.executemany(
                "INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, ?)",
                [("admin", hashlib.sha256("password".encode("utf-8")).hexdigest(), "admin")],
            )
            cur.executemany(
                "INSERT OR IGNORE INTO streets (name, zone) VALUES (?, ?)",
                [
                    ("Main St", "Zone A"),
                    ("2nd Ave", "Zone A"),
                    ("Purok 1", "Zone B"),
                    ("Purok 2", "Zone B"),
                    ("Purok 3", "Zone C"),
                    ("Purok 4", "Zone C"),
                ],
            )

            # Seed fallback residents only when local table is still empty.
            cur.execute("SELECT COUNT(*) FROM residents")
            existing_count = cur.fetchone()[0]
            if not existing_count:
                cur.executemany(
                    """
                    INSERT INTO residents (
                        full_name, date_of_birth, gender, civil_status,
                        place_of_birth, contact_info, occupation,
                        street_id, street_purok, complete_address, household_id,
                        residency_status, length_of_stay, photo_path
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            "Dela Cruz, Juan M.", "1990-05-15", "Male", "Married",
                            "Batangas City", "09171234567", "Software Developer",
                            3, "Purok 1", "123 Sampaguita St, Purok 1, Barangay Alangilan", "HH-1001",
                            "Registered Voter", "2015-01-10", "",
                        ),
                        (
                            "Pedro Reyes", "1980-05-12", "Male", None,
                            None, "09170000001", None,
                            1, "Main St", None, "HH-001",
                            "Permanent", None, "",
                        ),
                        (
                            "Ana Lopez", "2004-10-19", "Female", None,
                            None, "09170000002", None,
                            6, "Purok 4", None, "HH-002",
                            "Permanent", "2025-11-21", "",
                        ),
                    ],
                )

            conn.commit()
        finally:
            conn.close()

    def ensure_schema(self):
        """Create the tables from the provided database dump if they are missing."""
        if not self.conn or self.use_sqlite:
            return

        statements = [
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id    INT(11)       NOT NULL AUTO_INCREMENT,
                username   VARCHAR(100)  NOT NULL,
                password   VARCHAR(255)  NOT NULL,
                role       ENUM('admin','staff') NOT NULL DEFAULT 'staff',
                created_at TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id),
                UNIQUE KEY uq_username (username)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
            """,
            """
            CREATE TABLE IF NOT EXISTS streets (
                street_id  INT(11)       NOT NULL AUTO_INCREMENT,
                name       VARCHAR(150)  NOT NULL,
                zone       VARCHAR(100)  DEFAULT NULL,
                created_at TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                PRIMARY KEY (street_id),
                UNIQUE KEY uq_street_name (name)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
            """,
            """
            CREATE TABLE IF NOT EXISTS residents (
                barangay_id       INT(11)      NOT NULL AUTO_INCREMENT,
                full_name         VARCHAR(255) NOT NULL,
                date_of_birth     DATE         DEFAULT NULL,
                gender            ENUM('Male','Female','Other') DEFAULT NULL,
                civil_status      ENUM('Single','Married','Widowed','Separated','Annulled') DEFAULT NULL,
                place_of_birth    VARCHAR(255) DEFAULT NULL,
                contact_info      VARCHAR(100) DEFAULT NULL,
                occupation        VARCHAR(100) DEFAULT NULL,
                street_id         INT(11)      DEFAULT NULL,
                street_purok      VARCHAR(100) DEFAULT NULL,
                complete_address  TEXT         DEFAULT NULL,
                household_id      VARCHAR(50)  DEFAULT NULL,
                residency_status  ENUM('Permanent','Renter','Registered Voter','Transient') DEFAULT NULL,
                length_of_stay    DATE         DEFAULT NULL,
                photo_path        VARCHAR(512) NOT NULL DEFAULT '',
                created_at        TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at        TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                PRIMARY KEY (barangay_id),
                INDEX idx_full_name (full_name),
                INDEX idx_street_id (street_id),
                INDEX idx_household (household_id),
                CONSTRAINT fk_resident_street
                    FOREIGN KEY (street_id) REFERENCES streets (street_id)
                    ON DELETE SET NULL ON UPDATE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
            """,
        ]

        try:
            cur = self.conn.cursor()
            for statement in statements:
                cur.execute(statement)
            cur.execute(
                "INSERT IGNORE INTO users (username, password, role) VALUES (%s, %s, %s)",
                ("admin", hashlib.sha256("password".encode("utf-8")).hexdigest(), "admin"),
            )
            cur.executemany(
                "INSERT IGNORE INTO streets (name, zone) VALUES (%s, %s)",
                [
                    ("Main St", "Zone A"),
                    ("2nd Ave", "Zone A"),
                    ("Purok 1", "Zone B"),
                    ("Purok 2", "Zone B"),
                    ("Purok 3", "Zone C"),
                    ("Purok 4", "Zone C"),
                ],
            )
            self.conn.commit()
        except Exception as err:
            print("[DB DEBUG] ensure_schema skipped or failed:", err)

    @staticmethod
    def _hash_password(password):
        return hashlib.sha256(str(password).encode("utf-8")).hexdigest()

    @staticmethod
    def _normalize_password_value(value):
        """Normalize stored password values to avoid hidden CR/LF mismatch issues."""
        text = "" if value is None else str(value)
        return text.replace("\\r", "").replace("\\n", "").strip()

    def authenticate_user(self, username, password):
        """Authenticate against the users table using hashed passwords."""
        username = (username or "").strip()
        password = password or ""
        if not username or not password:
            return None

        sql = "SELECT user_id, username, password, role FROM users WHERE username = %s LIMIT 1"
        if not self.execute_query(sql, (username,)):
            return None

        row = self.cursor.fetchone()
        if not row:
            return None

        stored_password = row[2] if len(row) > 2 else ""
        stored_clean = self._normalize_password_value(stored_password)
        entered_clean = self._normalize_password_value(password)
        entered_hash = self._hash_password(entered_clean)
        if stored_clean in (entered_hash, entered_clean):
            return {
                "user_id": row[0],
                "username": row[1],
                "role": row[3] if len(row) > 3 else "staff",
            }
        return None

    def get_street_names(self):
        """Return street names from the database for comboboxes and lookup views."""
        if self._table_exists("dim_street"):
            sql = "SELECT name FROM dim_street ORDER BY name"
            if self.execute_query(sql):
                rows = self.cursor.fetchall()
                return [row[0] for row in rows if row and row[0]]

        sql = "SELECT name FROM streets ORDER BY name"
        if self.execute_query(sql):
            rows = self.cursor.fetchall()
            return [row[0] for row in rows if row and row[0]]
        return []

    def get_resident_view_rows(self):
        """Return resident rows for the core UI fields only."""
        if self._table_exists("fact_resident_snapshot") and self._table_exists("dim_resident"):
            sql = """
                SELECT
                    dr.resident_id AS resident_id,
                    dr.full_name,
                    dr.date_of_birth,
                    dr.gender,
                    dr.civil_status,
                    dr.place_of_birth,
                    dr.contact_info,
                    COALESCE(ds.name, '') AS street_name,
                    COALESCE(dh.complete_address, '') AS complete_address,
                    f.residency_status,
                    f.length_of_stay_days,
                    f.occupation
                FROM fact_resident_snapshot f
                INNER JOIN dim_resident dr ON f.resident_key = dr.resident_key
                LEFT JOIN dim_street ds ON f.street_key = ds.street_key
                LEFT JOIN dim_household dh ON f.household_key = dh.household_key
                INNER JOIN (
                    SELECT resident_key, MAX(snapshot_id) AS max_snapshot
                    FROM fact_resident_snapshot
                    GROUP BY resident_key
                ) latest
                    ON latest.resident_key = f.resident_key
                   AND latest.max_snapshot = f.snapshot_id
                ORDER BY dr.resident_id DESC
            """
            if self.execute_query(sql):
                return self.cursor.fetchall()

        sql = """
            SELECT barangay_id, full_name, date_of_birth, gender, civil_status,
                   place_of_birth, contact_info, street_purok, complete_address,
                   residency_status, length_of_stay, occupation
            FROM residents
            ORDER BY barangay_id DESC
        """
        if self.execute_query(sql):
            return self.cursor.fetchall()
        return []

    def get_person_search_rows(self, term):
        """Return person-card rows from DW schema first, then legacy residents table."""
        if self._table_exists("fact_resident_snapshot") and self._table_exists("dim_resident"):
            sql = """
                SELECT
                    dr.resident_id,
                    dr.full_name,
                    dr.date_of_birth,
                    COALESCE(ds.name, ''),
                    COALESCE(dh.complete_address, ''),
                    COALESCE(dr.contact_info, ''),
                    COALESCE(f.residency_status, ''),
                    COALESCE(f.occupation, '')
                FROM fact_resident_snapshot f
                INNER JOIN dim_resident dr ON f.resident_key = dr.resident_key
                LEFT JOIN dim_street ds ON f.street_key = ds.street_key
                LEFT JOIN dim_household dh ON f.household_key = dh.household_key
                INNER JOIN (
                    SELECT resident_key, MAX(snapshot_id) AS max_snapshot
                    FROM fact_resident_snapshot
                    GROUP BY resident_key
                ) latest
                    ON latest.resident_key = f.resident_key
                   AND latest.max_snapshot = f.snapshot_id
                WHERE LOWER(dr.full_name) LIKE LOWER(%s)
                ORDER BY dr.full_name
            """
            if self.execute_query(sql, (f"%{term}%",)):
                return self.cursor.fetchall()

        sql = """
            SELECT barangay_id, full_name, date_of_birth, street_purok, complete_address,
                   contact_info, residency_status, occupation
            FROM residents
            WHERE LOWER(full_name) LIKE LOWER(%s)
            ORDER BY full_name
        """
        if self.execute_query(sql, (f"%{term}%",)):
            return self.cursor.fetchall()
        return []

    def get_street_search_rows(self, term):
        """Return street search rows from DW schema first, then legacy residents table."""
        if self._table_exists("fact_resident_snapshot") and self._table_exists("dim_resident"):
            sql = """
                SELECT
                    dr.resident_id,
                    dr.full_name,
                    dr.date_of_birth,
                    COALESCE(ds.name, ''),
                    f.length_of_stay_days
                FROM fact_resident_snapshot f
                INNER JOIN dim_resident dr ON f.resident_key = dr.resident_key
                LEFT JOIN dim_street ds ON f.street_key = ds.street_key
                INNER JOIN (
                    SELECT resident_key, MAX(snapshot_id) AS max_snapshot
                    FROM fact_resident_snapshot
                    GROUP BY resident_key
                ) latest
                    ON latest.resident_key = f.resident_key
                   AND latest.max_snapshot = f.snapshot_id
                WHERE LOWER(dr.full_name) LIKE LOWER(%s)
                   OR LOWER(COALESCE(ds.name, '')) LIKE LOWER(%s)
                ORDER BY dr.full_name
            """
            params = (f"%{term}%", f"%{term}%")
            if self.execute_query(sql, params):
                return self.cursor.fetchall()

        if term.lower().startswith("purok "):
            sql = """
                SELECT barangay_id, full_name, date_of_birth, street_purok, length_of_stay
                FROM residents
                WHERE street_purok = %s
                ORDER BY full_name
            """
            params = (term,)
        else:
            sql = """
                SELECT barangay_id, full_name, date_of_birth, street_purok, length_of_stay
                FROM residents
                WHERE street_purok LIKE %s OR complete_address LIKE %s OR full_name LIKE %s
                ORDER BY full_name
            """
            params = (f"%{term}%", f"%{term}%", f"%{term}%")

        if self.execute_query(sql, params):
            return self.cursor.fetchall()
        return []

    def insert_record(self, data):
        """CREATE: Inserts a new resident record."""
        sql = """
            INSERT INTO residents (
                full_name, date_of_birth, gender, civil_status, place_of_birth,
                contact_info, street_purok, complete_address, residency_status,
                length_of_stay, occupation, photo_path
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        return self.execute_query(sql, data, commit=True)

    def read_all_records(self):
        """READ: Retrieves all records from the residents table."""
        sql = "SELECT * FROM residents"
        if self.execute_query(sql):
            return self.cursor.fetchall()
        return []

    def update_record(self, data, record_id):
        """UPDATE: Updates an existing resident record."""
        data_list = list(data)
        data_list.append(record_id)
        sql = """
            UPDATE residents SET
                full_name=%s, date_of_birth=%s, gender=%s, civil_status=%s,
                place_of_birth=%s, contact_info=%s, street_purok=%s,
                complete_address=%s, residency_status=%s, length_of_stay=%s,
                occupation=%s, photo_path=%s
            WHERE barangay_id = %s
        """
        return self.execute_query(sql, tuple(data_list), commit=True)

    def delete_record(self, record_id):
        """DELETE: Deletes a resident record by ID."""
        sql = "DELETE FROM residents WHERE barangay_id = %s"
        return self.execute_query(sql, (record_id,), commit=True)

    def search_records(self, search_term):
        """SEARCH: Searches records by name or ID."""
        if self._table_exists("fact_resident_snapshot") and self._table_exists("dim_resident"):
            sql = """
                SELECT
                    dr.resident_id AS resident_id,
                    dr.full_name,
                    dr.date_of_birth,
                    dr.gender,
                    dr.civil_status,
                    dr.place_of_birth,
                    dr.contact_info,
                    COALESCE(ds.name, '') AS street_name,
                    COALESCE(dh.complete_address, '') AS complete_address,
                    f.residency_status,
                    f.length_of_stay_days,
                    f.occupation
                FROM fact_resident_snapshot f
                INNER JOIN dim_resident dr ON f.resident_key = dr.resident_key
                LEFT JOIN dim_street ds ON f.street_key = ds.street_key
                LEFT JOIN dim_household dh ON f.household_key = dh.household_key
                INNER JOIN (
                    SELECT resident_key, MAX(snapshot_id) AS max_snapshot
                    FROM fact_resident_snapshot
                    GROUP BY resident_key
                ) latest
                    ON latest.resident_key = f.resident_key
                   AND latest.max_snapshot = f.snapshot_id
                WHERE dr.full_name LIKE %s OR dr.resident_id = %s
                ORDER BY dr.full_name
            """
            search_param = f"%{search_term}%"
            try:
                id_search = int(search_term)
            except ValueError:
                id_search = -1

            if self.execute_query(sql, (search_param, id_search)):
                return self.cursor.fetchall()

        sql = """
            SELECT * FROM residents
            WHERE full_name LIKE %s OR barangay_id = %s
        """
        search_param = f"%{search_term}%"
        try:
            id_search = int(search_term)
        except ValueError:
            id_search = -1

        if self.execute_query(sql, (search_param, id_search)):
            return self.cursor.fetchall()
        return []

    def _table_exists(self, table_name):
        """Return True if a table exists in the active backend."""
        if not self.conn:
            self.connect()
        if not self.conn:
            return False

        try:
            if self.use_sqlite:
                sql = "SELECT name FROM sqlite_master WHERE type='table' AND name=%s"
                if not self.execute_query(sql, (table_name,)):
                    return False
                return self.cursor.fetchone() is not None

            sql = "SELECT 1 FROM information_schema.tables WHERE table_schema=%s AND table_name=%s LIMIT 1"
            if not self.execute_query(sql, (self.config.get("database"), table_name)):
                return False
            return self.cursor.fetchone() is not None
        except Exception:
            return False

    def get_dashboard_metrics(self):
        """Return dashboard counters from star schema when available, else fallback tables."""
        metrics = {
            "total_residents": 0,
            "total_zones": 0,
            "total_users": 0,
        }

        has_fact = self._table_exists("fact_resident_snapshot")
        has_dim_street = self._table_exists("dim_street")
        has_dim_user = self._table_exists("dim_user")

        if has_fact and has_dim_street and has_dim_user:
            try:
                if self.execute_query("SELECT COUNT(DISTINCT resident_key) FROM fact_resident_snapshot"):
                    row = self.cursor.fetchone()
                    metrics["total_residents"] = int(row[0] or 0)

                if self.execute_query("SELECT COUNT(DISTINCT zone) FROM dim_street"):
                    row = self.cursor.fetchone()
                    metrics["total_zones"] = int(row[0] or 0)

                if self.execute_query("SELECT COUNT(*) FROM dim_user"):
                    row = self.cursor.fetchone()
                    metrics["total_users"] = int(row[0] or 0)

                return metrics
            except Exception:
                pass

        try:
            if self.execute_query("SELECT COUNT(*) FROM residents"):
                row = self.cursor.fetchone()
                metrics["total_residents"] = int(row[0] or 0)
        except Exception:
            pass

        try:
            if self.execute_query("SELECT COUNT(DISTINCT zone) FROM streets"):
                row = self.cursor.fetchone()
                metrics["total_zones"] = int(row[0] or 0)
            elif self.execute_query("SELECT COUNT(DISTINCT street_purok) FROM residents"):
                row = self.cursor.fetchone()
                metrics["total_zones"] = int(row[0] or 0)
        except Exception:
            pass

        try:
            if self.execute_query("SELECT COUNT(*) FROM users"):
                row = self.cursor.fetchone()
                metrics["total_users"] = int(row[0] or 0)
        except Exception:
            pass

        return metrics

    def get_dashboard_users_preview(self):
        """Return user rows for dashboard table from DW dim_user or app users table."""
        rows_out = []

        if self._table_exists("dim_user"):
            sql = """
                SELECT username, role, 'DW dim_user' AS source
                FROM dim_user
                ORDER BY username
                LIMIT 20
            """
            if self.execute_query(sql):
                for row in self.cursor.fetchall():
                    rows_out.append((row[0] or "", row[1] or "", row[2]))
                if rows_out:
                    return rows_out

        if self._table_exists("users"):
            sql = """
                SELECT username, role, 'App users' AS source
                FROM users
                ORDER BY username
                LIMIT 20
            """
            if self.execute_query(sql):
                for row in self.cursor.fetchall():
                    rows_out.append((row[0] or "", row[1] or "", row[2]))

        return rows_out


# --- 2. Tkinter GUI Application Class ---
class ResidentApp(tk.Tk):
    def __init__(self):
        super().__init__()
        # Initialize DB handler but do not connect until after login
        self.db = ResidentDB()
        # Logged-in user display
        self.logged_in_var = tk.StringVar(value="")
        self.current_user = None
        self.title("Populace Resident Information System (SDG 11 Aligned)")
        self.geometry("1100x700")

        # UI theme: 'light' or 'dark'
        self.current_theme = 'dark'
        # Start hidden and require login before showing main UI
        self.withdraw()
        self.authenticated = False
        self.authenticate()

    def create_widgets(self):
        # Top navigation (Residents / Street / Personal)
        nav_frame = ttk.Frame(self, padding=6)
        nav_frame.pack(side="top", fill="x")
        # keep a reference so we can lift it if other frames overlap
        self.nav_frame = nav_frame

        # DB status label (right side)
        self.db_status_var = tk.StringVar(value="DB: offline")
        status_lbl = ttk.Label(nav_frame, textvariable=self.db_status_var)
        status_lbl.pack(side="right", padx=6)
        ttk.Button(nav_frame, text="Connect DB", command=self.try_connect_db).pack(side="right", padx=(0,6))
        # Visible current view indicator (helps confirm tab switching)
        self.view_status_var = tk.StringVar(value="View: dashboard")
        view_lbl = ttk.Label(self, textvariable=self.view_status_var, anchor="w")
        view_lbl.pack(side="top", fill="x")

        style = ttk.Style(self)
        style.configure("Nav.TButton", padding=(12, 8), font=('Segoe UI', 10, 'bold'))
        style.configure("ActiveNav.TButton", padding=(12, 8), font=('Segoe UI', 10, 'bold'))
        # Form entry style to avoid bright-blue focus coloring on some platforms
        try:
            style.configure('Form.TEntry', fieldbackground='#ffffff', background='#ffffff', foreground='#000')
            style.map('Form.TEntry', fieldbackground=[('!focus', '#ffffff'), ('focus', '#ffffff')])
        except Exception:
            pass

        try:
            style.configure('Sidebar.TFrame', background='#0B1220')
            style.configure('Sidebar.TButton', padding=(10, 10), font=('Segoe UI', 10, 'bold'))
            style.configure('SidebarActive.TButton', padding=(10, 10), font=('Segoe UI', 10, 'bold'))
        except Exception:
            pass

        self.nav_buttons = {}
        tabs = [("Dashboard", "dashboard"), ("Residents", "residents"), ("Street", "street"), ("Personal", "personal")]
        for label, key in tabs:
            # use a dedicated handler to log clicks and then switch tabs
            btn = ttk.Button(nav_frame, text=label, style="Nav.TButton",
                             command=lambda k=key: self._nav_clicked(k))
            btn.pack(side="left", padx=(4, 0))
            self.nav_buttons[key] = btn

        # Theme toggle button
        ttk.Button(nav_frame, text="Toggle Theme", command=self.toggle_theme).pack(side="right", padx=(4,6))
        # debug: bind mouse clicks on nav frame to detect overlapping widgets
        try:
            nav_frame.bind('<Button-1>', lambda e: print(f"[NAV DEBUG] nav_frame click at {e.x},{e.y}"))
        except Exception:
            pass

        # Container for section-specific content
        self.content_container = ttk.Frame(self)
        # allow the content container to expand so its children layout correctly
        self.content_container.pack(side="top", fill="both", expand=True)

        # --- RESIDENTS FRAME (contains form + controls + results) ---
        residents_frame = ttk.Frame(self.content_container, padding="10")
        # use place so we can stack frames and lift the active one reliably
        residents_frame.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.section_frames = {"residents": residents_frame}

        # Initialize entries dict (fixes earlier AttributeError)
        self.entries = {}
        # We do not show an age label anymore; keep attribute for safety
        self.dob_age_label = None

        # --- Residents form fields (use residents_frame as parent) ---
        # Removed: 'Educational Attainment', 'Vulnerable Sector', 'Household ID'
        fields = [
            "ID (Auto)", "Full Name", "Gender", "Date of Birth (YYYY-MM-DD)",
            "Civil Status", "Place of Birth", "Contact Info", "Street/Purok/Zone",
            "Complete Address", "Residency Status", "Date Of Stay (YYYY-MM-DD)",
            "Occupation", "Photo Path"
        ]
        skip_fields = set()
        row_shift = 0
        for i, field in enumerate(fields):
            # If we've already created this field (e.g. DOB created when Full Name placed), skip it
            if field in skip_fields:
                continue

            # compute row/col and apply any row shift caused by inserting DOB beneath Full Name
            row = (i // 2) + row_shift
            col = (i % 2) * 2

            # If this is the Full Name field, create it and immediately create the DOB beneath it
            if field == "Full Name" and "Date of Birth (YYYY-MM-DD)" in fields:
                # Full Name label + entry
                lbl = ttk.Label(residents_frame, text=f"{field}:")
                lbl.grid(row=row, column=col, sticky="w", padx=5, pady=2)

                try:
                    li = ttk.Label(residents_frame, textvariable=self.logged_in_var, foreground='#1e73be')
                    li.grid(row=row, column=3, sticky='w', padx=(12,0))
                except Exception:
                    pass

                entry = ttk.Entry(residents_frame, width=35, style='Form.TEntry')
                entry.grid(row=row, column=col + 1, sticky="ew", padx=5, pady=2)
                self.entries[field] = entry

                # Create DOB directly beneath Full Name to guarantee visibility
                dob_row = row + 1
                dob_col = col
                try:
                    dob_lbl = ttk.Label(residents_frame, text="Date of Birth (YYYY-MM-DD):")
                    dob_lbl.grid(row=dob_row, column=dob_col, sticky="w", padx=5, pady=2)
                except Exception:
                    pass

                try:
                    dob_widget = DOBWidget(residents_frame)
                    dob_widget.grid(row=dob_row, column=dob_col + 1, sticky="w", padx=5, pady=2)
                    dob_widget.bind('<<ComboboxSelected>>', lambda e, w=dob_widget: self._on_dob_change(w))
                    try:
                        dob_widget.bind('<Return>', lambda e, w=dob_widget: self._on_dob_change(w))
                    except Exception:
                        pass
                    self.entries["Date of Birth (YYYY-MM-DD)"] = dob_widget
                except Exception:
                    pass

                # Age label removed (not needed); keep attribute as None

                # mark DOB as handled so we don't create it again later in the loop
                skip_fields.add("Date of Birth (YYYY-MM-DD)")
                # since we inserted an extra row for DOB, shift subsequent rows down by 1
                row_shift += 1
                continue

            # Normal behavior for other fields
            lbl = ttk.Label(residents_frame, text=f"{field}:")
            lbl.grid(row=row, column=col, sticky="w", padx=5, pady=2)

            # remove any leftover widget(s) previously placed in the target area
            try:
                for old in residents_frame.grid_slaves():
                    try:
                        info = old.grid_info()
                        r = int(info.get('row', -999))
                        c = int(info.get('column', -999))
                        colspan = int(info.get('columnspan', 1)) if info.get('columnspan') is not None else 1
                        target_cols = (col + 1, col + 2)
                        overlaps = any([(c + offset) in target_cols for offset in range(colspan)])
                        if r == row and (c in target_cols or overlaps):
                            try:
                                old.destroy()
                            except Exception:
                                pass
                    except Exception:
                        pass
            except Exception:
                pass

            # Length of Stay: also use DateEntry calendar when available
            if field == "Date Of Stay (YYYY-MM-DD)":
                # Use composite DOBWidget to visually match Date of Birth controls
                try:
                    widget = DOBWidget(residents_frame)
                    widget.grid(row=row, column=col + 1, sticky="w", padx=5, pady=2)
                    widget.bind('<<ComboboxSelected>>', lambda e, w=widget: self._on_dob_change(w))
                    try:
                        widget.bind('<Return>', lambda e, w=widget: self._on_dob_change(w))
                    except Exception:
                        pass
                except Exception:
                    # final fallback to plain Entry
                    widget = ttk.Entry(residents_frame, width=35)
                    widget.grid(row=row, column=col + 1, sticky="ew", padx=5, pady=2)
                self.entries[field] = widget

            # special widget for Street/Purok/Zone: combobox with Purok 1..10 (readonly so user clicks)
            elif field == "Street/Purok/Zone":
                values = [f"Purok {n}" for n in range(1, 11)]
                cb = ttk.Combobox(residents_frame, values=values, width=33, state="readonly")
                cb.set("")  # start empty
                cb.grid(row=row, column=col + 1, sticky="w", padx=5, pady=2)
                self.entries[field] = cb

            elif field == "Photo Path":
                e = ttk.Entry(residents_frame, width=30)
                e.grid(row=row, column=col + 1, sticky="w", padx=(5,2), pady=2)
                self.entries[field] = e
                btn = ttk.Button(residents_frame, text="Browse Photo", command=self.browse_photo)
                btn.grid(row=row, column=col + 2, sticky="w", padx=(2,5))
                self.photo_thumb = ttk.Label(residents_frame, text="", relief="sunken", width=20)
                self.photo_thumb.grid(row=row+1, column=col+1, sticky="w", padx=5, pady=(0,6))

            elif field == "Gender":
                var = tk.StringVar(value="")
                frm = tk.Frame(residents_frame, bg="#ffffff", bd=0, relief='flat')
                rb_m = ttk.Radiobutton(frm, text="Male", variable=var, value="Male")
                rb_f = ttk.Radiobutton(frm, text="Female", variable=var, value="Female")
                rb_o = ttk.Radiobutton(frm, text="Other", variable=var, value="Other")
                rb_m.pack(side='left', padx=(0,6))
                rb_f.pack(side='left', padx=(0,6))
                rb_o.pack(side='left')
                frm.grid(row=row, column=col + 1, sticky="w", padx=5, pady=2)
                self.entries[field] = var
                try:
                    self._gender_frame = frm
                    self._gender_grid = (row, col + 1)
                except Exception:
                    pass
            else:
                entry = ttk.Entry(residents_frame, width=35, style='Form.TEntry')
                entry.grid(row=row, column=col + 1, sticky="ew", padx=5, pady=2)
                self.entries[field] = entry

        # Disable ID field since it's auto-generated
        # Targeted removal: eliminate an extraneous widget that can appear
        # directly below the ID field (row=1, column=1). Call update_idletasks
        # so size information is available, then remove any untracked widget
        # at that grid cell while keeping known good widgets.
        try:
            try:
                residents_frame.update_idletasks()
            except Exception:
                pass
            tracked = set(self.entries.values())
            # Build a small whitelist of widgets we should NOT remove even if
            # they appear at the same grid cell (labels/frames we created intentionally).
            whitelist_classes = ('frame', 'labelframe', 'tlabel', 'label')
            for child in list(residents_frame.winfo_children()):
                try:
                    gi = child.grid_info()
                    r = int(gi.get('row', -999))
                    c = int(gi.get('column', -999))
                    # target the problematic cell directly
                    if r == 1 and c == 1 and child not in tracked:
                        cls = child.winfo_class().lower()
                        # If it's a label or frame we created intentionally, keep it
                        if cls in whitelist_classes:
                            continue
                        # Also keep our DOB composite or its internal children
                        if getattr(child, 'is_dob_widget', False):
                            continue
                        # If it's the age label or the photo thumbnail, keep it
                        if hasattr(self, 'dob_age_label') and child is getattr(self, 'dob_age_label'):
                            continue
                        if hasattr(self, 'photo_thumb') and child is getattr(self, 'photo_thumb'):
                            continue
                        # Aggressive removal: destroy any entry-like widget (likely the stray small box)
                        try:
                            if cls in ('entry', 'tentry', 'tkentry'):
                                child.destroy()
                                continue
                        except Exception:
                            pass
                        # Fallback: use requested width heuristic to remove narrow stray widgets
                        try:
                            req_w = None
                            try:
                                req_w = child.winfo_reqwidth()
                            except Exception:
                                req_w = None
                            if req_w is None or req_w < 140:
                                try:
                                    child.destroy()
                                except Exception:
                                    pass
                        except Exception:
                            pass
                except Exception:
                    pass
        except Exception:
            pass

        if "ID (Auto)" in self.entries:
            try:
                self.entries["ID (Auto)"].config(state='disabled')
            except Exception:
                pass

        # Ensure gender frame remains correctly placed (re-grid to override any overlay)
        try:
            if hasattr(self, '_gender_frame') and hasattr(self, '_gender_grid'):
                try:
                    g_row, g_col = self._gender_grid
                    self._gender_frame.grid_forget()
                    self._gender_frame.grid(row=g_row, column=g_col, sticky="w", padx=5, pady=2)
                except Exception:
                    pass
        except Exception:
            pass

        # Ensure all form entries do not show native blue focus rectangle
        try:
            for name, w in self.entries.items():
                try:
                    # Some ttk widgets contain an internal tk.Entry child
                    for child in w.winfo_children():
                        try:
                            if child.winfo_class().lower() in ('entry', 'tkentry'):
                                child.configure(highlightthickness=0, bd=1, relief='solid', background='#ffffff', selectbackground='#ffffff', selectforeground='#000000', insertbackground='#000000')
                        except Exception:
                            pass
                except Exception:
                    # If widget has no winfo_children or is a simple Entry, try configure directly
                    try:
                        if hasattr(w, 'configure'):
                            w.configure(highlightthickness=0, bd=1, relief='solid', background='#ffffff', selectbackground='#ffffff', selectforeground='#000000', insertbackground='#000000')
                    except Exception:
                        pass
        except Exception:
            pass

        # Ensure Date of Birth appears directly under Full Name (visible spot)
        try:
            if "Full Name" in fields and "Date of Birth (YYYY-MM-DD)" in self.entries:
                full_idx = fields.index("Full Name")
                full_row = full_idx // 2
                full_col = (full_idx % 2) * 2
                target_row = full_row + 1
                target_col = full_col

                # remove any existing DOB label placed elsewhere
                for child in list(residents_frame.winfo_children()):
                    try:
                        gi = child.grid_info()
                        r = int(gi.get('row', -999))
                        c = int(gi.get('column', -999))
                        if r == target_row and c == target_col:
                            # if label already exists in target spot, keep it
                            continue
                        # remove previous DOB label if it matches the text
                        if r != target_row and isinstance(child, ttk.Label):
                            try:
                                txt = child.cget('text')
                                if isinstance(txt, str) and txt.strip().lower().startswith('date of birth'):
                                    child.destroy()
                            except Exception:
                                pass
                    except Exception:
                        pass

                # Place a clear DOB label at the target position
                try:
                    dob_lbl = ttk.Label(residents_frame, text="Date of Birth (YYYY-MM-DD):")
                    dob_lbl.grid(row=target_row, column=target_col, sticky="w", padx=5, pady=2)
                except Exception:
                    pass

                # Move the existing DOB widget (composite) into the target column+1
                try:
                    dob_widget = self.entries.get("Date of Birth (YYYY-MM-DD)")
                    if dob_widget is not None:
                        try:
                            dob_widget.grid_forget()
                        except Exception:
                            pass
                        try:
                            dob_widget.grid(row=target_row, column=target_col + 1, sticky="w", padx=5, pady=2)
                        except Exception:
                            pass
                except Exception:
                    pass

                # Reposition the age label to the right of the DOB widget
                try:
                    if hasattr(self, 'dob_age_label') and self.dob_age_label:
                        try:
                            self.dob_age_label.grid_forget()
                        except Exception:
                            pass
                        try:
                            self.dob_age_label.grid(row=target_row, column=target_col + 2, sticky="w", padx=5)
                        except Exception:
                            pass
                except Exception:
                    pass
        except Exception:
            pass

        # Ensure DOB age label is placed in the correct row (robust placement)
        try:
            dob_index = fields.index("Date of Birth (YYYY-MM-DD)")
            dob_row = dob_index // 2
            dob_col = (dob_index % 2) * 2
            if hasattr(self, 'dob_age_label') and self.dob_age_label:
                try:
                    age_col = 2 if dob_col == 0 else 1
                    self.dob_age_label.grid(row=dob_row, column=age_col, sticky="w", padx=5)
                except Exception:
                    pass
        except Exception:
            pass

        # Remove any widgets overlapping the Gender area (defensive cleanup)
        try:
            if hasattr(self, '_gender_grid') and hasattr(self, '_gender_frame'):
                g_row, g_col = self._gender_grid
                target_cols = (g_col, g_col + 1)
                for child in list(residents_frame.winfo_children()):
                    try:
                        gi = child.grid_info()
                        r = int(gi.get('row', -999))
                        c = int(gi.get('column', -999))
                        colspan = int(gi.get('columnspan', 1)) if gi.get('columnspan') is not None else 1
                        # skip our gender frame itself or its internal widgets
                        if child is self._gender_frame or child in self._gender_frame.winfo_children():
                            continue
                        # if widget shares the same row and overlaps target columns, remove it
                        if r == g_row:
                            cols_occupied = [c + i for i in range(colspan)]
                            if any(tc in target_cols for tc in cols_occupied):
                                try:
                                    child.destroy()
                                except Exception:
                                    pass
                    except Exception:
                        pass
        except Exception:
            pass

        # --- Buttons + Search (now inside residents_frame) ---
        controls_frame = ttk.Frame(residents_frame, padding="8")
        controls_frame.grid(row=(len(fields)//2)+2, column=0, columnspan=4, sticky="ew", pady=(10,0))

        ttk.Button(controls_frame, text="Add Record (C)", command=self.add_record).pack(side="left", padx=5)
        ttk.Button(controls_frame, text="Update Record (U)", command=self.update_selected_record).pack(side="left", padx=5)
        ttk.Button(controls_frame, text="Delete Record (D)", command=self.delete_selected_record).pack(side="left", padx=5)
        ttk.Button(controls_frame, text="Clear Form", command=self.clear_entries).pack(side="left", padx=5)
        # keep Show All next to CRUD per request
        ttk.Separator(controls_frame, orient='vertical').pack(side="left", fill='y', padx=10)
        ttk.Button(controls_frame, text="Show All (R)", command=self.display_records).pack(side="left", padx=5)

        # small gap then DB actions (manual connect)

        # --- Results Tree (inside residents_frame) ---
        # create a frame that allows the treeview to resize cleanly
        result_frame = ttk.Frame(residents_frame, padding="6")
        result_frame.grid(row=(len(fields)//2)+3, column=0, columnspan=4, sticky="nsew", pady=(8,0))

        # give the residents_frame and result_frame resizable rows/cols
        residents_frame.rowconfigure((len(fields)//2)+3, weight=1)
        residents_frame.columnconfigure(0, weight=1)
        residents_frame.columnconfigure(1, weight=1)
        residents_frame.columnconfigure(2, weight=1)
        residents_frame.columnconfigure(3, weight=1)

        result_frame.rowconfigure(0, weight=1)
        result_frame.columnconfigure(0, weight=1)

        # Show only the core resident fields used by the main form
        cols = (
            "ID", "Full Name", "Date of Birth", "Gender", "Civil Status",
            "Place of Birth", "Contact", "Street", "Address",
            "Residency", "Date of Stay", "Occupation"
        )
        self.tree = ttk.Treeview(result_frame, columns=cols, show="headings")
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=140, anchor="w")

        # place tree with grid so it expands properly; no extra small scrollbar
        self.tree.grid(row=0, column=0, sticky="nsew")
        # bind selection to fill form
        self.tree.bind("<<TreeviewSelect>>", self.select_record)

        # ensure nav_frame is above content so buttons are clickable
        try:
            if hasattr(self, 'nav_frame'):
                self.nav_frame.lift()
        except Exception:
            pass

        # Optional: a proper scrollbar attached to the tree (hidden unless needed)
        vsb = ttk.Scrollbar(result_frame, orient="vertical", command=self.tree.yview)
        vsb.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=vsb.set)

        # Horizontal scrollbar for wide tables
        try:
            hsb = ttk.Scrollbar(result_frame, orient="horizontal", command=self.tree.xview)
            hsb.grid(row=1, column=0, columnspan=2, sticky="ew")
            self.tree.configure(xscrollcommand=hsb.set)
        except Exception:
            pass

        # --- Dashboard frame (new home tab) ---
        dashboard_f = DashboardFrame(self.content_container, db=self.db)
        self.section_frames["dashboard"] = dashboard_f

        # --- Create Street and Personal frames (they remain separate and will be lifted when active) ---
        street_f = StreetFrame(self.content_container, db=self.db)
        personal_f = PersonalFrame(self.content_container, db=self.db)
        # Do NOT pre-place street/personal frames here — place them only when activated
        # This avoids them overlapping the Residents frame on startup.
        # Temporary visual headers for debugging visibility
        try:
            import tkinter as _tk
            hdr_s = _tk.Label(street_f, text="--- STREET VIEW ---", bg="#cfeef5", fg="#000")
            hdr_s.pack(side="top", fill="x")
            hdr_p = _tk.Label(personal_f, text="--- PERSONAL VIEW ---", bg="#e6f7df", fg="#000")
            hdr_p.pack(side="top", fill="x")
        except Exception:
            pass
        self.section_frames["street"] = street_f
        self.section_frames["personal"] = personal_f

        # Load lookup values from the seeded database into the UI
        try:
            street_values = self.db.get_street_names()
            if hasattr(street_f, "load_street_values"):
                street_f.load_street_values(street_values)
        except Exception:
            pass

        # Force-hide any non-residents children in the content container to avoid accidental overlap
        try:
            for child in list(self.content_container.winfo_children()):
                try:
                    if child is not residents_frame:
                        try:
                            child.place_forget()
                        except Exception:
                            pass
                        try:
                            child.pack_forget()
                        except Exception:
                            pass
                except Exception:
                    pass
        except Exception:
            pass

        # Ensure residents_frame is above others and visible
        try:
            residents_frame.lift()
        except Exception:
            pass

        # Start with Residents tab active (lift it above others)
        self.active_tab = "residents"
        try:
            residents_frame.lift()
        except Exception:
            pass
        self.set_active_tab("dashboard")
        # apply initial theme
        try:
            self.apply_theme(self.current_theme)
        except Exception:
            pass

    def clear_entries(self):
        """Clears all input fields in the form."""
        for field, entry in self.entries.items():
            if field != "ID (Auto)":
                try:
                    # composite DOB widget uses set_date instead of delete
                    if hasattr(entry, 'set_date'):
                        entry.set_date("")
                    # tk.Variable (e.g. StringVar for Gender) should be .set("")
                    elif isinstance(entry, tk.Variable):
                        try:
                            entry.set("")
                        except Exception:
                            pass
                    else:
                        entry.delete(0, tk.END)
                except Exception:
                    try:
                        entry.delete(0, tk.END)
                    except Exception:
                        pass
            else:
                # Allow clearing of the disabled ID field, then disable again
                try:
                    entry.config(state='normal')
                except Exception:
                    pass
                try:
                    entry.delete(0, tk.END)
                except Exception:
                    pass
                try:
                    entry.config(state='disabled')
                except Exception:
                    pass
        if hasattr(self, 'search_var'):
            try:
                self.search_var.set("") # Clear search field
            except Exception:
                pass

    def get_form_data(self):
        """Collects data from the input entries."""
        data = [
            self.entries["Full Name"].get(), self.entries["Date of Birth (YYYY-MM-DD)"].get(),
            self.entries["Gender"].get(), self.entries["Civil Status"].get(), 
            self.entries["Place of Birth"].get(), self.entries["Contact Info"].get(), 
            self.entries["Street/Purok/Zone"].get(), self.entries["Complete Address"].get(),
            self.entries["Residency Status"].get(), self.entries["Date Of Stay (YYYY-MM-DD)"].get(),
            self.entries["Occupation"].get(), self.entries["Photo Path"].get()
        ]
        # Basic mandatory field check
        if not all(data[:2]): # Check Full Name and DoB
            messagebox.showerror("Input Error", "Full Name and Date of Birth are mandatory fields.")
            return None
            
        return tuple(data)

    # --- CRUD Functions ---
    
    def add_record(self):
        """Handles the CREATE operation with photo handling."""
        data = self.get_form_data()
        if not data:
            return
        # photo_path is last element in tuple
        photo_path = data[-1] if len(data) >= 12 else ""
        if self.db.insert_record(data):
            # lastrowid should be available on the cursor after insert
            new_id = getattr(self.db.cursor, "lastrowid", None)
            # if we have a temporary/timestamped photo file, move it to <id>.<ext>
            if new_id and photo_path:
                # if photo already in photos/<id>.* skip; otherwise move if filename contains timestamp underscore
                basename = os.path.basename(photo_path)
                if "_" in basename or not basename.startswith(str(new_id)):
                    try:
                        self._save_photo_for_id(photo_path, new_id)
                    except Exception:
                        pass
            messagebox.showinfo("Success", "New Resident record added successfully.")
            self.clear_entries()
            self.display_records()

    def display_records(self, records=None):
        """Handles the READ operation (Display All/Search Results)."""
        # Clear previous records
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        # Fetch records
        records_to_display = records if records is not None else self.db.get_resident_view_rows()
        
        # Insert new records
        for record in records_to_display:
            # Convert date objects to string for display if necessary
            display_record = [str(col) if col is not None else "" for col in record]
            self.tree.insert('', tk.END, values=display_record)

    def _on_dob_change(self, widget):
        """Update the DOB age label when the DateEntry changes."""
        try:
            dob_val = widget.get()
            age = self._compute_age_from_str(dob_val)
            if hasattr(self, "dob_age_label"):
                self.dob_age_label.config(text=str(age))
        except Exception:
            pass

    def _compute_age_from_str(self, dob_str):
        from datetime import datetime, date
        if not dob_str:
            return ""
        try:
            dt = datetime.strptime(str(dob_str), "%Y-%m-%d").date()
            return (date.today() - dt).days // 365
        except Exception:
            return ""

    def select_record(self, event=None):
        """Fill form when a record is selected in the tree (existing function)."""
        sel = self.tree.selection()
        if not sel:
            return
        item = self.tree.item(sel[0], "values")
        rec_id = item[0]
        row = None
        if self.db._table_exists("residents"):
            sql = "SELECT barangay_id, full_name, date_of_birth, gender, street_purok, complete_address, contact_info, residency_status, occupation, COALESCE(photo_path, '') FROM residents WHERE barangay_id = %s LIMIT 1"
            if self.db.execute_query(sql, (rec_id,)):
                row = self.db.cursor.fetchone()

        # Fallback for DW-backed rows already shown in the grid
        if not row and item:
            row = (
                item[0] if len(item) > 0 else "",
                item[1] if len(item) > 1 else "",
                item[2] if len(item) > 2 else "",
                item[3] if len(item) > 3 else "",
                item[7] if len(item) > 7 else "",
                item[8] if len(item) > 8 else "",
                item[6] if len(item) > 6 else "",
                item[9] if len(item) > 9 else "",
                item[11] if len(item) > 11 else "",
                "",
            )

        if row:
            # set ID (Auto) field so update_selected_record can read it
            try:
                if "ID (Auto)" in self.entries:
                    self.entries["ID (Auto)"].config(state='normal')
                    self.entries["ID (Auto)"].delete(0, tk.END)
                    self.entries["ID (Auto)"].insert(0, str(row[0]))
                    self.entries["ID (Auto)"].config(state='disabled')
            except Exception:
                pass

            # populate form fields (existing code)
            self.entries.get("Full Name").delete(0, tk.END); self.entries.get("Full Name").insert(0, row[1] or "")
            dob_widget = self.entries.get("Date of Birth (YYYY-MM-DD)")
            dob_val = str(row[2]) if row[2] else ""
            if dob_widget:
                try:
                    # support DateEntry, custom DOBWidget, or plain Entry
                    if hasattr(dob_widget, 'set_date'):
                        dob_widget.set_date(dob_val or "")
                    else:
                        # fallback for plain Entry
                        try:
                            dob_widget.delete(0, tk.END); dob_widget.insert(0, dob_val)
                        except Exception:
                            pass
                except Exception:
                    pass
                try:
                    # ensure age label updates after programmatic set
                    self._on_dob_change(dob_widget)
                except Exception:
                    pass
            # populate gender (combobox)
            g_widget = self.entries.get("Gender")
            if g_widget:
                try:
                    # Combobox uses .set()
                    g_widget.set(row[3] or "")
                except Exception:
                    try:
                        g_widget.delete(0, tk.END); g_widget.insert(0, row[3] or "")
                    except Exception:
                        pass

            sp_widget = self.entries.get("Street/Purok/Zone")
            if sp_widget:
                sp_widget.set(row[4] or "")
            if self.entries.get("Contact Info"):
                self.entries.get("Contact Info").delete(0, tk.END); self.entries.get("Contact Info").insert(0, row[6] or "")
            if self.entries.get("Residency Status"):
                self.entries.get("Residency Status").delete(0, tk.END); self.entries.get("Residency Status").insert(0, row[7] or "")
            # ...photo handling etc...

    def update_selected_record(self):
        """Handles the UPDATE operation and photo rename if needed."""
        try:
            record_id = int(self.entries["ID (Auto)"].get())
        except Exception:
            messagebox.showerror("Error", "Please select a record from the list to update.")
            return

        data = self.get_form_data()
        if not data:
            return

        # If photo field has a timestamped file, move and update DB after update_record
        photo_path = data[-1] if len(data) >= 12 else ""
        if self.db.update_record(data, record_id):
            # attempt to rename/move photo to <id>.<ext> if needed
            if photo_path and os.path.exists(photo_path):
                basename = os.path.basename(photo_path)
                if "_" in basename or not basename.startswith(str(record_id)):
                    try:
                        self._save_photo_for_id(photo_path, record_id)
                    except Exception:
                        pass
            messagebox.showinfo("Success", f"Record ID {record_id} updated successfully.")
            self.clear_entries()
            self.display_records()

    def delete_selected_record(self):
        """Handles the DELETE operation."""
        try:
            # Get the ID from the disabled ID field
            record_id = int(self.entries["ID (Auto)"].get())
        except ValueError:
            messagebox.showerror("Error", "Please select a record from the list to delete.")
            return

        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete Record ID: {record_id}?"):
            if self.db.delete_record(record_id):
                messagebox.showinfo("Success", f"Record ID {record_id} deleted successfully.")
                self.clear_entries()
                self.display_records()
            
    def search_records(self):
        """Handles the SEARCH function (calls READ with filtered results)."""
        search_term = self.search_var.get().strip()
        if not search_term:
            self.display_records() # If empty, display all
            return

        records = self.db.search_records(search_term)
        if records:
            messagebox.showinfo("Search Results", f"Found {len(records)} records matching '{search_term}'.")
            self.display_records(records)
        else:
            messagebox.showinfo("Search Results", f"No records found for '{search_term}'.")
            self.display_records([]) # Clear the table if no results

    def authenticate(self):
        """Show login window. On success, the provided callback will start the app.

        We pass `self.login_callback` which accepts `(username, password)` and
        returns truthy on success. This lets the LoginWindow hand us the entered
        credentials so we can validate (DB or fallback).
        """
        LoginWindow(self, self.login_callback)

    def login_callback(self, username=None, password=None):
        """Validate provided credentials against the database users table."""
        username = (username or "").strip()
        password = (password or "").strip()

        user = self.db.authenticate_user(username, password)
        if user:
            # Set logged-in display and return success.
            try:
                self.logged_in_var.set(user["username"])
            except Exception:
                pass
            self.current_user = user
            return True

        # Fallback path: allow local admin login when DB auth is unavailable.
        if username == "admin" and password == "password":
            try:
                self.logged_in_var.set(username)
            except Exception:
                pass
            self.current_user = {"user_id": 0, "username": username, "role": "admin"}
            return True

        return False

    def start_app(self):
        """Callback after successful login: connect DB, show main window, and initialize UI."""
        # Show the main window. Do not attempt automatic DB connect here to avoid
        # crashing the process if the native connector is unstable on this host.
        # The application will run in offline mode until the user explicitly
        # connects via settings or an explicit action.
        self.authenticated = True
        self.deiconify()
        self.create_widgets()
        # ensure navigation is on top and focusable
        try:
            if hasattr(self, 'nav_frame'):
                try:
                    self.nav_frame.lift()
                except Exception:
                    pass
            # focus first nav button for keyboard accessibility
            if hasattr(self, 'nav_buttons') and 'residents' in self.nav_buttons:
                try:
                    self.nav_buttons['residents'].focus_set()
                except Exception:
                    pass
        except Exception:
            pass
        self.display_records()
        self._refresh_db_status()
        try:
            if "dashboard" in self.section_frames and hasattr(self.section_frames["dashboard"], "refresh_data"):
                self.section_frames["dashboard"].refresh_data()
        except Exception:
            pass

    def set_active_tab(self, key):
        """Switch visible section and update nav button styles."""
        # Hide all section frames (they are managed with .place)
        for k, frame in self.section_frames.items():
            try:
                frame.place_forget()
            except Exception:
                try:
                    frame.lower()
                except Exception:
                    pass

        # Show selected by placing it to occupy the content area and lifting it
        frame = self.section_frames.get(key)
        if frame:
            try:
                frame.place(relx=0, rely=0, relwidth=1, relheight=1)
                try:
                    frame.lift()
                except Exception:
                    pass
                try:
                    frame.focus_set()
                except Exception:
                    pass
            except Exception:
                pass

        # Force a redraw so the newly-packed frame appears immediately
        try:
            self.update_idletasks()
        except Exception:
            pass

        # show a prominent transient title in the content area for clarity
        try:
            if hasattr(self, '_transient_title') and self._transient_title:
                try:
                    self._transient_title.destroy()
                except Exception:
                    pass
            self._transient_title = tk.Label(self.content_container, text=f"*** {key.upper()} VIEW ACTIVE ***",
                                             bg="#ffd54f", fg="#000", font=("Segoe UI", 12, "bold"))
            self._transient_title.place(relx=0.5, rely=0.01, anchor='n')
            # remove after a short delay
            self.content_container.after(1200, lambda: (self._transient_title.destroy() if hasattr(self, '_transient_title') else None))
        except Exception:
            pass

        try:
            print(f"[NAV DEBUG] active frame: {key}")
            if hasattr(self, 'view_status_var'):
                self.view_status_var.set(f"view: {key}")
        except Exception:
            pass
        # Debug: print child widget geometry for all section frames (helps find overlapping widgets)
        try:
            print("[WIDGET DEBUG] Listing section children and geometry:")
            for fname, f in self.section_frames.items():
                try:
                    print(f"  Section: {fname} (w={f.winfo_width()} h={f.winfo_height()})")
                    for child in f.winfo_children():
                        try:
                            cls = child.winfo_class()
                            rx = child.winfo_rootx()
                            ry = child.winfo_rooty()
                            w = child.winfo_width()
                            h = child.winfo_height()
                            gi = None
                            try:
                                gi = child.grid_info()
                            except Exception:
                                gi = None
                            print(f"    {cls} @ root({rx},{ry}) size({w}x{h}) grid={gi}")
                        except Exception as e:
                            print("    child info error:", e)
                except Exception:
                    pass
        except Exception:
            pass
        self._refresh_db_status()

        # update button styles
        for k, btn in self.nav_buttons.items():
            if k == key:
                btn.configure(style="ActiveNav.TButton")
            else:
                btn.configure(style="Nav.TButton")

        self.active_tab = key

        # Always refresh Residents table when returning to that tab.
        if key == "residents":
            try:
                self.display_records()
            except Exception:
                pass
        elif key == "dashboard":
            try:
                if "dashboard" in self.section_frames and hasattr(self.section_frames["dashboard"], "refresh_data"):
                    self.section_frames["dashboard"].refresh_data()
            except Exception:
                pass

    def toggle_theme(self):
        """Toggle between light and dark themes and apply to all frames."""
        self.current_theme = 'dark' if self.current_theme == 'light' else 'light'
        self.apply_theme(self.current_theme)

    def apply_theme(self, theme):
        """Apply theme colors/styles across the app.
        
        MODIFIED: Ensures entry text is black in dark mode for readability.
        """
        style = ttk.Style(self)
        if theme == 'dark':
            bg = '#071337'
            fg = '#D8E2F5'
            entry_bg = '#122448'
            accent = '#2F6FF3'
            input_text_fg = '#EAF1FF'
            input_bg = '#364869'
        else:
            bg = '#ffffff'
            fg = '#000000'
            entry_bg = '#ffffff'
            accent = '#2f85d0'
            input_text_fg = fg
            input_bg = entry_bg

        # Basic widget styles
        try:
            style.configure('TFrame', background=bg)
            style.configure('TLabel', background=bg, foreground=fg)
            style.configure('TButton', background=accent, foreground=fg)
            style.configure('Nav.TButton', background=accent, foreground=fg)
            style.configure('ActiveNav.TButton', background=accent, foreground='#ffffff')
            # Small compact button used for date dropdown arrows
            try:
                style.configure('Small.TButton', background=accent, foreground='#ffffff', padding=1)
            except Exception:
                pass
            
            # Apply light background/black text for entry widgets 
            style.configure('Form.TEntry', fieldbackground=input_bg, background=input_bg, foreground=input_text_fg)
            
            # Ensure base ttk Entry/Combobox styles pick up the input colors
            try:
                style.configure('TEntry', fieldbackground=input_bg, background=input_bg, foreground=input_text_fg)
            except Exception:
                pass
            try:
                style.configure('TCombobox', fieldbackground=input_bg, foreground=input_text_fg)
            except Exception:
                pass
            
            # Treeview uses the general dark/light theme colors
            style.configure('Treeview', background=entry_bg, fieldbackground=entry_bg, foreground=fg)
            style.map('Treeview', background=[('selected', accent)])
        except Exception:
            pass

        # set root/background
        try:
            self.configure(background=bg)
            try:
                self.content_container.configure(style='TFrame')
            except Exception:
                try:
                    self.content_container.configure(background=bg)
                except Exception:
                    pass
        except Exception:
            pass

        # Also update global option database for tk.Entry/Text so plain tk widgets pick up colors
        try:
            try:
                # Force entry background/foreground for plain tk.Entry widgets
                self.option_add('*Entry.background', input_bg)
                self.option_add('*Entry.foreground', input_text_fg) # <-- This is the main fix
                self.option_add('*Entry.insertBackground', input_text_fg)
                
                # Use the general theme colors for Text widgets
                self.option_add('*Text.background', entry_bg)
                self.option_add('*Text.foreground', fg)
                self.option_add('*Text.insertBackground', fg)
            except Exception:
                pass
        except Exception:
            pass

        # allow section frames to adjust (call their set_theme if available)
        try:
            for k, f in self.section_frames.items():
                try:
                    if hasattr(f, 'set_theme'):
                        f.set_theme(theme)
                    else:
                        try:
                            f.configure(style='TFrame')
                        except Exception:
                            try:
                                f.configure(background=bg)
                            except Exception:
                                pass
                except Exception:
                    pass
        except Exception:
            pass

        # Style form entries and special widgets in the Residents form
        try:
            for name, w in getattr(self, 'entries', {}).items():
                try:
                    # DOBWidget: set internal combobox backgrounds
                    if hasattr(w, 'is_dob_widget'):
                        try:
                            for cb in (w.day_cb, w.month_cb, w.year_cb):
                                try:
                                    # Use the input_bg/input_text_fg for the Combobox fields
                                    cb.configure(background=input_bg, foreground=input_text_fg)
                                except Exception:
                                    try:
                                        for child in cb.winfo_children():
                                            if child.winfo_class().lower() in ('entry', 'tkentry'):
                                                child.configure(background=input_bg, foreground=input_text_fg, insertbackground=input_text_fg)
                                    except Exception:
                                        pass
                        except Exception:
                            pass
                        continue

                    # tk.Variable stored fields (e.g., Gender StringVar) skip
                    if isinstance(w, tk.Variable):
                        continue

                    # Text widget
                    if isinstance(w, tk.Text):
                        try:
                            w.configure(background=entry_bg, foreground=fg, insertbackground=fg)
                        except Exception:
                            pass
                        continue

                    # For ttk.Entry / tk.Entry / ttk.Combobox etc.
                    try:
                            # Try to apply Form.TEntry style
                            try:
                                w.configure(style='Form.TEntry')
                            except Exception:
                                pass
                            # Try to set background on inner tk entry widgets
                            for child in w.winfo_children():
                                try:
                                    if child.winfo_class().lower() in ('entry', 'tkentry'):
                                        child.configure(background=input_bg, foreground=input_text_fg, insertbackground=input_text_fg)
                                except Exception:
                                    pass
                            try:
                                w.configure(background=input_bg, foreground=input_text_fg)
                            except Exception:
                                pass
                    except Exception:
                        pass
                except Exception:
                    pass
        except Exception:
            pass

        # Walk all section frames to ensure any remaining plain tk/ttk entries receive colors
        try:
            for fname, frame in self.section_frames.items():
                try:
                    for child in frame.winfo_children():
                        try:
                            # traverse recursively
                            stack = [child]
                            while stack:
                                node = stack.pop()
                                try:
                                    cls = node.winfo_class().lower()
                                except Exception:
                                    cls = ''
                                try:
                                    if cls in ('entry', 'tkentry'):
                                        try:
                                            node.configure(background=input_bg, foreground=input_text_fg, insertbackground=input_text_fg)
                                        except Exception:
                                            pass
                                    if cls == 'text':
                                        try:
                                            node.configure(background=entry_bg, foreground=fg, insertbackground=fg)
                                        except Exception:
                                            pass
                                    # for ttk widgets, try to configure their internal children
                                    try:
                                        for ch in node.winfo_children():
                                            stack.append(ch)
                                    except Exception:
                                        pass
                                except Exception:
                                    pass
                        except Exception:
                            pass
                except Exception:
                    pass
        except Exception:
            pass

        # Additional explicit fixes: ensure disabled/readonly entries and combobox internals
        try:
            for name, w in getattr(self, 'entries', {}).items():
                try:
                    # skip variables
                    if isinstance(w, tk.Variable):
                        continue
                    # For composite DOBWidget, update internal combobox children
                    if hasattr(w, 'is_dob_widget'):
                        try:
                            for cb in (w.day_cb, w.month_cb, w.year_cb):
                                try:
                                    for child in cb.winfo_children():
                                        if child.winfo_class().lower() in ('entry', 'tkentry'):
                                            child.configure(background=input_bg, foreground=input_text_fg, insertbackground=input_text_fg, disabledbackground=input_bg, disabledforeground=input_text_fg)
                                except Exception:
                                    pass
                        except Exception:
                            pass
                        continue

                    # For ttk.Combobox / ttk.Entry: update internal tk.Entry child if present
                    try:
                        for child in w.winfo_children():
                            try:
                                if child.winfo_class().lower() in ('entry', 'tkentry'):
                                    child.configure(background=input_bg, foreground=input_text_fg, insertbackground=input_text_fg, disabledbackground=input_bg, disabledforeground=input_text_fg)
                            except Exception:
                                pass
                    except Exception:
                        pass

                    # If the widget itself is disabled, temporarily enable to push color changes on some platforms
                    try:
                        st = None
                        try:
                            st = w.cget('state')
                        except Exception:
                            st = None
                        if st in ('disabled', 'readonly'):
                            try:
                                w.config(state='normal')
                            except Exception:
                                pass
                            try:
                                for child in w.winfo_children():
                                    try:
                                        if child.winfo_class().lower() in ('entry', 'tkentry'):
                                            child.configure(background=input_bg, foreground=input_text_fg, insertbackground=input_text_fg, disabledbackground=input_bg, disabledforeground=input_text_fg)
                                    except Exception:
                                        pass
                            except Exception:
                                pass
                            try:
                                w.config(state=st)
                            except Exception:
                                pass
                    except Exception:
                        pass
                except Exception:
                    pass
        except Exception:
            pass

        # Ensure the Photo thumbnail label and Photo Path entry are readable in dark mode
        try:
            if hasattr(self, 'photo_thumb'):
                try:
                    self.photo_thumb.configure(background=bg, foreground=fg)
                except Exception:
                    pass
            ph = self.entries.get('Photo Path') if hasattr(self, 'entries') else None
            if ph is not None:
                try:
                    for child in ph.winfo_children():
                        try:
                            if child.winfo_class().lower() in ('entry', 'tkentry'):
                                child.configure(background=input_bg, foreground=input_text_fg, disabledbackground=input_bg, disabledforeground=input_text_fg, insertbackground=input_text_fg)
                        except Exception:
                            pass
                except Exception:
                    pass
        except Exception:
            pass

    def _nav_clicked(self, key):
        """Internal handler that logs and switches tabs."""
        try:
            print(f"[NAV DEBUG] button clicked: {key}")
        except Exception:
            pass
        try:
            self.set_active_tab(key)
        except Exception as e:
            print("[NAV DEBUG] set_active_tab error:", e)

    def try_connect_db(self):
        """Manual DB connect invoked by the user via the Connect DB button."""
        try:
            self.db.connect()
        except Exception as e:
            print("[DB DEBUG] connect error:", e)
        self._refresh_db_status()
        try:
            self.display_records()
        except Exception:
            pass

    def _refresh_db_status(self):
        """Update the nav status label with active backend details."""
        try:
            if not hasattr(self, 'db_status_var'):
                return
            if self.db.conn:
                if getattr(self.db, 'use_sqlite', False):
                    self.db_status_var.set("DB: SQLite fallback (local)")
                else:
                    self.db_status_var.set("DB: MySQL connected")
            else:
                msg = getattr(self.db, 'last_error', None)
                if msg:
                    self.db_status_var.set(f"DB: offline ({msg})")
                else:
                    self.db_status_var.set("DB: offline")
        except Exception:
            pass

    def browse_photo(self):
        """Choose a photo file, copy to local photos folder and show thumbnail. Sets Photo Path entry."""
        path = filedialog.askopenfilename(parent=self, title="Select photo", filetypes=[("Image files","*.jpg *.jpeg *.png *.gif"), ("All files","*.*")])
        if not path:
            return
        photos_dir = os.path.join(os.path.dirname(__file__), "photos")
        os.makedirs(photos_dir, exist_ok=True)
        name = os.path.basename(path)
        ts = int(time.time())
        dest_name = f"{ts}_{name}"
        dest = os.path.join(photos_dir, dest_name)
        try:
            shutil.copy2(path, dest)
            # write full path into Photo Path entry
            if "Photo Path" in self.entries:
                try:
                    self.entries["Photo Path"].config(state='normal')
                except Exception:
                    pass
                self.entries["Photo Path"].delete(0, tk.END)
                self.entries["Photo Path"].insert(0, dest)
                try:
                    self.entries["Photo Path"].config(state='disabled')
                except Exception:
                    pass
            # show thumbnail
            self._show_thumbnail(dest)
        except Exception as e:
            messagebox.showerror("Photo Error", f"Could not copy photo:\n{e}")

    def _show_thumbnail(self, path):
        try:
            if not os.path.exists(path):
                self.photo_thumb.config(text="No Photo")
                return
            if PIL_AVAILABLE:
                img = Image.open(path)
                img.thumbnail((120,140))
                self._res_thumb = ImageTk.PhotoImage(img)
                self.photo_thumb.config(image=self._res_thumb, text="")
            else:
                # Tk PhotoImage supports PNG/GIF depending on platform
                self._res_thumb = tk.PhotoImage(file=path)
                self.photo_thumb.config(image=self._res_thumb, text="")
        except Exception:
            self.photo_thumb.config(text="No Preview")

    def _save_photo_for_id(self, src_path, record_id):
        """Move/rename the saved photo to photos/<id>.<ext> and update DB.photo_path."""
        if not src_path or not os.path.exists(src_path):
            return False
        photos_dir = os.path.join(os.path.dirname(__file__), "photos")
        os.makedirs(photos_dir, exist_ok=True)
        _, ext = os.path.splitext(src_path)
        new_name = f"{record_id}{ext.lower()}"
        dest = os.path.join(photos_dir, new_name)
        try:
            # move (overwrite if exists)
            shutil.move(src_path, dest)
        except Exception:
            try:
                # fallback copy + remove
                shutil.copy2(src_path, dest)
                os.remove(src_path)
            except Exception:
                return False
        # update DB photo_path if column exists
        try:
            upd_sql = "UPDATE residents SET photo_path=%s WHERE barangay_id=%s"
            self.db.execute_query(upd_sql, (dest, record_id), commit=True)
        except Exception:
            # ignore DB update errors here (DB may not have photo_path)
            pass
        return True

# --- 3. Main Execution ---
if __name__ == "__main__":
    print("[APP DEBUG] Creating ResidentApp instance")
    app = ResidentApp()
    print("[APP DEBUG] ResidentApp instance created")
    # Ensure the database connection is closed when the application exits
    app.protocol("WM_DELETE_WINDOW", lambda: (app.db.close(), app.destroy()))
    print("[APP DEBUG] entering mainloop")
    app.mainloop()