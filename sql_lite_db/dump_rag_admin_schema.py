import sqlite3
from pathlib import Path

DB_PATH = Path(r"D:\Projects\rag\rag-engine\sql_lite_db")


def get_schema(db_path: Path):
    if not db_path.exists():
        raise FileNotFoundError(f"Database file not found: {db_path}")

    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name, type, sql FROM sqlite_master WHERE type IN ('table', 'view') AND name NOT LIKE 'sqlite_%' ORDER BY type, name"
        )
        return cursor.fetchall()


def main():
    print(f"Inspecting SQLite schema for: {DB_PATH}")
    schema_objects = get_schema(DB_PATH)
    if not schema_objects:
        print("No tables or views found in the database.")
        return

    for name, obj_type, sql in schema_objects:
        print("---")
        print(f"{obj_type.upper()}: {name}")
        print(sql.strip())


if __name__ == "__main__":
    main()
