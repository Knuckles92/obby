from database.models import db

rows = db.execute_query(
    'SELECT id, markdown_file_path, source_type FROM semantic_entries WHERE source_type IN ("session_summary", "comprehensive") ORDER BY timestamp DESC LIMIT 10'
)

print("Recent semantic entries:")
for r in rows:
    print(f"ID: {r['id']}, Path: {r['markdown_file_path']}, Type: {r['source_type']}")

