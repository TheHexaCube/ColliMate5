import logging
from colorama import Fore, Style, init as colorama_init

# Global logging configuration
GLOBAL_LOG_LEVEL = logging.INFO  # Default global level
GLOBAL_HANDLERS = []  # Store global handlers

def set_global_log_level(level):
    """Set the global logging level for all loggers"""
    global GLOBAL_LOG_LEVEL
    GLOBAL_LOG_LEVEL = level
    
    # Update all existing loggers
    for logger_name in logging.Logger.manager.loggerDict:
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)  # Always override with global level

def set_global_log_level_by_name(level_name):
    """Set global log level by name (DEBUG, INFO, WARNING, ERROR, CRITICAL)"""
    level_map = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    level = level_map.get(level_name.upper(), logging.INFO)
    set_global_log_level(level)

def configure_global_logging(level=logging.INFO, format_string=None, handlers=None):
    """Configure global logging settings that will be applied to all loggers"""
    global GLOBAL_LOG_LEVEL, GLOBAL_HANDLERS
    
    GLOBAL_LOG_LEVEL = level
    
    # Set root logger level
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Clear existing handlers if specified
    if handlers is not None:
        root_logger.handlers.clear()
        GLOBAL_HANDLERS = handlers
        for handler in handlers:
            root_logger.addHandler(handler)
    
    # Apply to all existing loggers
    for logger_name in logging.Logger.manager.loggerDict:
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)
        if handlers is not None:
            logger.handlers.clear()
            for handler in handlers:
                logger.addHandler(handler)

class ColorFormatter(logging.Formatter):
    LEVEL_COLORS = {
        logging.DEBUG: Fore.CYAN,
        logging.INFO: Fore.GREEN,
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED,
        logging.CRITICAL: Fore.MAGENTA + Style.BRIGHT,
    }

    def format(self, record):
        color = self.LEVEL_COLORS.get(record.levelno, "")
        reset = Style.RESET_ALL
        msg = super().format(record)
        return f"{color}{msg}{reset}"

class Logger:
    def __init__(self, name=None, use_global_config=True):
        colorama_init(autoreset=True)
        if name is None:
            # Get the name of the module that instantiated this Logger
            import inspect
            frame = inspect.currentframe().f_back
            name = frame.f_globals.get('__name__', 'unknown')
        
        self.logger = logging.getLogger(name)
        
        # Use global configuration if enabled
        if use_global_config:
            self.logger.setLevel(GLOBAL_LOG_LEVEL)
            # If global handlers are configured, use them instead of creating new ones
            if GLOBAL_HANDLERS:
                self.logger.handlers.clear()
                for handler in GLOBAL_HANDLERS:
                    self.logger.addHandler(handler)
                return  # Skip individual handler setup
        
        # Individual handler setup (when not using global config)
        self.logger.setLevel(logging.INFO)
        self.console_handler = logging.StreamHandler()
        #self.console_handler.setLevel(logging.INFO)  # Explicitly set handler level
        self.formatter = ColorFormatter(
            '[%(asctime)s] - [%(name)s] - [%(levelname)s] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.console_handler.setFormatter(self.formatter)
        # Ensure no duplicate handlers
        if not self.logger.hasHandlers():
            self.logger.addHandler(self.console_handler)
        else:
            # Remove all existing handlers and add only the custom one
            for handler in self.logger.handlers[:]:  # Use slice copy to avoid modification during iteration
                self.logger.removeHandler(handler)
            self.logger.addHandler(self.console_handler)

    def debug(self, msg, *args, **kwargs):
        self.logger.debug(msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self.logger.info(msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self.logger.warning(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self.logger.error(msg, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        self.logger.critical(msg, *args, **kwargs)

