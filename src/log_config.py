import logging

def configure_logging(stream_level=logging.INFO, ignore_libs=None):
    """
    Configures the root logger for logging messages to the console.
    Supports ignoring logs from specified libraries.

    Parameters:
    - stream_level: The logging level for the stream handler.
    - ignore_libs: A list of library names whose logs should be ignored.
    """
    # Clear any previously added handlers from the root logger
    logging.getLogger().handlers = []

    # StreamHandler for console logging
    stream_formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] [%(name)s] - %(message)s', datefmt='%H:%M:%S')
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(stream_level)
    stream_handler.setFormatter(stream_formatter)

    # Function to create a filter for ignoring logs from specified libraries
    def create_ignore_filter(ignored_libs):
        def ignore_logs(record):
            return not any(record.name.startswith(lib) for lib in ignored_libs)
        return ignore_logs
    
    # Apply ignore filter if ignore_libs is provided
    if ignore_libs:
        ignore_filter = create_ignore_filter(ignore_libs)
        stream_handler.addFilter(ignore_filter)

    # Set up the root logger configuration with the StreamHandler
    logging.basicConfig(level=stream_level, handlers=[stream_handler])
