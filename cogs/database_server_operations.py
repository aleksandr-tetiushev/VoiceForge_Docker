from typing import Optional
import sqlite3
import discord
from pydantic import BaseModel, ConfigDict
from dotenv import load_dotenv
import os
from logger import log_error , log_info
import traceback

load_dotenv()
DB_NAME=os.getenv("SERVER_DB_NAME") 

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
        exception_traceback = traceback.format_exc()
        error_name = type(e).__name__
        log_error(message=f"Location : init_database - file : database_server_operations.py : Error Name - {error_name}",exc_info=exception_traceback)
        return False
    
    finally:
        if conn:
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
    if not server.server_id or not server.creator_channel_id or not server.category_id:
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
        exception_traceback = traceback.format_exc()
        error_name = type(e).__name__
        log_error(message=f"Location : write_server - file : database_server_operations.py : Error Name - {error_name}",exc_info=exception_traceback)
        return False
    
    except sqlite3.Error as e:
        exception_traceback = traceback.format_exc()
        error_name = type(e).__name__
        log_error(message=f"Location : write_server - file : database_server_operations.py : Error Name - {error_name}",exc_info=exception_traceback)
        return False
    
    finally:
        if conn:
            conn.close()

def read_server(server_id: int,db_name: str = DB_NAME) -> Server | None:
    """
    READ: Fetch server data from database by server_id
    
    Args:
        server_id: Discord guild ID
        db_name: Database file name
    
    Returns:
        Server object if found, None otherwise
    """
    
    conn: sqlite3.Connection | None = None
    
    try:
        conn = sqlite3.connect(db_name)
        conn.row_factory = sqlite3.Row
        cursor: sqlite3.Cursor = conn.cursor()
        
        cursor.execute("""
            SELECT server_id, category_id, creator_channel_id
            FROM servers
            WHERE server_id = ?
        """, (server_id,))
        
        row = cursor.fetchone()
        
        if row:
            server: Server = Server(**dict(row))
            return server
        else:
            return None
    
    except sqlite3.Error as e:
        exception_traceback = traceback.format_exc()
        error_name = type(e).__name__
        log_error(message=f"Location : read_server - file : database_server_operations.py : Error Name - {error_name}",exc_info=exception_traceback)
        return None
    
    finally:
        if conn:
            conn.close()

def read_all_servers(db_name: str = DB_NAME) -> list[Server]:
    """
    READ: Fetch all servers from database
    
    Args:
        db_name: Database file name
    
    Returns:
        List of Server objects
    """
    conn: sqlite3.Connection | None = None
    
    try:
        conn = sqlite3.connect(db_name)
        conn.row_factory = sqlite3.Row
        cursor: sqlite3.Cursor = conn.cursor()
        
        cursor.execute("""
            SELECT server_id, category_id, creator_channel_id
            FROM servers
        """)
        
        rows = cursor.fetchall()
        servers: list[Server] = [Server(**dict(row)) for row in rows]
        
        return servers
    
    except sqlite3.Error as e:
        exception_traceback = traceback.format_exc()
        error_name = type(e).__name__
        log_error(message=f"Location : read_all_server - file : database_server_operations.py : Error Name - {error_name}",exc_info=exception_traceback)
        return []
    
    finally:
        if conn:
            conn.close()

def edit_server(server_id: int,updates: dict,db_name: str = DB_NAME) -> bool:
    
    """
    EDIT: Update existing server data in database
    
    Args:
        server_id: Discord guild ID to update
        updates: Dictionary with fields to update
                 Example: {"category_id": 123, "creator_channel_id": 456}
        db_name: Database file name
    
    Returns:
        True if successful, False otherwise
    """
    if not updates:
        return False
    
    conn: sqlite3.Connection | None = None
    
    try:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        # Build dynamic UPDATE query
        set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
        values = list(updates.values()) + [server_id]
        
        query = f"UPDATE servers SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE server_id = ?"
        
        cursor.execute(query, values)
        conn.commit()
        
        return cursor.rowcount > 0
    
    except sqlite3.Error as e:
        exception_traceback = traceback.format_exc()
        error_name = type(e).__name__
        log_error(message=f"Location : edit_server - file : database_server_operations.py : Error Name - {error_name}",exc_info=exception_traceback)
        return False

    finally:
        if conn:
            conn.close()
 
def delete_server(server_id: int,db_name: str = DB_NAME) -> bool:

    """
    DELETE: Remove server from database
    
    Args:
        server_id: Discord guild ID to delete
        db_name: Database file name
    
    Returns:
        True if successful, False otherwise
    """

    
    conn: sqlite3.Connection | None = None
    
    try:
        
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM servers WHERE server_id = ?", (server_id,))
        conn.commit()
        
        return cursor.rowcount > 0
        
    except sqlite3.Error as e:
        exception_traceback = traceback.format_exc()
        error_name = type(e).__name__
        log_error(message=f"Location : delete_server - file : database_server_operations.py : Error Name - {error_name}",exc_info=exception_traceback)
        return False
    
    finally:
        if conn:
            conn.close()

def get_server_object(channel: discord.VoiceChannel) -> Server | None:
    """
    Extracts server configuration data from a Discord VoiceChannel object.

    This function builds a Server model using the provided VoiceChannel,
    removing dependency on Interaction context.

    Args:
        channel (discord.VoiceChannel): The voice channel used as the creator channel.

    Returns:
        db_server.Server | None:
            Server object containing server_id, category_id, and creator_channel_id
            if valid data is present, otherwise None.

    Notes:
        - Requires channel to belong to a guild.
        - Requires channel to have a valid category.
        - Used as a base builder for server registration flow.
    """
    try:
        guild = channel.guild

        if not guild:
            return None

        server_id = guild.id
        category_id = channel.category_id
        creator_channel_id = channel.id

        if not category_id:
            return None

        return Server(server_id=server_id,category_id=category_id,creator_channel_id=creator_channel_id)

    except Exception as e:
        exception_traceback = traceback.format_exc()
        error_name = type(e).__name__
        log_error(message=f"Location : get_server_object - file : database_server_operations.py : Error Name - {error_name}",exc_info=exception_traceback)
        return None