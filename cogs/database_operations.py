from typing import Optional
import sqlite3
import discord
from pydantic import BaseModel, ConfigDict
from dotenv import load_dotenv
import os

load_dotenv()
DB_NAME=os.getenv("DB_NAME") 

if not DB_NAME:
    DB_NAME = "discord_server.db"

class Server(BaseModel):
    model_config = ConfigDict(
        extra="forbid",  # ← no extra data
        validate_assignment=True,  # ← Keep data valid
        json_schema_extra={  # ← Show example in docs
            "example": {
                "server_id": 123456789,
                "category_id": 987654321,
                "creator_channel_id": 111222333
            }
        }
    )
    
    server_id: int | None = None
    category_id: int | None = None
    creator_channel_id: int | None = None


def init_database(db_name: str = DB_NAME) -> bool:
    """
    Initialize SQLite database and create servers table
    
    Args:
        db_name: Name of the database file
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        conn: sqlite3.Connection = sqlite3.connect(db_name)
        cursor: sqlite3.Cursor = conn.cursor()
 
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS servers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                server_id INTEGER UNIQUE NOT NULL,
                category_id INTEGER NOT NULL,
                creator_channel_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        return True
    
    except sqlite3.Error as e:
        return False
    
    finally:
        conn.close()


def write_server(server: Server,db_name: str = DB_NAME) -> bool:
    """
    WRITE: Insert server data in database
    
    Args:
        server: Server pydantic model instance
        db_name: Database file name
    
    Returns:
        bool: True if successful, False otherwise
    """
    # Validation
    if not server.server_id or not server.creator_channel_id:
        return False
    
    conn: sqlite3.Connection | None = None
    try:
        conn = sqlite3.connect(db_name)
        cursor: sqlite3.Cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO servers (server_id, category_id, creator_channel_id)
            VALUES (?, ?, ?)
        """, (server.server_id, server.category_id, server.creator_channel_id))
        
        conn.commit()
        return True
    
    except sqlite3.IntegrityError as e:
        return False
    
    except sqlite3.Error as e:
        return False
    
    finally:
        if conn:
            conn.close()



