import psycopg2
import os

def check_db():
    conn = psycopg2.connect(
        dbname=os.getenv('DB_NAME', 'strikeiq'),
        user=os.getenv('DB_USER', 'strikeiq'),
        password=os.getenv('DB_PASSWORD', 'strikeiq123'),
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5432')
    )
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
