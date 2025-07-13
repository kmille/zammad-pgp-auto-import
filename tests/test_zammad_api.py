from pathlib import Path
import pytest
import requests.exceptions

from zammad_pgp_import.zammad import Zammad
from zammad_pgp_import.pgp import PGPKey
from zammad_pgp_import.exceptions import ZammadError, ZammadPGPKeyAlreadyImportedError


ZAMMAD_BASE_URL = "https://tickets.example.org"
ZAMMAD_TOKEN = "secret token"

test_key_data = (Path(__file__).parent / "_testdata" / "E499C79F53C96A54E572FEE1C06086337C50773E.asc").read_text()


class TestZammad():

    def test_zammad_get_all_keys_ok(self, requests_mock):
        requests_mock.get(ZAMMAD_BASE_URL + "/api/v1/integration/pgp/key", json=[])
        z = Zammad(ZAMMAD_BASE_URL, ZAMMAD_TOKEN)
        assert z.get_all_imported_pgp_keys() == []

    def test_zammad_get_all_keys_network_issue(self, requests_mock):
        requests_mock.get(ZAMMAD_BASE_URL + "/api/v1/integration/pgp/key", exc=requests.exceptions.HTTPError)
        z = Zammad(ZAMMAD_BASE_URL, ZAMMAD_TOKEN)
        with pytest.raises(ZammadError):
            z.get_all_imported_pgp_keys()

    def test_zammad_download_attachment_ok(self, requests_mock):
        requests_mock.get(ZAMMAD_BASE_URL + "/attachment/1", text="data")
        z = Zammad(ZAMMAD_BASE_URL, ZAMMAD_TOKEN)
        assert z.download_attachment(ZAMMAD_BASE_URL + "/attachment/1") == "data"

    def test_zammad_download_attachment_network_issue(self, requests_mock):
        requests_mock.get(ZAMMAD_BASE_URL + "/attachment/1", exc=requests.exceptions.ConnectTimeout)
        z = Zammad(ZAMMAD_BASE_URL, ZAMMAD_TOKEN)
        with pytest.raises(ZammadError):
            assert z.download_attachment(ZAMMAD_BASE_URL + "/attachment/1")

    def test_zammad_import_pgp_key_ok(self, requests_mock):
        requests_mock.post(ZAMMAD_BASE_URL + "/api/v1/integration/pgp/key")
        z = Zammad(ZAMMAD_BASE_URL, ZAMMAD_TOKEN)
        z.import_pgp_key(PGPKey(test_key_data))

    def test_zammad_import_pgp_key_network_issue(self, requests_mock):
        requests_mock.post(ZAMMAD_BASE_URL + "/api/v1/integration/pgp/key", exc=requests.exceptions.ConnectTimeout)
        z = Zammad(ZAMMAD_BASE_URL, ZAMMAD_TOKEN)
        with pytest.raises(ZammadError):
            z.import_pgp_key(PGPKey(test_key_data))

    def test_zammad_import_pgp_key_already_exists(self, requests_mock):
        http_error = requests.exceptions.HTTPError()
        http_error.response = requests.models.Response()
        http_error.response.status_code = 422
        http_error.response._content = b'{ "error_human" : "error message" }'

        requests_mock.post(ZAMMAD_BASE_URL + "/api/v1/integration/pgp/key", exc=http_error)
        z = Zammad(ZAMMAD_BASE_URL, ZAMMAD_TOKEN)
        with pytest.raises(ZammadPGPKeyAlreadyImportedError):
            z.import_pgp_key(PGPKey(test_key_data))
