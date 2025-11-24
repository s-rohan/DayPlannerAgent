import logging
import os

# Logging configuration
LOG_FILE = os.path.join(os.getcwd(), "logger.log")
LOG_LEVEL = logging.DEBUG
FORMAT = "%(asctime)s %(name)s %(levelname)s %(message)s"
STREAM_HANDLER_CONSOLE = True


def configure_logging():
    """Idempotently configure root logging to write to a file and console.

    This function can be imported safely multiple times. It will not remove
    existing handlers or truncate existing logs; instead it ensures a file
    handler writing to LOG_FILE exists so log records from all modules are
    captured.
    """
    root = logging.getLogger()
    root.setLevel(LOG_LEVEL)

    # Add a FileHandler if one writing to LOG_FILE isn't present yet
    file_handler_exists = False
    for h in list(root.handlers):
        try:
            if isinstance(h, logging.FileHandler) and os.path.abspath(getattr(h, 'baseFilename', '')) == os.path.abspath(LOG_FILE):
                file_handler_exists = True
                break
        except Exception:
            # Some handlers may not have baseFilename attribute
            continue

    if not file_handler_exists:
        fh = logging.FileHandler(LOG_FILE, mode='a', encoding='utf-8')
        fh.setLevel(LOG_LEVEL)
        fh.setFormatter(logging.Formatter(FORMAT))
        root.addHandler(fh)

    # Ensure there's at least one console handler (StreamHandler) for interactive runs
    stream_exists = any(isinstance(h, logging.StreamHandler) for h in root.handlers)
    if not stream_exists:
        sh = logging.StreamHandler()
        sh.setLevel(logging.INFO)
        sh.setFormatter(logging.Formatter(FORMAT))
        root.addHandler(sh)

    # Redirect stdout/stderr to logging so print() output is captured in the logs.
    try:
        import sys

        class StreamToLogger:
            """Fake file-like object that redirects writes to a logger instance."""

            def __init__(self, logger, level=logging.INFO):
                self.logger = logger
                self.level = level

            def write(self, buf):
                for line in buf.rstrip().splitlines():
                    self.logger.log(self.level, line)

            def flush(self):
                pass

        stdout_logger = logging.getLogger('STDOUT')
        stderr_logger = logging.getLogger('STDERR')
        # Only redirect if not already redirected
        if not isinstance(sys.stdout, StreamToLogger) and not STREAM_HANDLER_CONSOLE:
            sys.stdout = StreamToLogger(stdout_logger, logging.INFO)
        if not isinstance(sys.stderr, StreamToLogger) and not STREAM_HANDLER_CONSOLE:
            sys.stderr = StreamToLogger(stderr_logger, logging.ERROR)
    except Exception:
        # If redirection fails, don't crash the import
        root.exception('Failed to redirect stdout/stderr to logging')


# Configure on import; this ensures other modules that import the package
# get a consistent logging setup. Because configure_logging is idempotent,
# repeated imports won't duplicate handlers.
configure_logging()

print("✅ Logging configured (file:", LOG_FILE, ")")
