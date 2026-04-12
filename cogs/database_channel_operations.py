from typing import Optional
import sqlite3
import discord
from pydantic import BaseModel, ConfigDict
from dotenv import load_dotenv
import os
from logger import log_error , log_info
import traceback

load_dotenv()
DB_NAME=os.getenv("CHANNEL_DB_NAME") 

if not DB_NAME:
    DB_NAME = "discord_channel.db"


class Channel(BaseModel):
    model_config = ConfigDict(extra="forbid",  # ← no extra data
        validate_assignment=True,  # ← Keep data valid
        json_schema_extra={  # ← Show example in docs
            "example": {
                "server_id": 123456789,
                "owner_id" : 000000000,
                "category_id": 987654321,
                "channel_id": 111222333
            }
        }
    )

    server_id: int | None = None
    owner_id:int | None = None
    category_id: int | None = None
    channel_id: int | None = None

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
            CREATE TABLE IF NOT EXISTS serversChannels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                server_id INTEGER UNIQUE NOT NULL,
                owner_id INTEGER NOT NULL,
                category_id INTEGER NOT NULL,
                channel_id INTEGER UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        return True
    
    except sqlite3.Error as e:
        exception_traceback = traceback.format_exc()
        error_name = type(e).__name__
        log_error(message=f"Location : init_database - file : database_channel_operations.py : Error Name - {error_name}",exc_info=exception_traceback)
        return False
    
    finally:
        if conn:
            conn.close()