# setup_database.py
import os
from database.connection import init_pool, query as db_query, close_pool

def setup_database():
    print("Setting up database...")
    try:
        sql_path = os.path.join('config', 'database.sql')
        with open(sql_path, 'r') as f:
            sql_script = f.read()
        
        statements = [s.strip() for s in sql_script.split(';') if s.strip()]
        for statement in statements:
            if statement:
                db_query(statement)
        
        print("✓ Database setup complete!")
        count = db_query("SELECT COUNT(*) as count FROM appliance_defaults")
        print(f"✓ Loaded {count[0]['count']} appliance defaults")
    except Exception as e:
        print(f"✗ Setup failed: {e}")

if __name__ == "__main__":
    init_pool()
    try:
        setup_database()
    finally:
        close_pool()
