import os
import logging


def setup_logger():
    current_file_dir = os.path.dirname(os.path.abspath(__file__))

    logger = logging.getLogger('printer')
    logger.setLevel(logging.DEBUG)  # Set the log level

    os.makedirs(current_file_dir +'/logs', exist_ok=True)

    # Create handlers
    f_handler = logging.FileHandler(current_file_dir +'/logs/printer.log')
    f_handler.setLevel(logging.DEBUG)  # Set the log level for the file handler

    c_handler = logging.StreamHandler()
    c_handler.setLevel(logging.DEBUG)  # Set the minimum log level for the console handler

    # Create formatters and add it to handlers
    f_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s | %(message)s')
    f_handler.setFormatter(f_format)

    c_format = logging.Formatter('%(message)s')
    c_handler.setFormatter(c_format)

    # Add handlers to the logger
    logger.addHandler(f_handler)
    logger.addHandler(c_handler)

    # Now, you can write to the log using the custom logger
    logger.debug('Logging Initialized')

    return logging.getLogger('printer')
