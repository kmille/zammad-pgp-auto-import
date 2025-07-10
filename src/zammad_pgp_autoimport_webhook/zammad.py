from zammad_pgp_autoimport_webhook.utils import get_version
import requests
import logging
import json


logger = logging.getLogger(__name__)


class Zammad(object):
    session = requests.Session
    #zammad_base: str

    def __init__(self, zammad_base_url: str, auth_token: str):
        self.base_url = zammad_base_url
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Token token={auth_token}",
                                     "User-Agent": f"PGP auto-import webhook {get_version()}"})

    def get_all_imported_pgp_keys(self):
        req = self.session.get(self.base_url + "/api/v1/integration/pgp/key")
        req.raise_for_status()
        #return [k["fingerprint"] for k in req.json()]
        return req.json()

    def download_attachment(self, url: str):
        return self.session.get(url)

    def delete_pgp_key(self, email: str):
        all_imported_keys = self.get_all_imported_pgp_keys()
        matching_keys = list(filter(lambda x: x['email_addresses'][0].lower() == email.lower(), all_imported_keys))
        if len(matching_keys) == 0:
            logger.warning(f"Could find a PGP key with e-mail {email}")
            print(f"Could find a PGP key with e-mail {email}")
        else:
            resp = self.session.delete(self.base_url + f"/api/v1/integration/pgp/key/{matching_keys[0]['id']}")
            resp.raise_for_status()
            print(resp.json())
            print("KEY DELETED!")

    def import_pgp_key(self, key_data: str):
        data = {'file': '',
                'key': key_data,
                'passphrase': ""}
        try:
            resp = self.session.post(self.base_url + "/api/v1/integration/pgp/key", json=data)
            resp.raise_for_status()
            logger.info("Successfully imported pgp key")
            logger.debug(resp.json())
            print("KEY UPLOADED")
        except requests.exceptions.RequestException as e:
            logger.error(f"Could not import PGP: {e.response.json()['error']}")
            logger.error(f"Request json:\n{json.dumps(data, indent=4)}")
