import pyodbc
# import logging
import configparser
from logger_config import logger  # Import centralized logger

# # Configure Logging
# logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
# logger = logging.getLogger(__name__)

# ✅ Load database configuration from config.inf
config = configparser.ConfigParser()
config.read("config.inf")

db_config = {
    "server": config.get("DATABASE", "SERVER"),
    "database": config.get("DATABASE", "DATABASE"),
    "username": config.get("DATABASE", "USERNAME"),
    "password": config.get("DATABASE", "PASSWORD"),
    "options": config.get("DATABASE", "OPTIONS"),
}

# New DB config from [DATABASE-NEW-DB]
new_db_config = {
    "server": config.get("DATABASE-NEW-DB", "SERVER"),
    "database": config.get("DATABASE-NEW-DB", "DATABASE"),
    "username": config.get("DATABASE-NEW-DB", "USERNAME"),
    "password": config.get("DATABASE-NEW-DB", "PASSWORD"),
    "options": config.get("DATABASE-NEW-DB", "OPTIONS"),
}

# Global connection object
# _db_connection = None

def get_db_connection():
    """Establish a new database connection when required."""
    try:
        logger.info("Creating a new database connection.")
        return pyodbc.connect(
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={db_config['server']};"
            f"DATABASE={db_config['database']};"
            f"UID={db_config['username']};"
            f"PWD={db_config['password']};"
            f";{db_config['options']}"
        )
    except pyodbc.Error as e:
        logger.error(f"ODBC Error: {e.args[0]}, {e.args[1]}")
    except Exception as e:
        logger.error(f"General Error: {str(e)}")
    return None

def get_new_db_connection():
    """Establish a new connection to the secondary database."""
    try:
        logger.info("Creating a new connection to the NEW database.")
        return pyodbc.connect(
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={new_db_config['server']};"
            f"DATABASE={new_db_config['database']};"
            f"UID={new_db_config['username']};"
            f"PWD={new_db_config['password']};"
            f";{new_db_config['options']}"
        )
    except pyodbc.Error as e:
        logger.error(f"ODBC Error (NEW DB): {e.args[0]}, {e.args[1]}")
    except Exception as e:
        logger.error(f"General Error (NEW DB): {str(e)}")
    return None


def close_db_connection():
    """Close the shared database connection."""
    global _db_connection
    if _db_connection:
        _db_connection.close()
        logger.info("Database connection closed.")
        _db_connection = None

