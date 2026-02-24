import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
DB_URL = os.getenv("DATABASE_URL")

try:
    conn = psycopg2.connect(DB_URL)
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM information_schema.tables WHERE table_name = 'licitaciones_biblioteca'")
        exists = cur.fetchone()
        if exists:
            print("TABLE_EXISTS")
        else:
            print("TABLE_MISSING")
    conn.close()
except Exception as e:
    print(f"DB_ERROR: {e}")
