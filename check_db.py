import sqlite3

conn = sqlite3.connect('obby.db')
cursor = conn.cursor()

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cursor.fetchall()]
print('Available tables:', tables)

# Check for skateboarding_wheels references in each table
for table in tables:
    try:
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [row[1] for row in cursor.fetchall()]
        print(f"\n{table} columns: {columns}")

        # Look for path-related columns
        path_columns = [col for col in columns if 'path' in col.lower()]
        if path_columns:
            for col in path_columns:
                cursor.execute(f"SELECT * FROM {table} WHERE {col} LIKE ?", ('%skateboarding_wheels%',))
                rows = cursor.fetchall()
                if rows:
                    print(f"Found {len(rows)} references in {table}.{col}:")
                    for row in rows[:5]:  # Show first 5
                        print(f"  {row}")
    except Exception as e:
        print(f"Error checking table {table}: {e}")

conn.close()
