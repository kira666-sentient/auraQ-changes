"""
Database Migration Script for AuraQ

This script updates the SQLite database schema to add new columns
to the users table without losing existing data.
"""

import os
import sqlite3
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join('logs', 'db_migration.log'))
    ]
)

logger = logging.getLogger('db_migration')

# Database path
DB_PATH = Path(os.path.dirname(__file__)) / "instance" / "aura_detector.db"

def migrate_database():
    """Update database schema to latest version"""
    
    if not DB_PATH.exists():
        logger.error(f"Database not found at {DB_PATH}")
        return False
    
    try:
        # Connect to the database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get current columns in users table
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        logger.info(f"Current columns in users table: {columns}")
        
        # Add missing columns
        columns_to_add = {
            'last_login': 'TIMESTAMP',
            'login_count': 'INTEGER DEFAULT 0',
            'is_active': 'BOOLEAN DEFAULT 1',
            'is_verified': 'BOOLEAN DEFAULT 0',
            'api_key': 'VARCHAR(64)'
        }
        
        for column_name, column_type in columns_to_add.items():
            if column_name not in columns:
                sql = f"ALTER TABLE users ADD COLUMN {column_name} {column_type}"
                logger.info(f"Adding column: {sql}")
                cursor.execute(sql)
                logger.info(f"Added {column_name} column to users table")
            else:
                logger.info(f"Column {column_name} already exists in users table")
        
        # Commit changes
        conn.commit()
        
        # Verify schema update
        cursor.execute("PRAGMA table_info(users)")
        new_columns = [column[1] for column in cursor.fetchall()]
        
        logger.info(f"Updated columns in users table: {new_columns}")
        
        # Check if all required columns exist
        missing_columns = [col for col in columns_to_add.keys() if col not in new_columns]
        
        if missing_columns:
            logger.error(f"Failed to add columns: {missing_columns}")
            return False
            
        logger.info("Database schema updated successfully")
        
        # Get user count to verify database is still valid
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        logger.info(f"Database contains {user_count} users")
        
        return True
        
    except sqlite3.Error as e:
        logger.error(f"SQLite error: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("\n===== AuraQ Database Migration Tool =====\n")
    
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Run migration
    success = migrate_database()
    
    if success:
        print("\n✅ Database migration completed successfully!")
        print("You can now start the application normally.\n")
    else:
        print("\n❌ Database migration failed. See logs/db_migration.log for details.\n")