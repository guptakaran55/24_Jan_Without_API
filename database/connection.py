# database/connection.py
# Database connection management

import psycopg2
from psycopg2 import pool
import os
from dotenv import load_dotenv

load_dotenv()

connection_pool = None

def init_pool():
    """Initialize database connection pool"""
    global connection_pool
    try:
        connection_pool = psycopg2.pool.SimpleConnectionPool(
            1, 20,
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', '5432'),
            database=os.getenv('DB_NAME', 'energy_survey'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD')
        )
        print("✓ Database connection pool created")
        return True
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False

def get_connection():
    """Get a connection from the pool"""
    if connection_pool is None:
        init_pool()
    return connection_pool.getconn()

def return_connection(conn):
    """Return connection to pool"""
    if connection_pool:
        connection_pool.putconn(conn)

def close_pool():
    """Close all connections in pool"""
    global connection_pool
    if connection_pool:
        connection_pool.closeall()
        print("Database pool closed")

def query(sql, params=None):
    """Execute a query and return results"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(sql, params)
        
        # Check if query returns results (SELECT or RETURNING clause)
        if cursor.description:
            columns = [desc[0] for desc in cursor.description]
            results = []
            for row in cursor.fetchall():
                results.append(dict(zip(columns, row)))
            if sql.strip().upper().startswith('SELECT'):
                return results
            else:
                # For INSERT/UPDATE/DELETE with RETURNING
                conn.commit()
                return results
        else:
            # No results returned
            conn.commit()
            return cursor.rowcount
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Query error: {e}")
        raise e
    finally:
        if conn:
            return_connection(conn)

def test_connection():
    """Test database connection"""
    try:
        result = query("SELECT NOW() as current_time")
        print("✓ Database connection successful!")
        print(f"Server time: {result[0]['current_time']}")
        return True
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False
