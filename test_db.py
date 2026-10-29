import main
import pprint

db = main.ResidentDB()   # uses same DB config as your app
pp = pprint.PrettyPrinter(width=120)

print("=== all full_name rows ===")
if db.execute_query("SELECT barangay_id, full_name FROM residents"):
    rows = db.cursor.fetchall()
    pp.pprint(rows)
else:
    print("Query failed: SELECT all")

name = "Pedro Reyes"  # change as needed
print(f"\n=== LIKE search for: {name} ===")
q = "SELECT barangay_id, full_name FROM residents WHERE LOWER(full_name) LIKE LOWER(%s)"
ok = db.execute_query(q, (f"%{name}%",))
print("ok:", ok)
if ok:
    pp.pprint(db.cursor.fetchall())

print(f"\n=== exact match search for: {name} ===")
q2 = "SELECT barangay_id, full_name FROM residents WHERE full_name = %s"
ok2 = db.execute_query(q2, (name,))
print("ok:", ok2)
if ok2:
    pp.pprint(db.cursor.fetchall())

db.close()