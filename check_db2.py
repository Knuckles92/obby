from database.models import db

rows = db.execute_query(
    'SELECT id, timestamp, markdown_file_path, source_type, summary FROM semantic_entries WHERE source_type IN ("living_note", "comprehensive") ORDER BY timestamp DESC LIMIT 10'
)

print("Recent semantic entries with details:")
for r in rows:
    print(f"\nID: {r['id']}")
    print(f"  Timestamp: {r['timestamp']}")
    print(f"  Type: {r['source_type']}")
    print(f"  Path: {r['markdown_file_path']}")
    print(f"  Summary: {r['summary'][:80] if r['summary'] else 'None'}...")

