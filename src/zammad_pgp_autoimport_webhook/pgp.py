import subprocess
from datetime import datetime, date
import re
import os
import logging
import requests
from zammad_pgp_autoimport_webhook.exceptions import PGPError, NotFoundOnKeyserverError

logger = logging.getLogger(__name__)

KEY_SERVER = os.environ.get("KEY_SERVER", "https://keys.openpgp.org")


class PGPKey(object):
    raw: str
    meta: str
    emails: list[str] = []
    fingerprint: str
    expires: date
    is_expired: bool

    def __init__(self, raw: str, cli_output: str):
        self.raw = raw
        self.meta = cli_output
        for line in cli_output.splitlines():
            if line.startswith("uid"):
                if result := re.search(r'<(.*)>', line):
                    self.emails.append(result.group(1))
            elif re.search(r'[0-9A-F]{40}', line):
                self.fingerprint = re.search(r'[0-9A-F]{40}', line)[0]
            elif result := re.search(r'expires: (\d{4}-\d{2}-\d{2})', line):
                self.expires = datetime.strptime(result.group(1), "%Y-%m-%d").date()
                self.is_expired = datetime.now().date() > self.expires

    def has_email(self, email: str) -> bool:
        return email in self.emails

    def __repr__(self):
        return f"PGPKey (emails={','.join(self.emails)} fingerprint={self.fingerprint}, expires={self.expires}))"


class PGPHandler:

    @staticmethod
    def parse_pgp_key(key_data: str) -> PGPKey:
        try:
            logger.info("TODO INPUT VALIDATION")
            p = subprocess.run("gpg", input=key_data.encode(), capture_output=True, check=True)
            logging.debug(f"Parsed attached PGP key:\n{p.stdout.decode()}")
            return PGPKey(key_data, p.stdout.decode())
        except FileNotFoundError as e:
            raise PGPError(f"Could not find pgp binary: {e}")
        except subprocess.CalledProcessError as e:
            logging.error(f"Content of the attachment\n: {key_data}")
            raise PGPError(f"Could not decode pgp key: {e.stderr.decode()}")

    @staticmethod
    def search_pgp_key(email: str) -> PGPKey:
        logging.debug(f"Using keyserver {KEY_SERVER} to find a PGP key for {email}")
        try:
            resp = requests.get(KEY_SERVER + f"/pks/lookup?op=get&options=mr&search={email}")
            resp.raise_for_status()
            return PGPHandler.parse_pgp_key(resp.text)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 400:
                logger.debug(f"API error message: {e.response.text}")
                raise NotFoundOnKeyserverError(f"Could find a PGP key for {email} using keyserver {KEY_SERVER}")
            else:
                raise PGPError(f"Could find PGP key on {KEY_SERVER}: {e.response.text}")
        except requests.exceptions.RequestException as e:
            raise PGPError(f"Could find PGP key on {KEY_SERVER}: {e}")
