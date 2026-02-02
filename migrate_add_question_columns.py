import sqlite3

DB_PATH = "testprep.db"

def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Add columns if they do not already exist
    cur.execute("PRAGMA table_info(questions);")
    existing_cols = {row[1] for row in cur.fetchall()}

    if "subject" not in existing_cols:
        cur.execute("ALTER TABLE questions ADD COLUMN subject TEXT;")
    if "type" not in existing_cols:
        cur.execute("ALTER TABLE questions ADD COLUMN type TEXT;")
    if "difficulty" not in existing_cols:
        cur.execute("ALTER TABLE questions ADD COLUMN difficulty TEXT;")
    if "tags" not in existing_cols:
        cur.execute("ALTER TABLE questions ADD COLUMN tags TEXT;")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    main()
