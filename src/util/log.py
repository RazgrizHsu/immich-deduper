import logging
import logging.handlers
import sys
import os
from typing import Any, Optional

EnableLogFile = True
LogLevel = logging.INFO
KeepDays = 3

log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'logs')
os.makedirs(log_dir, exist_ok=True)

log_file = os.path.join(log_dir, 'deduper.log')

class filterLv(logging.Filter):
    def filter(self, record):
        if record.levelname == 'WARNING': record.levelname = 'WARN'
        if record.levelname == 'ERROR': record.levelname = 'ERRO'
        return True

def setup(level=LogLevel, enableFile=EnableLogFile):

    fmtC = logging.Formatter(
        fmt='%(asctime)s.%(msecs)03d|%(levelname)s| %(message)s',
        datefmt='%H:%M:%S'
    )
    fmtF = logging.Formatter(
        fmt='%(asctime)s.%(msecs)03d|%(levelname)s|%(name)s| %(message)s',
        datefmt='%H:%M:%S'
    )

    hndC = logging.StreamHandler(sys.stdout)
    hndC.setLevel(level)
    hndC.setFormatter(fmtC)

    rlg = logging.getLogger()
    rlg.setLevel(level)

    for handler in rlg.handlers[:]: rlg.removeHandler(handler)
    rlg.addHandler(hndC)

    if enableFile:
        hndF = logging.handlers.TimedRotatingFileHandler(
            log_file,
            when='midnight',
            interval=1,
            backupCount=KeepDays
        )
        hndF.setLevel(level)
        hndF.setFormatter(fmtF)
        rlg.addHandler(hndF)

    for handler in rlg.handlers: handler.addFilter(filterLv())

    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('flask').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)

    return rlg


setup()

class LoggerAdapter:
    def __init__(self, logger: logging.Logger):
        self._logger = logger

    def debug(self, msg: Any, *args: Any, exc_info: Optional[Any] = None,
              extra: Optional[dict] = None, stack_info: bool = False,
              stacklevel: int = 1, **kwargs) -> None:
        self._logger.debug(msg, *args, exc_info=exc_info, extra=extra, stack_info=stack_info, stacklevel=stacklevel, **kwargs)

    def info(self, msg: Any, *args: Any, exc_info: Optional[Any] = None,
             extra: Optional[dict] = None, stack_info: bool = False,
             stacklevel: int = 1, **kwargs) -> None:
        self._logger.info(msg, *args, exc_info=exc_info, extra=extra, stack_info=stack_info, stacklevel=stacklevel, **kwargs)

    def warn(self, msg: Any, *args: Any, exc_info: Optional[Any] = None,
             extra: Optional[dict] = None, stack_info: bool = False,
             stacklevel: int = 1, **kwargs) -> None:
        self._logger.warning(msg, *args, exc_info=exc_info, extra=extra, stack_info=stack_info, stacklevel=stacklevel, **kwargs)

    def error(self, msg: Any, *args: Any, exc_info: Optional[Any] = None,
              extra: Optional[dict] = None, stack_info: bool = False,
              stacklevel: int = 1, **kwargs) -> None:
        self._logger.error(msg, *args, exc_info=exc_info, extra=extra, stack_info=stack_info, stacklevel=stacklevel, **kwargs)

    def exception(self, msg: Any, *args: Any, exc_info: Optional[Any] = None,
                  extra: Optional[dict] = None, stack_info: bool = False,
                  stacklevel: int = 1, **kwargs) -> None:
        self._logger.exception(msg, *args, exc_info=exc_info, extra=extra, stack_info=stack_info, stacklevel=stacklevel, **kwargs)

    def critical(self, msg: Any, *args: Any, exc_info: Optional[Any] = None,
                 extra: Optional[dict] = None, stack_info: bool = False,
                 stacklevel: int = 1, **kwargs) -> None:
        self._logger.critical(msg, *args, exc_info=exc_info, extra=extra, stack_info=stack_info, stacklevel=stacklevel, **kwargs)

    def fatal(self, msg: Any, *args: Any, exc_info: Optional[Any] = None,
              extra: Optional[dict] = None, stack_info: bool = False,
              stacklevel: int = 1, **kwargs) -> None:
        self._logger.fatal(msg, *args, exc_info=exc_info, extra=extra, stack_info=stack_info, stacklevel=stacklevel, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._logger, name)

def get(name: str) -> LoggerAdapter:
    return LoggerAdapter(logging.getLogger(name))
