# SQLite Database Persistence Module - Phoenix Backup

This module is responsible for setting up the local SQLite database pool, applying DDL schema migrations, and executing transactional CRUD operations via repository layers.

## Features:
1.  **Transactional Pool Manager:** Uses the Python context manager `get_connection()` to coordinate SQL query transactions, automatically committing changes or rolling them back if execution fails.
2.  **Constraint Enforcement:** Enforces foreign keys (`PRAGMA foreign_keys = ON;`) and writes data using Write-Ahead Logging (`WAL` mode) to improve write speeds on consumer PCs.
3.  **Automatic Schema Migrator:** The `MigrationRunner` automatically bootstraps version-tracked table setups on startup, tracking version increments in the `schema_migrations` log table.
4.  **Decoupled Repositories:** Implements clean Data Access Objects (DAOs):
    *   `DeviceRepository`: Log and upsert device metadata configurations.
    *   `BackupJobRepository`: Initialize and update migration session transactions.
    *   `AuditLogRepository`: Relational logger capturing system warnings/errors.

## Usage:
```python
from shared.db.connection import DatabaseConnectionManager
from shared.db.migrations import MigrationRunner
from shared.db.repositories import DeviceRepository

# Initialize connection pool manager
db_manager = DatabaseConnectionManager(db_path="phoenix_local.db")

# Apply database migrations on startup
with db_manager.get_connection() as conn:
    migrator = MigrationRunner(conn)
    migrator.run_migrations()

# Write device metadata record
with db_manager.get_connection() as conn:
    device_repo = DeviceRepository(conn)
    device_repo.save_device(
        device_id="serial-123",
        manufacturer="Samsung",
        model="SM-G991B",
        android_version="14",
        api_level=34
    )
```

## Running Unit Tests:
```bash
python -m unittest shared.db.test_persistence
```
