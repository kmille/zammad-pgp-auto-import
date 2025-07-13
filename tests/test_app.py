#from zammad_pgp_import.pgp import PGPHandler, PGPKey
#from zammad_pgp_import.utils import load_envs
import zammad_pgp_import
from pathlib import Path
from zammad_pgp_import import app
import zammad_pgp_import
import copy
import pytest

ZAMMAD_BASE_URL = "https://tickets.example.org"
ZAMMAD_TOKEN = "secret token"

test_key_data = (Path(__file__).parent / "_testdata" / "E499C79F53C96A54E572FEE1C06086337C50773E.asc").read_text()
test_key_email = 'jelle@vdwaa.nl'


zammad_pgp_import.ZAMMAD_BASE_URL = ZAMMAD_BASE_URL



@pytest.fixture()
def client():
    app.config['BASIC_AUTH_USERNAME'] = "admin"
    app.config['BASIC_AUTH_PASSWORD'] = "admin123"

    with app.test_client() as client:
        yield client


class TestEnd2EndStatusEndpoint:

    def test_status_auth_required(self, client):
        assert client.get("/status").status_code == 401

    def test_status_auth_ok(self, client):
        assert client.get("/status", auth=("admin", "admin123")).status_code == 200

    def test_status_state_ok(self, client):
        zammad_pgp_import.error_counter = 0
        resp = client.get("/status", auth=("admin", "admin123"))
        assert resp.status_code == 200
        assert resp.json["status"] == "ok"

    def test_status_state_failed(self, client):
        zammad_pgp_import.error_counter = 1
        resp = client.get("/status", auth=("admin", "admin123"))
        assert resp.status_code == 200
        assert resp.json["status"] == "failed"


class TestEnd2EndWebhookEndpoint:

    minimum_ticket_data = {
        "ticket": {
            "id": 10,
            "created_by": {
                "email": test_key_email,
            },
        },
        "article": {
            "preferences": {},
            "attachments": [],

        }
    }

    def test_webhook_auth_required(self, client):
        assert client.get("/api/zammad/pgp").status_code == 401
        assert client.post("/api/zammad/pgp").status_code == 401

    def test_webhook_auth_ok(self, client):
        assert client.get("/api/zammad/pgp", auth=("admin", "admin123")).status_code == 405 # not allowed
        resp = client.post("/api/zammad/pgp",
                           json=self.minimum_ticket_data,
                           auth=("admin", "admin123"))
        assert resp.status_code == 200

    def test_webhook_pgp_key_attached(self, client, requests_mock):
        ticket = copy.deepcopy(self.minimum_ticket_data)
        attachment = {
            "preferences": {
                "Content-Type": "application/pgp-keys",
            },
            "url": ZAMMAD_BASE_URL + "/attachment/1",
        }
        ticket["article"]["attachments"] = [attachment, ]

        requests_mock.get(ZAMMAD_BASE_URL + "/attachment/1", text=test_key_data)
        requests_mock.post(ZAMMAD_BASE_URL + "/api/v1/integration/pgp/key")
        resp = client.post("/api/zammad/pgp",
                           json=ticket,
                           auth=("admin", "admin123"))
        assert resp.status_code == 200

    def test_webhook_pgp_encrypted(self, client, requests_mock):
        ticket = copy.deepcopy(self.minimum_ticket_data)

        ticket["article"] = {
            "preferences": {
                "security": {
                    "type": "PGP",
                },
                "encryption": {
                    "success": True
                },
            },
            "attachments": [],
        }

        requests_mock.post(ZAMMAD_BASE_URL + "/api/v1/integration/pgp/key")
        resp = client.post("/api/zammad/pgp",
                           json=ticket,
                           auth=("admin", "admin123"))
        assert resp.status_code == 200
