from .database_operations import *
import discord 


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
            return None,False

        return server_object, True
    
    except Exception as e:
        exception_traceback = traceback.format_exc()
        error_name = type(e).__name__
        log_error(message=f"Location : server_read - file : databaseio.py : Error Name - {error_name}",exc_info=exception_traceback)
        return None,False