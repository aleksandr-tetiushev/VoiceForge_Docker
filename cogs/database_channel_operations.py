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

def channel_write(channel: Channel, db_name: str = DB_NAME) -> bool:
    """
    WRITE: Insert channel data in database
    
    Args:
        channel: Channel pydantic model instance
        db_name: Database file name
    
    Returns:
        bool: True if successful, False otherwise
    """
    if not channel.server_id or not channel.channel_id or not channel.owner_id:
        return False
    
    conn: sqlite3.Connection | None = None
    try:
        conn = sqlite3.connect(db_name)
        cursor: sqlite3.Cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO serversChannels (server_id, owner_id, category_id, channel_id)
            VALUES (?, ?, ?, ?)
        """, (channel.server_id, channel.owner_id, channel.category_id, channel.channel_id))
        
        conn.commit()
        return True
    
    except sqlite3.Error as e:
        exception_traceback: str = traceback.format_exc()
        error_name: str = type(e).__name__
        log_error(message=f"Location : channel_write - file : database_channel_operations.py : Error Name - {error_name}",exc_info=exception_traceback)
        return False
    
    finally:
        if conn:
            conn.close()

def channel_read(server_id: int, channel_id: int, db_name: str = DB_NAME) -> Channel | None:
    """
    READ: Fetch channel data from database by server_id and channel_id
    
    Args:
        server_id: Discord guild ID
        channel_id: Discord channel ID
        db_name: Database file name
    
    Returns:
        Channel object if found, None otherwise
    """
    conn: sqlite3.Connection | None = None
    
    try:
        conn = sqlite3.connect(db_name)
        conn.row_factory = sqlite3.Row
        cursor: sqlite3.Cursor = conn.cursor()
        
        # Query by BOTH server_id AND channel_id
        cursor.execute("""
            SELECT server_id, owner_id, category_id, channel_id
            FROM serversChannels
            WHERE server_id = ? AND channel_id = ?
        """, (server_id, channel_id))
        
        row = cursor.fetchone()
        
        if row:
            channel: Channel = Channel(**dict(row))
            return channel
        else:
            return None

    except sqlite3.Error as e:
        exception_traceback: str = traceback.format_exc()
        error_name: str = type(e).__name__
        log_error(message=f"Location : channel_read - file : database_channel_operations.py : Error Name - {error_name}",exc_info=exception_traceback)
        return None
    
    finally:
        if conn:
            conn.close()

def channel_edit(server_id: int,channel_id: int,new_owner_id: int,db_name: str = DB_NAME) -> bool:
    """
    EDIT: Update channel owner in database
    
    Args:
        server_id: Discord guild ID
        channel_id: Discord channel ID
        new_owner_id: New owner ID to set
        db_name: Database file name
    
    Returns:
        True if successful, False otherwise
    """
    conn: sqlite3.Connection | None = None
    
    try:
        conn = sqlite3.connect(db_name)
        cursor: sqlite3.Cursor = conn.cursor()
        
        # Update owner_id where server_id AND channel_id match
        query: str = """
            UPDATE serversChannels 
            SET owner_id = ?, updated_at = CURRENT_TIMESTAMP 
            WHERE server_id = ? AND channel_id = ?
        """
        
        values: tuple = (new_owner_id, server_id, channel_id)
        
        cursor.execute(query, values)
        conn.commit()
        
        # Return True if any rows were updated
        return cursor.rowcount > 0
    
    except sqlite3.Error as e:
        exception_traceback: str = traceback.format_exc()
        error_name: str = type(e).__name__
        log_error(message=f"Location : channel_edit - file : database_channel_operations.py : Error Name - {error_name}",exc_info=exception_traceback)
        return False

    finally:
        if conn:
            conn.close()