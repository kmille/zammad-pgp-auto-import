import logging
import os
import sys
import importlib


def get_version() -> str:
    try:
        return importlib.metadata.version(__package__)
    except importlib.metadata.PackageNotFoundError:
        return 'development'


def load_envs() -> list:
    envs = []
    required_envs = ["ZAMMAD_BASE_URL", "ZAMMAD_TOKEN", "BASIC_AUTH_USER", "BASIC_AUTH_PASSWORD"]
    for required_env in required_envs:
        if required_env not in os.environ:
            logging.fatal(f"Required environment variable not set: {required_env}")
            logging.fatal("Here you will find some docs: https://github.com/kmille/zammad-pgp-auto-import")
            sys.exit(1)
        else:
            envs.append(os.environ[required_env])
    LISTEN_HOST = os.environ.get("LISTEN_HOST", "127.0.0.1")
    LISTEN_PORT = int(os.environ.get("LISTEN_PORT", "22000"))
    DEBUG = os.environ.get("DEBUG", "0")
    return [*envs, LISTEN_HOST, LISTEN_PORT, DEBUG]
