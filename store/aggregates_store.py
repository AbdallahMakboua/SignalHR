"""
SQLite aggregates store.

Replaces AWS DynamoDB AggregatesTable for local development.
- Table with PK=userId, SK=weekId (matches DC-FEAT-V1)
- Stores computed features and indices
- Provides query interface
"""

import sqlite3
import json
from typing import Any, Dict, List, Optional
from datetime import datetime


class AggregatesStore:
    """SQLite-based aggregates store simulating AWS DynamoDB."""

    def __init__(self, db_path: str = "/tmp/signalhr_aggregates.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create aggregates table (matches DC-FEAT-V1 schema)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS aggregates (
                userId TEXT NOT NULL,
                weekId TEXT NOT NULL,
                signalCounts TEXT,
                overload_trend REAL,
                context_switch_rate REAL,
                collaboration_index REAL,
                growth_index REAL,
                createdAt TEXT,
                PRIMARY KEY (userId, weekId)
            )
        """)

        # Create indices
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_userId ON aggregates(userId)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_weekId ON aggregates(weekId)")

        conn.commit()
        conn.close()

    def put_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulate DynamoDB PutItem API.

        Args:
            item: Dict with userId, weekId, and feature fields

        Returns:
            Response with status
        """
        user_id = item.get("userId")
        week_id = item.get("weekId")
        signal_counts = json.dumps(item.get("signalCounts", {}))
        overload_trend = item.get("overload_trend", 0.0)
        context_switch_rate = item.get("context_switch_rate", 0.0)
        collaboration_index = item.get("collaboration_index", 0.0)
        growth_index = item.get("growth_index", 0.0)
        created_at = item.get("createdAt", datetime.utcnow().isoformat())

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT OR REPLACE INTO aggregates
                (userId, weekId, signalCounts, overload_trend, context_switch_rate, 
                 collaboration_index, growth_index, createdAt)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, week_id, signal_counts, overload_trend, context_switch_rate,
                  collaboration_index, growth_index, created_at))

            conn.commit()
            return {"status": "success"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
        finally:
            conn.close()

    def get_item(self, user_id: str, week_id: str) -> Optional[Dict[str, Any]]:
        """
        Simulate DynamoDB GetItem API.

        Args:
            user_id: userId (partition key)
            week_id: weekId (sort key)

        Returns:
            Item dict or None
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT * FROM aggregates WHERE userId = ? AND weekId = ?
            """, (user_id, week_id))

            row = cursor.fetchone()
            if row:
                item = dict(row)
                item["signalCounts"] = json.loads(item["signalCounts"])
                return item
            return None
        finally:
            conn.close()

    def query_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Query all aggregates for a user.

        Args:
            user_id: userId to query

        Returns:
            List of item dicts
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT * FROM aggregates WHERE userId = ? ORDER BY weekId DESC
            """, (user_id,))

            items = []
            for row in cursor.fetchall():
                item = dict(row)
                item["signalCounts"] = json.loads(item["signalCounts"])
                items.append(item)
            return items
        finally:
            conn.close()

    def scan(self) -> List[Dict[str, Any]]:
        """
        Scan all aggregates (full table).

        Returns:
            List of all items
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT * FROM aggregates")

            items = []
            for row in cursor.fetchall():
                item = dict(row)
                item["signalCounts"] = json.loads(item["signalCounts"])
                items.append(item)
            return items
        finally:
            conn.close()

    def delete_item(self, user_id: str, week_id: str) -> Dict[str, Any]:
        """
        Simulate DynamoDB DeleteItem API.

        Args:
            user_id: userId (partition key)
            week_id: weekId (sort key)

        Returns:
            Response with status
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                DELETE FROM aggregates WHERE userId = ? AND weekId = ?
            """, (user_id, week_id))

            conn.commit()
            return {"status": "success"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
        finally:
            conn.close()

    def clear(self):
        """Clear all aggregates (for testing)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM aggregates")
        conn.commit()
        conn.close()

    def get_count(self) -> int:
        """Get total number of aggregates."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM aggregates")
            return cursor.fetchone()[0]
        finally:
            conn.close()
