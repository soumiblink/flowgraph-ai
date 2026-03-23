import sqlite3

conn = sqlite3.connect("data.db")

tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()

for table in tables:
    table_name = table[0]
    print(f"\n=== {table_name} ===")

    columns = conn.execute(f"PRAGMA table_info({table_name});").fetchall()
    for col in columns:
        print(col[1])

conn.close()