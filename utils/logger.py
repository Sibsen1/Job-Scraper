import logging


def _makeLogger(fn):
    def wrapper(*args):
        msg = " ".join(str(x) for x in args)
        try:
            fn(msg)
        except UnicodeEncodeError:
            fn(msg.encode("cp1252", "replace").decode("cp1252"))
    return wrapper


logDebug = _makeLogger(logging.debug)
logInfo = _makeLogger(logging.info)
logWarning = _makeLogger(logging.warning)
logError = _makeLogger(logging.error)
logCritical = _makeLogger(logging.critical)


def setupLogger():
    fmt = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    h = logging.StreamHandler()
    f = logging.FileHandler("app.log", mode="a", encoding="utf-8")
    h.setFormatter(fmt)
    f.setFormatter(fmt)

    logging.basicConfig(level=logging.INFO, handlers=[h,f])