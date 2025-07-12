from flask import Flask, request
from flask_basicauth import BasicAuth
import json
import waitress
import werkzeug
import logging

from zammad_pgp_autoimport_webhook.pgp import PGPHandler, PGPKey
from zammad_pgp_autoimport_webhook.zammad import Zammad
from zammad_pgp_autoimport_webhook.utils import get_version, load_envs
from zammad_pgp_autoimport_webhook.exceptions import PGPImportError, NotFoundOnKeyserverError, ZammadPGPKeyAlreadyImportedError

#LOG_FORMAT = "[%(asctime)s %(filename)s:%(lineno)s %(funcName)s() %(levelname)s] %(message)s"
LOG_FORMAT = "[%(asctime)s %(levelname)5s] %(message)s"
logging.basicConfig(format=LOG_FORMAT,
                    level=logging.INFO)

logging.getLogger("urllib3").setLevel(logging.WARNING)


logger = logging.getLogger(__name__)

(ZAMMAD_BASE_URL, ZAMMAD_TOKEN, BASIC_AUTH_USER, BASIC_AUTH_PASSWORD,
    LISTEN_HOST, LISTEN_PORT, DEBUG) = load_envs()

if DEBUG == 1:
    logger.setLevel(logging.DEBUG)

app = Flask(__name__)
app.config['BASIC_AUTH_USERNAME'] = BASIC_AUTH_USER
app.config['BASIC_AUTH_PASSWORD'] = BASIC_AUTH_PASSWORD
app.config['BASIC_AUTH_FORCE'] = True # protect all endpoints
basic_auth = BasicAuth(app)

error_counter = 0


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


def get_pgp_key_from_attachments(article_data: dict):
    # this only supports a single PGP key
    if len(article_data["attachments"]) == 0:
        logger.debug("This ticket does not have any attachments")
        return None
    for attachment in article_data["attachments"]:
        if "application/pgp-keys" in attachment["preferences"]["Content-Type"]:
            logger.debug("Seems like a PGP key is attached to this email")
            z = Zammad(ZAMMAD_BASE_URL, ZAMMAD_TOKEN)
            key_data = z.download_attachment(attachment["url"])
            return PGPKey(key_data)


def import_pgp_key(pgp_key: PGPKey, sender_email: str):
    if not pgp_key.has_email(sender_email):
        logger.warning(f"E-Mail contains a PGP not matching with senders email ({sender_email}, {pgp_key})")
        raise ValueError("nooon")
    elif pgp_key.is_expired:
        logger.warning(f"PGP key is already expired. Not importing it ({pgp_key.expires})")
    else:
        z = Zammad(ZAMMAD_BASE_URL, ZAMMAD_TOKEN)
        try:
            z.import_pgp_key(pgp_key)
        except ZammadPGPKeyAlreadyImportedError as e:
            logger.info(e)
        else:
            logger.info(f"Successfully imported pgp key ({pgp_key.fingerprint}) for email {sender_email}")


def get_key_from_keyserver(email: str) -> PGPKey:
    try:
        pgp_key = PGPHandler.search_pgp_key(email)
        logger.info("Successfully found PGP key using a keyserver")
        return pgp_key
    except NotFoundOnKeyserverError as e:
        logging.error(e)
        return None


@app.route("/api/zammad/pgp", methods=["POST"])
def webhook_new_ticket():
    global error_counter
    try:
        data = request.get_json(force=True)
        sender_email = data["ticket"]["created_by"]["email"]
        article_data = data['article']

        is_encrypted = is_encrypted_mail(article_data)
        logger.info(f"Received a new ticket: {ZAMMAD_BASE_URL}/#ticket/zoom/{data['ticket']['id']} (from={sender_email}, is_encrypted={is_encrypted})")

        pgp_key = get_pgp_key_from_attachments(article_data)
        if not pgp_key:
            pgp_key = get_key_from_keyserver(sender_email)
        if not pgp_key:
            logger.info("Could not import PGP key. Key was not attached to mail nor a key was found on the keyserver")
        else:
            import_pgp_key(pgp_key, sender_email)
    except (werkzeug.exceptions.BadRequest, KeyError) as e:
        logger.exception(e)
        error_counter += 1
        return {"status": 'failed', 'reason': 'invalid client request'}, 500
    except PGPImportError as e:
        logger.error(e)
        error_counter += 1
        return {"status": 'failed', 'reason': 'PGP/API error'}, 500
    except Exception as e:
        logger.error(f"Unhandled exception occured: {e}")
        logger.exception(e)
        error_counter += 1
        return {"status": "failed", 'reason': 'unhandled exception'}, 500
    else:
        return {"status": "ok"}


@app.route("/status")
def status():
    if error_counter == 0:
        return {"status": "ok"}
    else:
        return {"status": "fail"}


def main():
    logger.info(f"Starting webhook backend on {LISTEN_HOST}:{LISTEN_PORT} (version {get_version()}, debug={DEBUG == '1'})")
    if __name__ == '__main__':
        app.run(host=LISTEN_HOST, port=LISTEN_PORT, debug=True)
    else:
        waitress.serve(app, listen=f"{LISTEN_HOST}:{LISTEN_PORT}")


if __name__ == '__main__':
    main()
