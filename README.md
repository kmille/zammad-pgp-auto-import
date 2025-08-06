# Zammad PGP import - Webhook & cli tools

### The what and why
Zammad helpdesk supports PGP encryption and it works quite nice. But the current workflow of importing PGP keys is a bit cumbersome. Also, agents need special admin privileges to import PGP keys. This project provides a webhook that automatically imports PGP keys when some checks are completed. The Zammad webhook triggers for each new incoming ticket. It automatically imports PGP keys attached to the ticket or found on a keyserver.

There are also some cli tools to import PGP manually or import PGP keys from a Thunderbird directory structure.

### How does it work?
1) Zammad receives a new ticket
2) Zammad sends a webhook (must be configured manually in Zammad)
3) This projects contains the backend. There are two supported scenarios where PGP keys are imported:
    - The email has a PGP key attached. If sender's email matches with the one of the attached PGP key, the Zammad API is used to import the key
    - If the email is PGP-encrypted: Use a PGP keyserver to find a valid PGP key and import it.

### How to use it as a dev?
It's written in python and uses [poetry](https://python-poetry.org/) to manage dependencies.

```bash
poetry install

cat secrets.source
export DEBUG="1"
export ZAMMAD_BASE_URL="https://tickets.example.org"
export ZAMMAD_TOKEN="auth token"
export BASIC_AUTH_USER="test"
export BASIC_AUTH_PASSWORD="test"
export LISTEN_HOST="0.0.0.0"
export LISTEN_PORT="22000"


source secrets.source
poetry run python zammad_pgp_import/__init__.py --help

TODO: here help text
```

### Configuration

Configuration is done via environment variables.

| name of environment variable | meaning                                                     | required |
| ---------------------------- | ----------------------------------------------------------- | -------- |
| DEBUG                        | set 1 to enable debug log                                   | no       |
| ZAMMAD_BASE_URL              | url of zammad instance, like https://tickets.example.org    | yes      |
| ZAMMAD_TOKEN                 | auth token with enough permissions                          | yes      |
| BASIC_AUTH_USER              | username for webhook and monitoring endpoint authentication | yes      |
| BASIC_AUTH_PASSWORD          | password for webhook and monitoring endpoint authentication | yes      |
| LISTEN_HOST                  | defaults to "127.0.0.1"                                     | no       |
| LISTEN_PORT                  | defaults to 22000                                           | no       |
| KEY_SERVER                   | default PGP key server, default is https://keys.openpgp.org | no       |


https://docs.zammad.org/en/latest/api/intro.html

### How to use it with pip?

### How to use it with Docker





### Docker



### Example output
 you have to specify webhook



Monitoring



### KNOWN  ISSUES

- PGP: subject i identifier
- benachrichtigungen
