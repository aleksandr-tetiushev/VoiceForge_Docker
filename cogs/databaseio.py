from . import database_server_operations as db_server
import discord 
from logger import log_error , log_info
import traceback

def validate_data_dict(data: dict) -> bool:
    """Validate data dictionary has only allowed keys and isn't empty"""
    
    allowed_keys: set[str] = {"server_id", "category_id", "creator_channel_id"}
    
    if not isinstance(data, dict):
        return False
    
    if len(data) == 0:
        return False
    
    # Check: all provided keys are in allowed list
    if not set(data.keys()).issubset(allowed_keys):
        return False
    
    return True

def server_write(channel: discord.VoiceChannel) -> bool:
    """
    Writes server configuration into the database using a VoiceChannel.

    This function converts the given VoiceChannel into a Server object
    and persists it in the database.

    Args:
        channel (discord.VoiceChannel): Creator voice channel used for registration.

    Returns:
        bool:
            True if server was successfully written to database,
            False if validation fails or database operation fails.

    Notes:
        - Internally calls get_server_object() to build Server model.
        - Logs database or runtime errors via logging system.
        - Returns False for both validation failure and DB failure cases.
    """
    try:
        server: db_server.Server | None = db_server.get_server_object(channel=channel)

        if server is None:
            return False

        return db_server.write_server(server)

    except Exception as e:
        exception_traceback = traceback.format_exc()
        error_name = type(e).__name__
        log_error(message=f"Location : server_write - file : databaseio.py : Error Name - {error_name}",exc_info=exception_traceback)
        return False

def server_read(interaction: discord.Interaction) -> tuple[db_server.Server | None, bool]:
    try:
        server_id: int = interaction.guild_id
        server_object: db_server.Server | None = db_server.read_server(server_id)

        if server_object is None:
            return None, False

        return server_object, True

    except Exception as e:
        exception_traceback = traceback.format_exc()
        error_name = type(e).__name__
        log_error(message=f"Location : server_read - file : databaseio.py : Error Name - {error_name}",exc_info=exception_traceback)
        return None, False
    
def server_edit(interaction:discord.Interaction,data:dict)->bool:
    try:
        server_id:int = interaction.guild_id
        
        if not validate_data_dict(data=data):
            return False
        
        edit_status:bool = db_server.edit_server(server_id=server_id,updates=data)

        if not edit_status:
            log_error(message=f"Location : server_edit - file : databaseio.py : Error Name - Database edit operation Failed.")
            return False
        
        return edit_status
    
    except Exception as e:
        exception_traceback = traceback.format_exc()
        error_name = type(e).__name__
        log_error(message=f"Location : server_edit - file : databaseio.py : Error Name - {error_name}",exc_info=exception_traceback)
        return False
    
def server_delete(interaction:discord.Interaction)->bool:
    """
    Delete server configuration from database
    
    Args:
        interaction: Discord interaction object
    
    Returns:
        True if successfully deleted, False otherwise
    """
    try:
        server_id:int = interaction.guild_id

        delete_status:bool = db_server.delete_server(server_id=server_id)
        
        if not delete_status:
            log_error(message=f"Location : server_delete - file : databaseio.py : Error Name - Database delete operation Failed.")
        
        return delete_status
    
    except Exception as e:
        exception_traceback = traceback.format_exc()
        error_name = type(e).__name__
        log_error(message=f"Location : server_delete - file : databaseio.py : Error Name - {error_name}",exc_info=exception_traceback)
        return False