from .database_operations import *
import discord 


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

def server_write(interaction:discord.Interaction)->bool:
    try:
        server:Server | None = get_server_object(interaction=interaction)

        if not isinstance(server,Server):
            return False

        write_status = write_server(server)
        
        if not write_status:
            log_error(message=f"Location : server_write - file : databaseio.py : Error Name - Database write operation Failed.")

        return write_status

    except Exception as e:
        exception_traceback = traceback.format_exc()
        error_name = type(e).__name__
        log_error(message=f"Location : server_write - file : databaseio.py : Error Name - {error_name}",exc_info=exception_traceback)
        return False

def server_read(interaction:discord.Interaction)->tuple[Server|None,bool]:
    try:
        server_id:int = interaction.guild_id
        server_object:Server | None = read_server(server_id)

        if not isinstance(server_object,Server):
            log_error(message=f"Location : server_read - file : databaseio.py : Error Name - Database read operation Failed.")
            return None,False

        return server_object, True
    
    except Exception as e:
        exception_traceback = traceback.format_exc()
        error_name = type(e).__name__
        log_error(message=f"Location : server_read - file : databaseio.py : Error Name - {error_name}",exc_info=exception_traceback)
        return None,False
    
def server_edit(interaction:discord.Interaction,data:dict)->bool:
    try:
        server_id:int = interaction.guild_id
        
        if not validate_data_dict(data=data):
            return False
        
        edit_status:bool = edit_server(server_id=server_id,updates=data)

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

        delete_status:bool = delete_server(server_id=server_id)
        
        if not delete_status:
            log_error(message=f"Location : server_delete - file : databaseio.py : Error Name - Database delete operation Failed.")
        
        return delete_status
    
    except Exception as e:
        exception_traceback = traceback.format_exc()
        error_name = type(e).__name__
        log_error(message=f"Location : server_delete - file : databaseio.py : Error Name - {error_name}",exc_info=exception_traceback)
        return False