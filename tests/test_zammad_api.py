from zammad_pgp_autoimport_webhook.zammad import Zammad
from zammad_pgp_autoimport_webhook.pgp import PGPHandler
from zammad_pgp_autoimport_webhook.utils import load_envs

try:
    ZAMMAD_BASE_URL, ZAMMAD_TOKEN, LISTEN_HOST, LISTEN_PORT, DEBUG = load_envs()
except SystemExit:
    print("You need to set the envs")

TEST_PGP_KEY_CERT = """-----BEGIN PGP PUBLIC KEY BLOCK-----
Comment: E499 C79F 53C9 6A54 E572  FEE1 C060 8633 7C50 773E
Comment: Jelle van der Waa <jelle@archlinux.org>
Comment: Jelle van der Waa <jelle@vdwaa.nl>
Comment: Jelle van der Waa <jvanderwaa@redhat.com>

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
eAsEBWHLvLkdZkmwNl7FTQcUol+QOLtFQ+M=
=yWTo
-----END PGP PUBLIC KEY BLOCK-----"""
TEST_PGP_KEY_FINGERPRINT = "E499C79F53C96A54E572FEE1C06086337C50773E"
TEST_PGP_KEY_EMAIL = "jelle@vdwaa.nl"


class TestZammad(object):

    z: Zammad

    def setup_class(self):
        self.zammad = Zammad(ZAMMAD_BASE_URL, ZAMMAD_TOKEN)
        self.zammad.delete_pgp_key(TEST_PGP_KEY_EMAIL)

    def teardown_class(self):
        self.zammad.delete_pgp_key(TEST_PGP_KEY_EMAIL)

    def test_import(self):
        # first, let's import test key
        self.zammad.import_pgp_key(TEST_PGP_KEY_CERT)

        # then, let's check it' really there
        imported_keys = self.zammad.get_all_imported_pgp_keys()
        key = PGPHandler.parse_pgp_key(TEST_PGP_KEY_CERT)
        assert key.fingerprint == TEST_PGP_KEY_FINGERPRINT
        assert key.email == TEST_PGP_KEY_EMAIL
        assert key.fingerprint in [k['fingerprint'] for k in imported_keys]
        assert key.email in [k['email_addresses'][0] for k in imported_keys]

    def test_deletion(self):
        # First, import it
        self.zammad.import_pgp_key(TEST_PGP_KEY_CERT)

        # delete it
        self.zammad.delete_pgp_key(TEST_PGP_KEY_EMAIL)
        # check it does not exist any more
        imported_keys = self.zammad.get_all_imported_pgp_keys()
        assert TEST_PGP_KEY_FINGERPRINT not in [k['fingerprint'] for k in imported_keys]
        assert TEST_PGP_KEY_EMAIL not in [k['email_addresses'][0] for k in imported_keys]
