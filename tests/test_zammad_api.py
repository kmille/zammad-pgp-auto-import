from zammad_pgp_autoimport_webhook.zammad import Zammad
from zammad_pgp_autoimport_webhook.pgp import PGPHandler
from zammad_pgp_autoimport_webhook.utils import load_envs
from zammad_pgp_autoimport_webhook.exceptions import ZammadError
from pathlib import Path

try:
    ZAMMAD_BASE_URL, ZAMMAD_TOKEN, LISTEN_HOST, LISTEN_PORT, DEBUG = load_envs()
except SystemExit:
    print("You need to set the envs")

test_key_data = (Path(__file__).parent / "_testdata" / "E499C79F53C96A54E572FEE1C06086337C50773E.asc").read_text()
test_key_email = 'jelle@vdwaa.nl'
test_key_fingerprint = "E499C79F53C96A54E572FEE1C06086337C50773E"


class TestZammad(object):

    zammad: Zammad

    def setup_class(self):
        self.zammad = Zammad(ZAMMAD_BASE_URL, ZAMMAD_TOKEN)
        self.zammad.delete_pgp_key(test_key_email)

    def teardown_class(self):
        self.zammad.delete_pgp_key(test_key_email)

    def test_zammad_pgp_import(self):
        # first, let's import test key
        self.zammad.import_pgp_key(test_key_data)

        key = PGPHandler.parse_pgp_key(test_key_data)
        assert key.fingerprint == test_key_fingerprint
        assert test_key_email in key.emails

        # then, let's check it's really there
        imported_keys = self.zammad.get_all_imported_pgp_keys()
        assert key.fingerprint in [k['fingerprint'] for k in imported_keys]
        assert set(key.emails) in ([set(e['email_addresses']) for e in imported_keys])

    def test_zammad_pgp_deletion(self):
        try:
            self.zammad.import_pgp_key(test_key_data)
        except ZammadError:
            # key already exists
            pass

        # delete it
        self.zammad.delete_pgp_key(test_key_email)
        # check it does not exist any more
        imported_keys = self.zammad.get_all_imported_pgp_keys()
        assert test_key_fingerprint not in [k['fingerprint'] for k in imported_keys]
