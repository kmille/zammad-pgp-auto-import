from flask import Flask, request
from pathlib import Path
import requests
from requests import Session
import json
from datetime import datetime
import waitress
import logging

from zammad_pgp_autoimport_webhook.pgp import PGPHandler
from zammad_pgp_autoimport_webhook.zammad import Zammad
from zammad_pgp_autoimport_webhook.utils import get_version, load_envs

#LOG_FORMAT = "[%(asctime)s %(filename)s:%(lineno)s %(funcName)s() %(levelname)s] %(message)s"
LOG_FORMAT = "[%(asctime)s %(levelname)s] %(message)s"
logging.basicConfig(format=LOG_FORMAT,
                    level=logging.DEBUG)

#logging.getLogger("requests").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

ZAMMAD_BASE_URL, ZAMMAD_TOKEN, LISTEN_HOST, LISTEN_PORT, DEBUG = load_envs()

if DEBUG == 1:
    logger.setLevel(logging.DEBUG)

app = Flask(__name__)


"""
TODOS
- check if key is really a pgp key (api changen) - lädt gerade von File
- basic auth
- tests
- input validation api endpoint
"""


def handle_attachments(sender_email, article_data):
    key_data = get_pgp_key_from_attachments(article_data)
    if not key_data:
        return
    pgp_key = PGPHandler.parse_pgp_key(key_data)
    if not pgp_key:
        return
    if pgp_key.email != sender_email:
        logger.info(f"E-Mail contains a PGP not matching with senders email ({sender_email}, {pgp_key.email}")
    else:
        z = Zammad(ZAMMAD_BASE_URL, ZAMMAD_TOKEN)
        known_keys = z.get_all_imported_pgp_keys()
        if pgp_key.fingerprint in known_keys:
            logger.info(f"{pgp_key} already imported")
        else:
            z.import_pgp_key(key_data)


def get_pgp_key_from_attachments(article_data):
    # this only supports a single PGP key
    if len(article_data["attachments"]) == 0:
        logger.debug("This ticket does not have any attachments")
        return None
    for attachment in article_data["attachments"]:
        if "application/pgp-keys" in attachment["preferences"]["Content-Type"]:
            logger.debug("Seems like a PGP key is attached in this email")
            try:
                z = Zammad(ZAMMAD_BASE_URL, ZAMMAD_TOKEN)
                resp = z.download_attachment(attachment["url"])
                resp.raise_for_status()
                return resp.text
            except requests.exceptions.RequestException as e:
                print(f"Could not download PGP via Zammad API: {e}")
                return None


def is_encrypted_mail(article_data) -> bool:
    preferences = article_data["preferences"]
    if "security" not in preferences:
        print("E-Mail is not encrypted")
        return False

    security = preferences["security"]
    if security.get("type", "") != "PGP":
        print("E-Mail seems encrypted, but not with PGP")
        return False

    try:
        return security["encryption"]["success"] is True
    except KeyError as e:
        print(f"Could not check if mail is PGP encrypted: {e}")
        print(json.dumps(security, indent=4))
        return False


@app.route("/zammad/webhook/pgp", methods=["POST"])
def webhook_new_ticket():
    with open(f"request-{datetime.now()}.json", "w") as f:
        json.dump(request.json, f, indent=4)

    data = request.json
    sender_email = data["ticket"]["created_by"]["email"]
    #body = data["article"]["body"]

    handle_attachments(sender_email, data["article"])
    return {"status": "ok"}


@app.route("/status")
def status():
    return {"status": "ok"}


def main():
    logger.info(f"Starting webhook backend: {LISTEN_HOST}:{LISTEN_PORT} (version {get_version()})")
    if __name__ == '__main__':
        app.run(host=LISTEN_HOST, port=LISTEN_PORT, debug=True)
    else:
        waitress.serve(app, listen=f"{LISTEN_HOST}:{LISTEN_PORT}")


if __name__ == '__main__':
    main()
