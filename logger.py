# import logging
# import sys

# # Configure the logging settings

# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(levelname)s - %(message)s',   # Define the log message format
#     filename='script_output.log',   # Log messages will be written to this file
#     filemode='a'  # Append log messages to the file
# )

# class StreamToLogger:
#     def __init__(self, level):
#         self.level = level
#         self.buffer = ''

#     # Writes a message to the logger.
#     def write(self, message):
#         message = message.strip()
#         if message:
#             logging.log(self.level, message)
#              # Log the message only if it's not empty

#     def flush(self):
#         # Flush method required for compatibility with sys.stdout and sys.stderr.
#         pass


# # Redirect stdout and stderr to the logger
# sys.stdout = StreamToLogger(logging.INFO)  
# sys.stderr = StreamToLogger(logging.ERROR)


import logging
import sys
import os
import time

# Create a logs folder if it doesn't exist
LOGS_FOLDER = "logs"
os.makedirs(LOGS_FOLDER, exist_ok=True)

# Generate a unique identifier for the log file (e.g., timestamp + PID)
unique_id = f"{time.strftime('%Y%m%d_%H%M%S')}_{os.getpid()}"

# Configure the logging settings
log_file_path = os.path.join(LOGS_FOLDER, f"script_output_{unique_id}.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - PID:%(process)d - %(levelname)s - %(message)s',  # Include PID in log format
    filename=log_file_path,  # Log messages will be written to a unique file
    filemode='a'  # Append log messages to the file
)

class StreamToLogger:
    def __init__(self, level):
        self.level = level
        self.buffer = ''

    # Writes a message to the logger.
    def write(self, message):
        message = message.strip()
        if message:
            logging.log(self.level, message)  # Log the message only if it's not empty

    def flush(self):
        # Flush method required for compatibility with sys.stdout and sys.stderr.
        pass


# Redirect stdout and stderr to the logger
sys.stdout = StreamToLogger(logging.INFO)
sys.stderr = StreamToLogger(logging.ERROR)