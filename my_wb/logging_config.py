from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ENV = "dev"

LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,

    "formatters": {
        "simple": {
            "format": "[{asctime}] [{threadName}] {levelname} {name}.{funcName}[{lineno}] - {message}",
            "style": "{",
        },
    },

    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "formatter": "simple",
        },
        # "file": {
        #     "class": "logging.handlers.TimedRotatingFileHandler",
        #     "filename": LOG_DIR / "django.log",
        #     "when": "midnight",
        #     "backupCount": 7,
        #     "encoding": "utf-8",
        #     "formatter": "simple",
        # },
        "file": {
            "class": "concurrent_log_handler.ConcurrentRotatingFileHandler",
            "filename": str(LOG_DIR / "django.log"),
            "maxBytes": 20 * 1024 * 1024,  # 20MB 切割
            "backupCount": 7,
            "encoding": "utf-8",
            "formatter": "simple",
        },
    },

    "root": {
        "handlers": ["console","file"] if ENV == "dev" else ["file"],
        "level": "INFO",
    },
}
