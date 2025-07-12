#from zammad_pgp_autoimport_webhook.pgp import get_key_from_public_server, get_pgp_key_from_file, get_all_imported_pgp_keys
from zammad_pgp_autoimport_webhook.pgp import PGPKey, PGPHandler
from zammad_pgp_autoimport_webhook.exceptions import PGPError
from pathlib import Path
import pytest

test_key_data = (Path(__file__).parent / "_testdata" / "E499C79F53C96A54E572FEE1C06086337C50773E.asc").read_text()
test_key_email = 'jelle@vdwaa.nl'
test_key_fingerprint = "E499C79F53C96A54E572FEE1C06086337C50773E"


class TestPGPHandler:

    def test_parse_valid_pgp_key(self):
        key = PGPKey(test_key_data)
        assert key.fingerprint == test_key_fingerprint
        assert set(key.emails) == {'jelle@archlinux.org', 'jelle@vdwaa.nl', 'jvanderwaa@redhat.com'}
        assert key.has_email(test_key_email)
        assert not key.has_email('nooo@abc.de')

    def test_parse_invalid_pgp_key(self):
        key_data = "this is not a PGP key"
        with pytest.raises(PGPError):
            PGPKey(key_data)

    def test_search_valid_pgp_key(self):
        key = PGPHandler.search_pgp_key(test_key_email)
        assert key.fingerprint == test_key_fingerprint

    def test_search_invalid_pgp_key(self):
        with pytest.raises(PGPError):
            PGPHandler.search_pgp_key('nanana@noo.lol')
