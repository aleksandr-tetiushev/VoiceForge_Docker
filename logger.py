import logging
import os

folder = "Logs"
os.makedirs(folder, exist_ok=True)

error_logger = logging.getLogger("error_logger")

# Prevent duplicate handlers on multiple imports
if not error_logger.handlers:
    error_handler = logging.FileHandler(os.path.join(folder, "error.log"))
    error_handler.setFormatter(
        logging.Formatter(
            '\n\n%(asctime)s - %(levelname)s - %(message)s\n\n'
        )
    )
    error_logger.addHandler(error_handler)

error_logger.setLevel(logging.INFO)
error_logger.propagate = False  # optional but recommended


def log_error(message: str,exc_info:str|None="No Traceback") -> None:
    error_logger.error(f"{message} - traceback : \n\n{exc_info}")


def log_info(message: str) -> None:
    error_logger.info(message)
