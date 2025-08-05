import logging
import re
import os
import subprocess
# from datetime import datetime, date
import requests

from zammad_pgp_import.exceptions import PGPError, RateLimitError, NotFoundOnKeyserverError

logger = logging.getLogger(__name__)

KEY_SERVER = os.environ.get("KEY_SERVER", "https://keys.openpgp.org")


class PGPKey(object):
    raw: str
    meta: str
    emails: list[str] = []
    fingerprint: str
    # expires: date
    is_expired: bool

    def __init__(self, key_data: str):
        self.raw = key_data
        try:
            p = subprocess.run(["gpg", "--show-keys"], input=key_data.encode(), capture_output=True, check=True)
            self.meta = p.stdout.decode()
        except FileNotFoundError as e:
            raise PGPError(f"Could not find gpg binary: {e}")
        except subprocess.CalledProcessError as e:
            logging.error(f"Content of the PGP key\n: {key_data}")
            raise PGPError(f"Could not decode pgp key: {e.stderr.decode()}")

        for line in self.meta.splitlines():
            if line.startswith("uid"):
                if result := re.search(r'<(.*)>', line):
                    self.emails.append(result.group(1))
            elif result := re.search(r'[0-9A-F]{40}', line):
                self.fingerprint = result[0]
            # elif result := re.search(r'expires: (\d{4}-\d{2}-\d{2})', line):
            #     self.expires = datetime.strptime(result.group(1), "%Y-%m-%d").date()
            #     self.is_expired = datetime.now().date() > self.expires

        #  TODO: test if everything is set up
        # breakpoint()
        # if not all([self.fingerprint, self.expires]):
        #     raise PGPError("Could not parse PGP key data")
        self.is_expired = False

    def has_email(self, email: str) -> bool:
        return email in self.emails

    def __repr__(self) -> str:
        # return f"PGPKey (emails={','.join(self.emails)} fingerprint={self.fingerprint}, expires={self.expires}))"
        return f"PGPKey (emails={','.join(self.emails)} fingerprint={self.fingerprint}"


class PGPHandler:

    @staticmethod
    def search_pgp_key(email: str) -> PGPKey:
        logging.debug(f"Using keyserver {KEY_SERVER} to find a PGP key for {email}")
        try:
            resp = requests.get(KEY_SERVER + f"/pks/lookup?op=get&options=mr&search={email}")
            resp.raise_for_status()
            return PGPKey(resp.text)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.debug(f"API error message: {e.response.text.strip()}")
                raise NotFoundOnKeyserverError(f"Could not find a PGP key for {email} using keyserver {KEY_SERVER}")
            elif e.response.status_code == 429:
                logger.debug(f"We got rate limited by the API: {e.response.text.strip()}")
                raise RateLimitError(f"Could not find a PGP key for {email} using keyserver {KEY_SERVER}")
            else:
                raise PGPError(f"Could not find PGP key on {KEY_SERVER}: {e.response.text}")
        except requests.exceptions.RequestException as e:
            raise PGPError(f"Could not get PGP key: {e}")
