import os
import shutil
import sys
import sqlite3
from sqlalchemy import create_engine, text, inspect

# Add workspace directory to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.config import settings
from backend.database import normalize_database_url, mask_database_url, Base

def backup_sqlite_db(sqlite_path: str = "healthvault.db") -> str:
    """
    Safely creates healthvault.db.backup before any migration operations.
    """
    if not os.path.exists(sqlite_path):
        print(f"[Backup] Source SQLite file '{sqlite_path}' does not exist.")
        return ""
    backup_path = f"{sqlite_path}.backup"
    shutil.copy2(sqlite_path, backup_path)
    print(f"[Backup] Preserved '{sqlite_path}' -> '{backup_path}'.")
    return backup_path

def migrate_sqlite_to_postgres(sqlite_path: str = "healthvault.db", postgres_url: str = None):
    """
    Migrates all 8 tables and records from SQLite to PostgreSQL in foreign-key dependency order:
    users -> patients, doctors -> visits -> documents -> consents, access_logs, processing_jobs
    """
    target_url = postgres_url or settings.DATABASE_URL
    normalized_target = normalize_database_url(target_url)

    if "sqlite" in normalized_target:
        print(f"[Migration Warning] Target DATABASE_URL is SQLite ({mask_database_url(normalized_target)}). Please set a PostgreSQL DATABASE_URL in .env to perform live migration.")
        return False

    print(f"[Migration] Starting migration to PostgreSQL target: {mask_database_url(normalized_target)}")

    # 1. Create SQLite backup
    backup_sqlite_db(sqlite_path)

    # 2. Connect to SQLite source
    if not os.path.exists(sqlite_path):
        raise FileNotFoundError(f"SQLite source file '{sqlite_path}' not found.")
        
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_cursor = sqlite_conn.cursor()

    # Get row counts in source SQLite
    tables_order = ["users", "patients", "doctors", "visits", "documents", "consents", "access_logs", "processing_jobs"]
    sqlite_counts = {}
    for table in tables_order:
        try:
            sqlite_cursor.execute(f"SELECT COUNT(*) FROM {table}")
            sqlite_counts[table] = sqlite_cursor.fetchone()[0]
        except Exception:
            sqlite_counts[table] = 0

    print("[Migration] Source SQLite Row Counts:", sqlite_counts)

    # 3. Connect to PostgreSQL target
    pg_engine = create_engine(normalized_target, pool_pre_ping=True)
    
    # Create all tables on target if not present
    Base.metadata.create_all(bind=pg_engine)

    # Copy data in order
    with pg_engine.connect() as pg_conn:
        transaction = pg_conn.begin()
        try:
            for table in tables_order:
                sqlite_cursor.execute(f"SELECT * FROM {table}")
                rows = sqlite_cursor.fetchall()
                if not rows:
                    print(f"  Table '{table}': 0 rows to copy.")
                    continue

                # Get column names
                col_names = [description[0] for description in sqlite_cursor.description]
                cols_str = ", ".join(col_names)
                placeholders = ", ".join([f":{col}" for col in col_names])

                insert_sql = text(f"INSERT INTO {table} ({cols_str}) VALUES ({placeholders}) ON CONFLICT DO NOTHING")
                
                records = [dict(zip(col_names, row)) for row in rows]
                pg_conn.execute(insert_sql, records)
                print(f"  Migrated {len(records)} rows into '{table}'.")

            transaction.commit()
            print("[Migration] Data commit successful.")

        except Exception as e:
            transaction.rollback()
            print(f"[Migration Error] Failed during data copy: {e}")
            raise e
        finally:
            sqlite_conn.close()

    # 4. Verify post-migration row counts on PostgreSQL
    with pg_engine.connect() as pg_conn:
        pg_counts = {}
        for table in tables_order:
            cnt = pg_conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            pg_counts[table] = cnt
        print("[Migration] Target PostgreSQL Post-Migration Counts:", pg_counts)

    # Validate equality
    all_match = all(sqlite_counts[t] == pg_counts[t] for t in tables_order)
    if all_match:
        print("[Migration SUCCESS] All row counts match perfectly between SQLite and PostgreSQL!")
    else:
        print("[Migration WARNING] Row count mismatch detected!")

    return all_match

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else None
    migrate_sqlite_to_postgres(postgres_url=target)
