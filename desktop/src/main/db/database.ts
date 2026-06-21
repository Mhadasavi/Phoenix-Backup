// @ts-ignore (better-sqlite3 may lack type definitions during skeleton compilation)
import Database from 'better-sqlite3';

/**
 * Local SQLite Database Connection and Schema Migrations Coordinator.
 */
export class DatabaseManager {
  private db: any = null;

  /**
   * Initializes local connection pool and applies database DDL statements.
   * TODO: Add version tracking and handle schema migration triggers in subsequent Sprints.
   */
  public initialize(dbPath: string): void {
    try {
      this.db = new Database(dbPath, { verbose: console.log });
      
      // Enforce SQL foreign key validations
      this.db.pragma('foreign_keys = ON');

      // Initialize DDL migrations for Sprint 1
      this.createTables();
      
      console.log(`[DatabaseManager] Database initialized at: ${dbPath}`);
    } catch (error) {
      console.error('[DatabaseManager] Connection initialization failed:', error);
      throw error;
    }
  }

  /**
   * Execute schema migrations.
   * TODO: Move SQL schemas to static files inside shared assets folder in v2 monorepo.
   */
  private createTables(): void {
    const migrations = `
      CREATE TABLE IF NOT EXISTS devices (
          device_id TEXT PRIMARY KEY,
          manufacturer TEXT NOT NULL,
          model TEXT NOT NULL,
          android_version TEXT NOT NULL,
          api_level INTEGER NOT NULL,
          first_seen DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          last_seen DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
      );

      CREATE TABLE IF NOT EXISTS backup_jobs (
          job_id TEXT PRIMARY KEY,
          device_id TEXT NOT NULL,
          start_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          end_time DATETIME,
          status TEXT NOT NULL CHECK(status IN ('STARTED', 'COMPLETED', 'FAILED', 'PARTIAL')),
          readiness_score INTEGER CHECK(readiness_score >= 0 AND readiness_score <= 100),
          encryption_salt TEXT NOT NULL,
          key_derivation_rounds INTEGER NOT NULL,
          FOREIGN KEY(device_id) REFERENCES devices(device_id) ON DELETE CASCADE
      );

      CREATE TABLE IF NOT EXISTS audit_logs (
          log_id INTEGER PRIMARY KEY AUTOINCREMENT,
          timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          log_level TEXT NOT NULL CHECK(log_level IN ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'FATAL')),
          module TEXT NOT NULL,
          message TEXT NOT NULL
      );

      CREATE TABLE IF NOT EXISTS job_contacts (
          job_id TEXT NOT NULL,
          name TEXT NOT NULL,
          phones TEXT,
          emails TEXT,
          PRIMARY KEY(job_id, name),
          FOREIGN KEY(job_id) REFERENCES backup_jobs(job_id) ON DELETE CASCADE
      );

      CREATE TABLE IF NOT EXISTS job_sms (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          job_id TEXT NOT NULL,
          address TEXT NOT NULL,
          body TEXT,
          timestamp INTEGER NOT NULL,
          type TEXT NOT NULL,
          FOREIGN KEY(job_id) REFERENCES backup_jobs(job_id) ON DELETE CASCADE
      );

      CREATE TABLE IF NOT EXISTS job_call_logs (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          job_id TEXT NOT NULL,
          number TEXT NOT NULL,
          timestamp INTEGER NOT NULL,
          duration INTEGER NOT NULL,
          type TEXT NOT NULL,
          name TEXT,
          FOREIGN KEY(job_id) REFERENCES backup_jobs(job_id) ON DELETE CASCADE
      );

      CREATE TABLE IF NOT EXISTS job_extraction_logs (
          job_id TEXT NOT NULL,
          data_type TEXT NOT NULL CHECK(data_type IN ('CONTACTS', 'SMS', 'CALL_LOGS', 'SYSTEM_INFO')),
          status TEXT NOT NULL CHECK(status IN ('SUCCESS', 'FAILED', 'PERMISSION_DENIED')),
          records_extracted INTEGER NOT NULL DEFAULT 0,
          timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY(job_id, data_type),
          FOREIGN KEY(job_id) REFERENCES backup_jobs(job_id) ON DELETE CASCADE
      );
    `;

    this.db.exec(migrations);
  }

  /**
   * Expose raw database connection pool.
   */
  public getPool(): any {
    return this.db;
  }
}
