import logging
import os
import sys
import configparser
from logging.handlers import RotatingFileHandler

# Step 1: Read config.inf
config = configparser.ConfigParser()
config.read("config.inf")

# Step 2: Get log path and log level from config file
DEFAULT_LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
LOG_DIR = config.get("LOGGING", "LOG_PATH", fallback=DEFAULT_LOG_DIR)  # Default to "logs" folder if not set
LOG_LEVEL = config.get("LOGGING", "LOG_LEVEL", fallback="DEBUG").upper()  # Default log level is DEBUG

# Step 3: Create logs directory if it doesn't exist
os.makedirs(LOG_DIR, exist_ok=True)

# Step 4: Define log file path
LOG_FILE = os.path.join(LOG_DIR, "application.log")

# Step 5: Configure logging
logging.getLogger().handlers.clear()  # Clear existing handlers

#logger = logging.getLogger(__name__)
logger = logging.getLogger("main_logger")
logger.setLevel(getattr(logging, LOG_LEVEL, logging.DEBUG))  # Convert string level to logging constant

# ✅ Remove all existing handlers to prevent duplicate logs
while logger.hasHandlers():
    logger.removeHandler(logger.handlers[0])

# Use RotatingFileHandler (Automatically creates new files when full)**
file_handler = RotatingFileHandler(LOG_FILE, mode="a", maxBytes=5*1024*1024, backupCount=3, encoding="utf-8")
file_handler.setLevel(getattr(logging, LOG_LEVEL, logging.DEBUG))

# Console handler (Logs to terminal)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(getattr(logging, LOG_LEVEL, logging.DEBUG))

# Log format
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Add handlers to logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# ✅ Prevent propagation to root logger (which causes duplicate formats)
logger.propagate = False  # ❌ This was causing duplicate logs

logger.info("✅ Logger initialized  with rotation. Logs will be stored in: %s", LOG_FILE)
