
import os
import psycopg2
import psycopg2.extras
import traceback

DB_CONNECTION_STRING = os.getenv(
    "DATABASE_URL",
    "postgresql://neondb_owner:npg_xHS7sA1FDPqI@ep-hidden-grass-a4sa46kc-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require"
)

def debug_query():
    try:
        conn = psycopg2.connect(DB_CONNECTION_STRING)
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            print("Executing query...")
            cur.execute("""
                SELECT u.user_id, u.email, u.nombre, u.nivel_acceso,
                       d.nombre AS division, d.division_id, u.role_id,
                       u.activo AS es_activo
                FROM users u
                LEFT JOIN divisiones d ON u.division_id = d.division_id
                ORDER BY u.nombre
            """)
            print("Query executed successfully.")
            rows = cur.fetchall()
            print(f"Fetched {len(rows)} rows.")
            for r in rows:
                print(r)
        conn.close()
    except Exception as e:
        print(f"ERROR: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    debug_query()
