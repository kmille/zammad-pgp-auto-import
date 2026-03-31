import logging
import sys
import json
import argparse
from typing import Optional
from datetime import datetime, timezone
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
            key_data = z.download_attachment(article_data["ticket_id"], article_data["id"], attachment["id"])
            return PGPKey(key_data)
        else:
            logger.debug(f"This attachment is not a PGP key (Content-Type='{attachment['preferences'].get('Content-Type', '')}')")
    logger.debug("No PGP key was attached to this email")
    return None


def import_pgp_key(pgp_key: PGPKey, sender_email: str) -> None:
    if not pgp_key.has_email(sender_email):
        logger.warning(f"E-Mail contains a PGP key not matching with senders email ({sender_email}, {pgp_key})")
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
        logger.error(e)
        return None


def run_webhok_for_ticket(ticket_id: int, sender_email: str, article_data: dict) -> None:
    ticket_url = f"{ZAMMAD_BASE_URL}/#ticket/zoom/{ticket_id}"
    is_encrypted = is_encrypted_mail(article_data)
    logger.info(f"Running webhook for ticket: {ticket_url} (from={sender_email}, is_encrypted={is_encrypted})")

    # always check if there is a PGP key attached to the mail
    pgp_key = get_pgp_key_from_attachments(article_data)
    # if we don't have a pgp key at this point and the mail is encrypted, check if we can find one online
    if not pgp_key and is_encrypted:
        pgp_key = get_key_from_keyserver(sender_email)
    if pgp_key:
        import_pgp_key(pgp_key, sender_email)
    else:
        logger.info("Ticket does not have a PGP key attached. It is also not encrypted and/or PGP key was not found on a keysever")


@app.route("/api/zammad/pgp", methods=["POST"])
@basic_auth.required
def webhook_new_ticket() -> tuple[dict[str, str], int]:
    global error_counter
    try:
        ticket_data = request.get_json(force=True)
        sender_email = ticket_data["ticket"]["created_by"]["email"]
        article_data = ticket_data['article']
        run_webhok_for_ticket(ticket_data['ticket']['id'], sender_email, article_data)
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
    logger.info(f"Found key on keyserver: {pgp_key}")
    z = Zammad(ZAMMAD_BASE_URL, ZAMMAD_TOKEN)
    z.import_pgp_key(pgp_key)
    logger.info("Successfully imported PGP key")


def remove_expired_pgp_keys():
    logger.info("Iterating over all imported PGP keys to remove expired ones")
    z = Zammad(ZAMMAD_BASE_URL, ZAMMAD_TOKEN)
    pgp_keys = z.get_all_imported_pgp_keys()
    now = datetime.now(timezone.utc)
    for key in pgp_keys:
        logger.debug(f"Checking key {key['fingerprint']}")
        if not key["expires_at"]:
            # some keys do not expire at all
            continue
        expires_at = datetime.fromisoformat(key["expires_at"])
        if now > expires_at:
            logger.info(f"Key {key['fingerprint']} ({','.join(key['email_addresses'])}) is outdated")
            z.delete_pgp_key(key["id"])


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
            time.sleep(70)
        except (NotFoundOnKeyserverError, ZammadPGPKeyAlreadyImportedError) as e:
            logger.info(e)
            time.sleep(70)
        except RateLimitError as e:
            logger.error(f"Got rate limited for {email}: {e}")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Got generic exception for email {email}")
            logger.error(e)
            sys.exit(1)


def run_webhook_for_ticket(ticket_id: int):
    logging.info(f"Getting all data before running webhook for ticket {ticket_id}")
    z = Zammad(ZAMMAD_BASE_URL, ZAMMAD_TOKEN)
    ticket_data = z.get_ticket(ticket_id)
    customer_id = ticket_data["customer_id"]
    user = z.get_user(customer_id)
    email = user["email"]
    articles = z.get_ticket_articles(ticket_id)
    run_webhok_for_ticket(ticket_id, email, articles[0])


def check_all_tickets():
    logging.info("Checking all tickets")
    z = Zammad(ZAMMAD_BASE_URL, ZAMMAD_TOKEN)
    tickets = z.get_tickets()
    for ticket in tickets:
        run_webhook_for_ticket(ticket["id"])


def main() -> None:
    parser = argparse.ArgumentParser("zammad-pgp-import", description=DESC)
    parser.add_argument("--backend", "-b", action="store_true", help="run webhook backend")
    parser.add_argument("--import-key", "-i", help="use key server to import pgp key by supplied email/key id")
    _help = """Needs a global-messages-db.sqlite file. Get all email addresses from global-messages-db.sqlite
    (part of a Thunderbird profile). Try to find a PGP key and import it to Zammad.
    As there is rate limiting, we sleep for a long time after each attempt. So you may want to run this on a server"""
    parser.add_argument("--remove-expired-keys", action="store_true", help="Iterate over all imported PGP keys in Zammad and remove the expired ones")
    parser.add_argument("--run-webhook-for-ticket", help="Run webhook for a specific ticket. Needs the ticket id")
    parser.add_argument("--check-all-tickets", action="store_true", help="Iterate over all tickets and run webhook for each ticket")
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
    elif args.remove_expired_keys:
        remove_expired_pgp_keys()
    elif args.import_thunderbird:
        import_pgp_keys_from_thunderbird(args.import_thunderbird)
    elif args.run_webhook_for_ticket:
        ticket_id = args.run_webhook_for_ticket
        run_webhook_for_ticket(ticket_id)
    elif args.check_all_tickets:
        check_all_tickets()
    elif args.version:
        print(f"{sys.argv[0]} {get_version()}")
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
