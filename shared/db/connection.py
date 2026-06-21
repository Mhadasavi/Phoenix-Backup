"""
Phoenix Backup SQLite Connection Pool Manager (Hardened Python Implementation)
"""

import logging
import os
import sqlite3
from contextlib import contextmanager
from typing import Generator

# Configure module-level logger
logger = logging.getLogger("phoenix.db")

class DatabaseConnectionManager:
    """
    Manages SQLite database connections, enforcing foreign key pragmas,
    absolute paths, and busy timeouts.
    """

    def __init__(self, db_path: str):
        # Resolve to absolute path to prevent directory drift bugs (GAP-05)
        self.db_path = db_path if db_path == ":memory:" else os.path.abspath(db_path)
        logger.debug("Database manager initialized targeting: %s", self.db_path)

    @contextmanager
    def get_connection(self, read_only: bool = False) -> Generator[sqlite3.Connection, None, None]:
        """
        Context manager yielding a configured SQLite connection.
        Enforces transaction commit/rollback and busy timeouts.
        """
        conn = None
        try:
            # Add timeout parameter (30.0s) to prevent instant crashes during concurrent locks
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON;")
            
            # WAL mode is only valid for physical filesystem databases
            if self.db_path != ":memory:":
                conn.execute("PRAGMA journal_mode = WAL;")
                conn.execute("PRAGMA synchronous = NORMAL;")
            
            # Avoid deadlock by starting write transactions with IMMEDIATE locking (GAP-06)
            if not read_only:
                conn.execute("BEGIN IMMEDIATE;")
            else:
                conn.execute("BEGIN DEFERRED;")

            yield conn
            conn.commit()
        except sqlite3.Error as err:
            logger.error("Database transaction error: %s", err)
            if conn:
                try:
                    conn.rollback()
                except sqlite3.Error as rollback_err:
                    logger.debug("Rollback attempt failed: %s", rollback_err)
            raise err
        finally:
            if conn:
                conn.close()
