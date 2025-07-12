import logging
import json
import requests

from zammad_pgp_import.utils import get_version
from zammad_pgp_import.pgp import PGPKey
from zammad_pgp_import.exceptions import ZammadError, ZammadPGPKeyAlreadyImportedError

logger = logging.getLogger(__name__)


class Zammad(object):
    session: requests.Session
    bsae_url: str

    def __init__(self, zammad_base_url: str, auth_token: str):
        self.base_url = zammad_base_url
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Token token={auth_token}",
                                     "User-Agent": f"PGP auto-import webhook {get_version()}"})

    def get_all_imported_pgp_keys(self) -> list:
        """
        This is not used any more.  We just import and do net check if the key already exists before
        """
        logger.debug("Getting all imported PGP keys using Zammad API")
        try:
            req = self.session.get(self.base_url + "/api/v1/integration/pgp/key")
            req.raise_for_status()
            return req.json()
        except requests.exceptions.RequestException as e:
            raise ZammadError(f"Could not get all imported PGP keys from Zammad: {e}")

    def download_attachment(self, url: str) -> str:
        logger.debug("Downloading ticket attachment using Zammad API")
        try:
            resp = self.session.get(url)
            resp.raise_for_status()
            logger.debug("Successfully downloaded email attachment")
            return resp.text
        except requests.exceptions.RequestException as e:
            if isinstance(e, requests.exceptions.HTTPError):
                logger.error(f"Zammad API error: {e}")
                raise ZammadError(f"Could not download attachment from Zammad: {e.response.json()['error_human']}")
            raise ZammadError(f"Could not download attachment from Zammad: {e}")

    def import_pgp_key(self, pgp_key: PGPKey) -> None:
        logger.debug("Importing PGP key using Zammad API")
        data = {'file': '',
                'key': pgp_key.raw,
                'passphrase': ""}
        try:
            resp = self.session.post(self.base_url + "/api/v1/integration/pgp/key", json=data)
            resp.raise_for_status()
        except requests.exceptions.RequestException as e:
            if isinstance(e, requests.exceptions.HTTPError) and e.response.status_code == 422:
                raise ZammadPGPKeyAlreadyImportedError(f"Key was already imported. API response: {e.response.json()['error_human']}")
            elif isinstance(e, requests.exceptions.HTTPError):
                logger.error(f"Zammad API error: {e}")
                logger.error(f"Request json:\n{json.dumps(data, indent=4)}")
                raise ZammadError(f"Could not import PGP key: {e.response.json()['error_human']}")
            raise ZammadError(f"Could not import PGP key: {e}")

    def delete_pgp_key(self, email: str) -> None:
        logger.debug("Deleting PGP key using Zammad API")
        try:
            all_imported_keys = self.get_all_imported_pgp_keys()
            matching_keys = list(filter(lambda x: x['email_addresses'][0].lower() == email.lower(), all_imported_keys))
            if len(matching_keys) == 0:
                logger.warning(f"Could find a PGP key with e-mail {email}")
            else:
                resp = self.session.delete(self.base_url + f"/api/v1/integration/pgp/key/{matching_keys[0]['id']}")
                resp.raise_for_status()
                logger.info("Successfully deleted PGP in Zammad")
        except requests.exceptions.RequestException as e:
            logger.warning(f"Could not delete PGP key in Zammad: {e}")
