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
