import subprocess
import re
import logging

logger = logging.getLogger(__name__)


class PGPKey(object):
    email: str
    fingerprint: str
    raw: str

    def __init__(self, cli_output: str):
        self.raw = cli_output
        # TODO: check if key is expired
        for line in cli_output.splitlines():
            if line.startswith("uid"):
                result = re.search(r'<.*>', line)[0]
                self.email = result[1:len(result)-1] # dirty hack :/
            if re.search(r'[0-9A-F]{40}', line):
                self.fingerprint = re.search(r'[0-9A-F]{40}', line)[0]

    def __repr__(self):
        return f"PGPKey (email={self.email} fingerprint={self.fingerprint})"


class PGPHandler:

    @staticmethod
    def parse_pgp_key(key_data):
        try:
            logger.info("TODO INPUT VALIDATION")
            p = subprocess.run("gpg", input=key_data.encode(), capture_output=True, check=True)
            logging.debug(f"Parsed attached PGP key:\n{p.stdout.decode()}")
            return PGPKey(p.stdout.decode())
        except FileNotFoundError as e:
            logging.error(f"Could not find gpg binary: {e}")
        except subprocess.CalledProcessError as e:
            logging.error(f"Could not decode pgp key: {e.stderr.decode()}")
            logging.error(f"Content of the attachment\n: {key_data}")
