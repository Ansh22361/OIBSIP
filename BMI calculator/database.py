import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
import random

class Database:
    def __init__(self, db_path: str):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        self._init_db()
        self.seed_dummy_data()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS bmi_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    weight_kg REAL NOT NULL,
                    height_m REAL NOT NULL,
                    bmi REAL NOT NULL,
                    category TEXT NOT NULL,
                    recorded_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );
            """)

    def seed_dummy_data(self):
        """Insert sample users + history only if database is empty."""
        with self._connect() as conn:
            count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            if count > 0:
                return

            dummy_users = [
                ("Alice Johnson", 62, 1.68),
                ("Bob Smith", 85, 1.80),
                ("Carol Davis", 54, 1.60),
            ]

            for name, base_weight, height_m in dummy_users:
                cur = conn.execute("INSERT INTO users (name) VALUES (?)", (name,))
                user_id = cur.lastrowid

                for weeks_ago in range(8, 0, -1):
                    weight = round(base_weight + random.uniform(-2, 2), 1)
                    bmi = round(weight / (height_m ** 2), 2)
                    category = self._category_for_bmi(bmi)
                    date = (datetime.now() - timedelta(weeks=weeks_ago)).strftime("%Y-%m-%d %H:%M:%S")
                    conn.execute(
                        """INSERT INTO bmi_records
                           (user_id, weight_kg, height_m, bmi, category, recorded_at)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (user_id, weight, height_m, bmi, category, date),
                    )

    @staticmethod
    def _category_for_bmi(bmi: float) -> str:
        if bmi < 18.5:
            return "Underweight"
        if bmi < 25:
            return "Normal"
        if bmi < 30:
            return "Overweight"
        return "Obese"

    def add_user(self, name: str) -> int:
        name = name.strip()
        if not name:
            raise ValueError("Name cannot be empty.")
        with self._connect() as conn:
            cur = conn.execute("INSERT INTO users (name) VALUES (?)", (name,))
            return cur.lastrowid

    def get_users(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM users ORDER BY name").fetchall()
            return [dict(r) for r in rows]

    def get_user_id(self, name: str) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT id FROM users WHERE name = ?", (name,)).fetchone()
            if row is None:
                raise ValueError(f"User '{name}' not found.")
            return row["id"]

    def add_record(self, user_id, weight_kg, height_m, bmi, category, recorded_at=None):
        with self._connect() as conn:
            if recorded_at:
                conn.execute(
                    """INSERT INTO bmi_records
                       (user_id, weight_kg, height_m, bmi, category, recorded_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (user_id, weight_kg, height_m, bmi, category, recorded_at),
                )
            else:
                conn.execute(
                    """INSERT INTO bmi_records
                       (user_id, weight_kg, height_m, bmi, category)
                       VALUES (?, ?, ?, ?, ?)""",
                    (user_id, weight_kg, height_m, bmi, category),
                )

    def get_history(self, user_id: int) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM bmi_records WHERE user_id = ? ORDER BY recorded_at DESC",
                (user_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_statistics(self, user_id: int) -> dict | None:
        records = self.get_history(user_id)
        if not records:
            return None
        bmis = [r["bmi"] for r in records]
        return {
            "count": len(bmis),
            "latest": bmis[0],
            "average": round(sum(bmis) / len(bmis), 2),
            "min": min(bmis),
            "max": max(bmis),
            "change": round(bmis[0] - bmis[-1], 2),
        }

    def get_latest_record(self, user_id: int) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM bmi_records WHERE user_id = ? ORDER BY recorded_at DESC LIMIT 1",
                (user_id,),
            ).fetchone()
            return dict(row) if row else None

    def delete_record(self, record_id: int) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM bmi_records WHERE id = ?", (record_id,))

    def delete_user(self, name: str) -> None:
        with self._connect() as conn:
            row = conn.execute("SELECT id FROM users WHERE name = ?", (name,)).fetchone()
            if row is None:
                raise ValueError(f"User '{name}' not found.")
            user_id = row["id"]
            conn.execute("DELETE FROM bmi_records WHERE user_id = ?", (user_id,))
            conn.execute("DELETE FROM users WHERE id = ?", (user_id,))

    def export_csv(self, user_id: int, path: str) -> None:
        import csv
        records = self.get_history(user_id)
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["id", "user_id", "weight_kg", "height_m", "bmi", "category", "recorded_at"],
            )
            writer.writeheader()
            writer.writerows(records)