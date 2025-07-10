import importlib
import subprocess
import logging
import re
import os
import sys


def get_version():
    try:
        return importlib.metadata.version(__package__)
    except importlib.metadata.PackageNotFoundError:
        return 'development'


def get_pgp_key_from_file():
    gpg = gnupg.GPG(gnupghome='/home/kmille/tmp/gpg-test')

    t = Path(__file__).parent / ".." / ".." / "tests" / "_testdata" / "garbage.asc"
    assert t.exists()
    data = gpg.import_keys_file(t)
    print(data.count)
    print(data.stderr)

    t = Path(__file__).parent / ".." / ".." / "tests" / "_testdata" / "E499C79F53C96A54E572FEE1C06086337C50773E.asc"
    assert t.exists()
    data = gpg.import_keys_file(t)
    print(data.count)

    return True


def get_key_from_public_server():
    gpg = gnupg.GPG(gnupghome='/home/kmille/tmp/gpg-test')
    #data = gpg.recv_keys('keys.openpgp.org', 'EF7057AFAD179F5F04FBDD369B5E2484B92BEBD0')
    data = gpg.search_keys('tickets@test.org', 'keys.openpgp.org')
    return True

#def handle_encrypted_mail():


def load_envs():
    envs = []
    required_envs = ["ZAMMAD_BASE_URL", "ZAMMAD_TOKEN"]
    for required_env in required_envs:
        if required_env not in os.environ:
            logging.fatal(f"Required environment variable not set: {required_env}")
            sys.exit(1)
        else:
            envs.append(os.environ[required_env])
    LISTEN_HOST = os.environ.get("LISTEN_HOST", "127.0.0.1")
    LISTEN_PORT = int(os.environ.get("LISTEN_PORT", "22000"))
    DEBUG = os.environ.get("DEBUG", 0)
    return [*envs, LISTEN_HOST, LISTEN_PORT, DEBUG]
