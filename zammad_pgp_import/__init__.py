import logging
import sys
import json
import argparse
from typing import Optional
from flask import Flask, request
from flask_basicauth import BasicAuth
import waitress
import werkzeug

from zammad_pgp_import.utils import get_version, load_envs
from zammad_pgp_import.exceptions import PGPImportError, NotFoundOnKeyserverError, RateLimitError, ZammadPGPKeyAlreadyImportedError
from zammad_pgp_import.zammad import Zammad
from zammad_pgp_import.pgp import PGPHandler, PGPKey

DESC = """Zammad webhook that automatically imports PGP keys.
    There is also a cli to import PGP keys manually.
    Configuration is done via environment variables.
    Docs can be found here: https://github.com/kmille/zammad-pgp-auto-import"""


LOG_FORMAT = "[%(asctime)s %(levelname)5s] %(message)s"
logging.basicConfig(format=LOG_FORMAT,
                    level=logging.INFO)

logging.getLogger("urllib3").setLevel(logging.WARNING)


logger = logging.getLogger(__name__)

(ZAMMAD_BASE_URL, ZAMMAD_TOKEN, BASIC_AUTH_USER, BASIC_AUTH_PASSWORD,
    LISTEN_HOST, LISTEN_PORT, DEBUG) = load_envs()

if DEBUG == "1":
    logger.setLevel(logging.DEBUG)

app = Flask(__name__)
app.config['BASIC_AUTH_USERNAME'] = BASIC_AUTH_USER
app.config['BASIC_AUTH_PASSWORD'] = BASIC_AUTH_PASSWORD
app.config['BASIC_AUTH_FORCE'] = True  # protect all endpoints
basic_auth = BasicAuth(app)

error_counter = 0


def is_encrypted_mail(article_data: dict) -> bool:
    preferences = article_data["preferences"]
    if "security" not in preferences:
        return False

    security = preferences["security"]
    if security.get("type", "") != "PGP":
        logger.debug("Email seems encrypted, but not with PGP")
        return False

    try:
        return security["encryption"].get("success", False) is True
    except KeyError as e:
        logger.error(f"Could not check if mail is PGP encrypted: {e}")
        logger.error(json.dumps(article_data, indent=4))
        return False


def get_pgp_key_from_attachments(article_data: dict) -> Optional[PGPKey]:
    # this only supports a single PGP key
    if len(article_data["attachments"]) == 0:
        logger.debug("This ticket does not have any attachments")
        return None
    for attachment in article_data["attachments"]:
        if "application/pgp-keys" in attachment["preferences"].get("Content-Type", ""):
            logger.info("Seems like a PGP key is attached to this email")
            z = Zammad(ZAMMAD_BASE_URL, ZAMMAD_TOKEN)
            key_data = z.download_attachment(attachment["url"])
            return PGPKey(key_data)
        else:
            logger.debug(f"This attachment is not a PGP key (Content-Type='{attachment['preferences'].get('Content-Type', '')}')")
    logger.debug("No PGP key was attached to this email")
    return None


def import_pgp_key(pgp_key: PGPKey, sender_email: str) -> None:
    if not pgp_key.has_email(sender_email):
        logger.warning(f"E-Mail contains a PGP not matching with senders email ({sender_email}, {pgp_key})")
    elif pgp_key.is_expired:
        pass
        # logger.warning(f"PGP key is already expired. Not importing it ({pgp_key.expires})")
    else:
        z = Zammad(ZAMMAD_BASE_URL, ZAMMAD_TOKEN)
        try:
            z.import_pgp_key(pgp_key)
        except ZammadPGPKeyAlreadyImportedError as e:
            logger.info(e)
        else:
            logger.info(f"Successfully imported pgp key {pgp_key.fingerprint} for email {sender_email}")


def get_key_from_keyserver(email: str) -> Optional[PGPKey]:
    try:
        pgp_key = PGPHandler.search_pgp_key(email)
        logger.info("Successfully found PGP key using a keyserver")
        return pgp_key
    except NotFoundOnKeyserverError as e:
        logging.error(e)
        return None


@app.route("/api/zammad/pgp", methods=["POST"])
def webhook_new_ticket() -> tuple[dict[str, str], int]:
    global error_counter
    try:
        data = request.get_json(force=True)
        sender_email = data["ticket"]["created_by"]["email"]
        article_data = data['article']

        is_encrypted = is_encrypted_mail(article_data)
        logger.info(f"Received a new Ticket: {ZAMMAD_BASE_URL}/#ticket/zoom/{data['ticket']['id']} (from={sender_email}, is_encrypted={is_encrypted})")

        # always check if there is a PGP key attached to the mail
        pgp_key = get_pgp_key_from_attachments(article_data)
        # if we don't have a pgp key at this point and the mail is encrypted, check if we can find one online
        if not pgp_key and is_encrypted:
            pgp_key = get_key_from_keyserver(sender_email)
        if pgp_key:
            import_pgp_key(pgp_key, sender_email)
        else:
            logger.info("Ticket does not have a PGP key attached. It is also not encrypted and/or PGP key was not found on a keysever")

    except (werkzeug.exceptions.BadRequest, KeyError) as e:
        logger.exception(e)
        error_counter += 1
        return {"status": 'failed', 'reason': 'invalid client request'}, 500
    except PGPImportError as e:
        logger.error(e)
        logger.exception(e)
        error_counter += 1
        return {"status": 'failed', 'reason': 'PGP/API error'}, 500
    except Exception as e:
        logger.error(f"Unhandled exception occured: {e}")
        logger.exception(e)
        error_counter += 1
        return {"status": "failed", 'reason': 'unhandled exception'}, 500
    else:
        return {"status": "ok"}, 200


@app.route("/status")
def status() -> dict:
    if error_counter == 0:
        return {"status": "ok"}
    else:
        return {"status": "failed"}


def serve_backend() -> None:
    logger.info(f"Starting webhook backend on {LISTEN_HOST}:{LISTEN_PORT} (version {get_version()}, debug={DEBUG == '1'})")
    if __name__ == '__main__':
        app.run(host=LISTEN_HOST, port=LISTEN_PORT, debug=True)
    else:
        waitress.serve(app, listen=f"{LISTEN_HOST}:{LISTEN_PORT}")


def find_and_import_pgp_key(search_term: str) -> None:
    # search can be key-id or email
    pgp_key = PGPHandler.search_pgp_key(search_term)
    logger.info(f"Found key: {pgp_key}")
    z = Zammad(ZAMMAD_BASE_URL, ZAMMAD_TOKEN)
    z.import_pgp_key(pgp_key)
    logger.info("Successfully imported PGP key")


def import_pgp_keys_from_thunderbird(db_file: str) -> None:
    # https://keys.openpgp.org/about/api#rate-limiting
    import sqlite3
    from pathlib import Path
    import time

    db = Path(db_file).expanduser()
    if not db.exists() or db.name != "global-messages-db.sqlite":
        logger.error("Thunderbird db: File does not exist or file name is not 'global-messages-db.sqlite'")
        sys.exit(1)

    try:
        con = sqlite3.connect(db_file)
        cur = con.cursor()
        res = cur.execute("SELECT value FROM identities WHERE kind = 'email'")

        email_addresses = []
        for row in res.fetchall():
            email = row[0]
            if email not in email_addresses:
                email_addresses.append(email)
            logger.debug(f"Read email: {email}")
    except Exception as e:
        logger.error(f"Could not read email addresses from Thunderbird db: {e}")
        sys.exit(1)

    logger.info(f"Read {len(email_addresses)} addresses")
    for i, email in enumerate(email_addresses):
        logger.info(f"Checking mail {i}/{len(email_addresses)}: {email}")
        try:
            find_and_import_pgp_key(email)
            time.sleep(90)
        except (NotFoundOnKeyserverError, ZammadPGPKeyAlreadyImportedError) as e:
            logger.info(e)
            time.sleep(90)
        except (RateLimitError, Exception) as e:
            logger.error(e)
            logger.info(f"Got rate limited for {email}")
            sys.exit(1)


def main() -> None:

    parser = argparse.ArgumentParser("zammad-pgp-import", description=DESC)
    parser.add_argument("--backend", "-b", action="store_true", help="run webhook backend")
    parser.add_argument("--import-key", "-i", help="import pgp key by supplied email/key id")
    _help = """Needs a global-messages-db.sqlite file. Get all email addresses from global-messages-db.sqlite
    (part of a Thunderbird profile). Try to find a PGP key and import it to Zammad.
    As there is rate limiting, we sleep for a long time after each attempt. So you may want to run this on a server"""
    parser.add_argument("--import-thunderbird", "-t", help=_help)
    parser.add_argument("--version", action="store_true", help="show version")
    args = parser.parse_args()

    if args.backend:
        serve_backend()
    elif args.import_key:
        try:
            find_and_import_pgp_key(args.import_key)
        except Exception as e:
            logger.error(f"Could not import PGP key: {e}")
    elif args.import_thunderbird:
        import_pgp_keys_from_thunderbird(args.import_thunderbird)
    elif args.version:
        print(f"{sys.argv[0]} {get_version()}")
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
