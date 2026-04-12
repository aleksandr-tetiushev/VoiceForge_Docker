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