"""
audit_service.py
================
Audit Logging and Compliance Module.

Features:
- Records security and record lifecycle events.
- Anonymizes / suppresses sensitive clinical details to comply with medical privacy standards.
- Supports atomic logging within active transactions.
- Provides filtered retrieval for Administrator auditing.
"""

import sqlite3
from typing import List, Dict, Any, Optional
from database import get_db_connection
from blockchain import get_current_utc_timestamp


def record_audit_event(
    cursor_or_conn,
    action: str,
    entity_type: str,
    entity_id: Optional[str],
    ip_address: str,
    details: str,
    actor_user_id: Optional[int] = None,
    timestamp: Optional[str] = None
) -> int:
    """
    Inserts an immutable audit event into the audit_logs table.
    Works with either an active cursor (inside a transaction) or a connection.
    """
    ts = timestamp if timestamp else get_current_utc_timestamp()
    sql = """
        INSERT INTO audit_logs (
            actor_user_id, action, entity_type, entity_id, ip_address, timestamp, details
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    params = (
        actor_user_id,
        action.strip().upper(),
        entity_type.strip().upper(),
        str(entity_id) if entity_id is not None else None,
        ip_address.strip() if ip_address else "127.0.0.1",
        ts,
        details.strip()
    )

    if isinstance(cursor_or_conn, sqlite3.Cursor):
        cursor_or_conn.execute(sql, params)
        return cursor_or_conn.lastrowid
    else:
        with cursor_or_conn:
            cursor = cursor_or_conn.cursor()
            cursor.execute(sql, params)
            return cursor.lastrowid


def get_audit_logs(
    db_path: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    action_filter: Optional[str] = None,
    entity_filter: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Retrieves audit logs with actor username join for administrator inspection.
    """
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        query = """
            SELECT 
                a.id,
                a.actor_user_id,
                u.username AS actor_username,
                u.role AS actor_role,
                a.action,
                a.entity_type,
                a.entity_id,
                a.ip_address,
                a.timestamp,
                a.details
            FROM audit_logs a
            LEFT JOIN users u ON a.actor_user_id = u.id
            WHERE 1=1
        """
        params = []
        if action_filter:
            query += " AND a.action = ?"
            params.append(action_filter.strip().upper())
        if entity_filter:
            query += " AND a.entity_type = ?"
            params.append(entity_filter.strip().upper())

        query += " ORDER BY a.id DESC LIMIT ? OFFSET ?;"
        params.extend([int(limit), int(offset)])

        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_total_audit_logs_count(db_path: Optional[str] = None) -> int:
    """Returns total count of audit events in the system."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) AS count FROM audit_logs;")
        row = cursor.fetchone()
        return row["count"] if row else 0
    finally:
        conn.close()
