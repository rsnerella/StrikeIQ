import psycopg2
import os
from urllib.parse import urlparse

def check_db():
    db_url = "postgresql://postgres.yjxdepuwskcankmtfjvz:StrikeIQ%402026%23DB@aws-1-ap-northeast-1.pooler.supabase.com:5432/postgres"
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        tables = cursor.fetchall()
        print(f"Tables: {[t[0] for t in tables]}")
        
        for table in [t[0] for t in tables]:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()
            print(f"- {table}: {count[0]} entries")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    check_db()
