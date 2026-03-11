import psycopg2
import os
from typing import Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIDatabase:
    def __init__(self):
        self.db_config = {
            'dbname': os.getenv('DB_NAME', 'strikeiq'),
            'user': os.getenv('DB_USER', 'strikeiq'),
            'password': os.getenv('DB_PASSWORD', 'strikeiq123'),
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': os.getenv('DB_PORT', '5432')
        }
        self.connection = None
        self.cursor = None
        
    def connect(self):
        """Establish database connection"""
        try:
            self.connection = psycopg2.connect(**self.db_config)
            self.cursor = self.connection.cursor()
            logger.info("Successfully connected to PostgreSQL database")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            return False
            
    def disconnect(self):
        """Close database connection"""
        try:
            if self.cursor:
                self.cursor.close()
            if self.connection:
                self.connection.close()
            logger.info("Database connection closed")
        except Exception as e:
            logger.error(f"Error closing database connection: {e}")
            
    def execute_query(self, query: str, params: tuple = None):
        """Execute a query with parameters"""
        try:
            if not self.connection or self.connection.closed:
                if not self.connect():
                    logger.warning("AI DB connection unavailable — skipping query")
                    return False
            
            self.cursor.execute(query, params or ())
            self.connection.commit()
            logger.info(f"Query executed successfully: {query[:50]}...")
            return True
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            if self.connection:
                try:
                    self.connection.rollback()
                    logger.info("Transaction rolled back")
                except Exception as rollback_error:
                    logger.error(f"Error during rollback: {rollback_error}")
            return False
            
    def fetch_query(self, query: str, params: tuple = None):
        """Execute a query and fetch results"""
        try:
            if not self.connection or self.connection.closed:
                if not self.connect():
                    logger.warning("AI DB connection unavailable — skipping query")
                    return []
            
            self.cursor.execute(query, params or ())
            results = self.cursor.fetchall()
            logger.info(f"Fetched {len(results)} rows")
            return results
        except Exception as e:
            logger.error(f"AI DB query failed: {e}")
            return []
            
    def fetch_one(self, query: str, params: tuple = None):
        """Execute a query and fetch single result"""
        try:
            if not self.connection or self.connection.closed:
                if not self.connect():
                    logger.warning("AI DB connection unavailable — skipping query")
                    return None
            
            self.cursor.execute(query, params or ())
            result = self.cursor.fetchone()
            return result
        except Exception as e:
            logger.error(f"AI DB query failed: {e}")
            return None

# Global database instance
ai_db = AIDatabase()
