# Zammad PGP import - Webhook & cli tools

### The what and why
Zammad helpdesk supports PGP encryption and it works quite nice. But the current workflow of importing PGP keys is a bit cumbersome. Also, agents need special admin privileges to import PGP keys. This project provides a webhook that automatically imports PGP keys when some checks are completed. You need to configure a Zammad webhook that sends a POST request to this webhook for each new incoming ticket. The webhook automatically imports PGP keys attached to the ticket or keys found on a keyserver.

There are also some cli tools to import PGP keys manually or import PGP keys from a Thunderbird profile.

### How does it work?
1) Zammad receives a new ticket
2) Zammad sends a webhook (must be configured manually in Zammad)
3) This projects contains the backend of the webhook. There are two supported scenarios where PGP keys are imported:
    - The email has a PGP key attached. If sender's email address matches with the one of the attached PGP key, the Zammad API is used to import the key
    - If the email is PGP-encrypted: Use a PGP keyserver to find a valid PGP key and import it.

#### Quickstart

```bash
pip install zammad-pgp-import

cat secrets.source
export DEBUG="1"
export ZAMMAD_BASE_URL="https://tickets.example.org"
export ZAMMAD_TOKEN="auth token"
export BASIC_AUTH_USER="test"
export BASIC_AUTH_PASSWORD="test"
export LISTEN_HOST="0.0.0.0"
export LISTEN_PORT="22000"

source secrets.source

zammad-pgp-import -h
usage: zammad-pgp-import [-h] [--backend] [--import-key IMPORT_KEY] [--import-thunderbird IMPORT_THUNDERBIRD] [--version]

Zammad webhook that automatically imports PGP keys. There is also a cli to import PGP keys manually. Configuration is done via environment variables. Docs can be found here: https://github.com/kmille/zammad-pgp-auto-import

options:
  -h, --help            show this help message and exit
  --backend, -b         run webhook backend
  --import-key, -i IMPORT_KEY
                        use key server to import pgp key by supplied email/key id
  --import-thunderbird, -t IMPORT_THUNDERBIRD
                        Needs a global-messages-db.sqlite file. Get all email addresses from global-messages-db.sqlite (part of a Thunderbird profile). Try to find a PGP key and import it to Zammad. As there is rate limiting, we sleep
                        for a long time after each attempt. So you may want to run this on a server
  --version             show version
```

### Configuration

Configuration of this tool is done via environment variables.

| name of environment variable | meaning                                                     | required |
| ---------------------------- | ----------------------------------------------------------- | -------- |
| DEBUG                        | set 1 to enable debug log                                   | no       |
| ZAMMAD_BASE_URL              | url of zammad instance, like https://tickets.example.org    | yes      |
| ZAMMAD_TOKEN                 | auth token/api key with enough permissions (see below)      | yes      |
| BASIC_AUTH_USER              | username for webhook and monitoring endpoint authentication | yes      |
| BASIC_AUTH_PASSWORD          | password for webhook and monitoring endpoint authentication | yes      |
| LISTEN_HOST                  | defaults to "127.0.0.1"                                     | no       |
| LISTEN_PORT                  | defaults to 22000                                           | no       |
| KEY_SERVER                   | default PGP key server, default is https://keys.openpgp.org | no       |

### Zammad Webhook configuration

1) Define webhook

![](/docs/screenshot_webhook.png)

2) Create trigger (triggers webhook for every new ticket)

![](/docs/screenshot_trigger.png)

To get an API key for a production environment, I recommend:

1) Create a new Zammad user, only used for the API
2) Create a new role for the webhook user
3) The role needs permissions to read tickets for all groups (to download ticket attachments) and the integration permission (to import PGP keys)

### How to use it as a dev?

It's written in python and uses [poetry](https://python-poetry.org/) to manage dependencies.

```bash
poetry install
source secrets.txt (see above)
poetry run python zammad_pgp_import/__init__.py --help
```

### How to use it with Docker

You can use the [Github Docker image](https://github.com/kmille/zammad-pgp-auto-import/pkgs/container/zammad-pgp-import): 

> docker pull ghcr.io/kmille/zammad-pgp-import

Or the [Dockerhub image](https://hub.docker.com/r/kmille2/zammad-pgp-import):

> docker pull kmille2/zammad-pgp-import

You can use this docker-compose.yml:

```yaml
services:
   zammad-pgp-import:
    image: ghcr.io/kmille/zammad-pgp-import
    environment:
      DEBUG: "1"
      BASIC_AUTH_USER: "test"
      BASIC_AUTH_PASSWORD: "test"
      ZAMMAD_BASE_URL: "https://tickets.example.org"
      ZAMMAD_TOKEN: "token"
    security_opt:
      - no-new-privileges
    cap_drop:
      - ALL
```

### Example output
1) Run the webhook backend

```bash
kmille@spring:~/projects/zammad-pgp-import# poetry run zammad-pgp-import --backend
[2025-08-14 17:56:01,279  INFO] Starting webhook backend on 0.0.0.0:22000 (version 0.1.1a5, debug=True)
[2025-08-14 17:56:01,281  INFO] Serving on http://0.0.0.0:22000

...

zammad-pgp-import-1  | [2025-08-04 12:08:46,377  INFO] Received a new Ticket: https://tickets.example.org/#ticket/zoom/133 (from=<redacted>, is_encrypted=False)
zammad-pgp-import-1  | [2025-08-04 12:08:46,377 DEBUG] This attachment is not a PGP key (Content-Type='')                                                                                                                                      
zammad-pgp-import-1  | [2025-08-04 12:08:46,377 DEBUG] No PGP key was attached to this email                                                                                                                                                   
zammad-pgp-import-1  | [2025-08-04 12:08:46,377  INFO] Ticket does not have a PGP key attached. It is also not encrypted and/or PGP key was not found on a keysever                  

zammad-pgp-import-1  | [2025-08-05 13:24:06,815  INFO] Received a new Ticket: https://tickets.example.org/#ticket/zoom/139 (from=<redacted>, is_encrypted=True)
zammad-pgp-import-1  | [2025-08-05 13:24:06,815  INFO] Seems like a PGP key is attached to this email
zammad-pgp-import-1  | [2025-08-05 13:24:06,816 DEBUG] Downloading ticket attachment using Zammad API
zammad-pgp-import-1  | [2025-08-05 13:24:06,972 DEBUG] Successfully downloaded email attachment
zammad-pgp-import-1  | [2025-08-05 13:24:06,987 DEBUG] Importing PGP key using Zammad API
zammad-pgp-import-1  | [2025-08-05 13:24:07,126  INFO] Successfully imported pgp key <redacted> for email <redacted>

```

2. Import PGP key via cli

```bash
[2025-08-14 17:58:26,621  INFO] Found key: PGPKey (emails=jelle@vdwaa.nl,jelle@archlinux.org,jvanderwaa@redhat.com fingerprint=E499C79F53C96A54E572FEE1C06086337C50773E
[2025-08-14 17:58:26,621  INFO] Found key: PGPKey (emails=jelle@vdwaa.nl,jelle@archlinux.org,jvanderwaa@redhat.com fingerprint=E499C79F53C96A54E572FEE1C06086337C50773E
[2025-08-14 17:58:26,626 DEBUG] Importing PGP key using Zammad API
[2025-08-14 17:58:26,789  INFO] Successfully imported PGP key
kmille@spring:~/projects/zammad-pgp-import# poetry run zammad-pgp-import -i jelle@archlinux.org
[2025-08-14 17:58:35,483  INFO] Found key: PGPKey (emails=jelle@vdwaa.nl,jelle@archlinux.org,jvanderwaa@redhat.com fingerprint=E499C79F53C96A54E572FEE1C06086337C50773E
[2025-08-14 17:58:35,488 DEBUG] Importing PGP key using Zammad API
[2025-08-14 17:58:35,598 ERROR] Could not import PGP key: Key was already imported. API response: Fingerprint There is already a PGP key with the same fingerprint.
```

3. Import PGP keys from Thunderbird profile

```bash
kmille@spring:~/projects/zammad-pgp-import# poetry run python zammad_pgp_import/__init__.py -t ~/.config/Thunderbird-LG/.thunderbird/....default-release/global-messages-db.sqlite                                                        
[2025-08-14 17:59:34,866 DEBUG] Read email: <redacted@bla.com>
...
[2025-08-14 18:00:45,224  INFO] Checking mail 1/3460: <redacted @ ....>
[2025-08-14 18:00:45,272 DEBUG] API error message: No key found for email address < redacted>
[2025-08-14 18:00:45,273  INFO] Could not find a PGP key for < redacted > using keyserver https://keys.openpgp.org
...
[2025-08-04 10:27:53,933  INFO] Doing 6/3448: <redacted>
[2025-08-04 10:27:53,969  INFO] Found key: PGPKey <redacted>
[2025-08-04 10:27:53,970 DEBUG] Importing PGP key using Zammad API
[2025-08-04 10:27:54,144  INFO] Successfully imported PGP key
```

### Monitoring

You can monitor the webhook:

```
curl https://webhook.example.org/status -u webhook
Enter host password for user 'webhook':
{"status":"ok"}
```

In case of at least one error, `{"status":"failed"}` is returned. Both responses use status code 200. The authentication credentials are the same like the ones for the webhook endpoint. In case of an error, check the logs and restart the webhook.

### KNOWN ISSUES/TODOs

- TODO: handle expired PGP keys (do not import them)
- TODO: improve tests
- Please check this Zammad PGP issue (was fixed, but it is not released yet I think): https://github.com/zammad/zammad/issues/5170
- Right now, agents don't get PGP encrypted notifications, even if they have a PGP key imported for that email address
