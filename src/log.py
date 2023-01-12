import sys

class Logger:
    def __init__(self, id):
        self.id = id

    def _log(self, type, str):
        print("%s %s: %s" % (type, self.id, str))

    def trace(self, *args):
        self._log("TRACE", *args)

    def info(self, *args):
        self._log("INFO", *args)

    def warn(self, *args):
        self._log("WARN", *args)

    def error(self, *args):
        self._log("ERROR", *args)

    def safe(self, message):
        return Safe(self, message)


class Safe:
    def __init__(self, logger, message):
        self.logger = logger
        self.message = message

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc, tb):
        if exc_type is not None:
            print("EXCEPTION %s: %s" % (self.logger.id, self.message))
            sys.print_exception(exc)
        return True
