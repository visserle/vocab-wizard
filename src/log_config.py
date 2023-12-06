import logging

def configure_logging(stream_lvl=logging.INFO, ignore_libs=None):
    """
    Configures the root logger for logging messages to the console.
    Supports ignoring logs from specified libraries.

    Parameters:
    - stream_lvl: The logging level for the stream handler.
    - ignore_libs: A list of library names whose logs should be ignored.
    """
    # Clear any previously added handlers from the root logger
    logging.getLogger().handlers = []

    # StreamHandler for console logging
    stream_formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] [%(name)s] - %(message)s', datefmt='%H:%M:%S')
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(stream_lvl)
    stream_handler.setFormatter(stream_formatter)

    # Create filter for ignoring logs from specified libraries
    def create_filter(ignored_libs):
        def ignore_logs(record):
            return not any(record.name.startswith(lib) for lib in ignored_libs)
        return ignore_logs
    
    if ignore_libs:
        ignore_filter = create_filter(ignore_libs)
        stream_handler.addFilter(ignore_filter)

    # Set up the root logger configuration with the StreamHandler
    logging.basicConfig(level=stream_lvl, handlers=[stream_handler])
