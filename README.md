# Zammad PGP import webhook

### TLDR:
This is a Zammad webhook that gets triggered for each new incoming ticket. It automatically imports PGP keys attached to the ticket or found on a keyserver.

### The problem it solves
Zammad supports PGP encryption. The current workflow of importing PGP keys is suboptimal. Agents need special admin privileges to import PGP keys. This webhook automatically imports PGP keys when some checks are completed.

### How does it work?
1) Zammad gets a new ticket
2) It sends you a webhook
3) This projects runs the backend of the webhook. There are two supported scenarios:
    - The email/ticket has a PGP key attached. If sender's email matches with the one of the PGP key => use Zammad API to import PGP key
    - If the email is PGP-encrypted: Use a keyserver to find a valid PGP

### How to use it?
It's based on python and [poetry](https://python-poetry.org/).

```
poetry install
poetry run python zammad_pgp_import/__init__.py
```

Configuration is done via environment variables.




### Configuration

| name of environment variable | meaning                                                  | required |
| ---------------------------- | -------------------------------------------------------- | -------- |
| ZAMMAD_BASE_URL              | url of zammad instance, like https://tickets.example.org | yes      |
| ZAMMAD_TOKEN                 | auth token with enough permissions                       | yes      |
| BASIC_AUTH_USER              | username for webhook and monitoring authentication       | yes      |
| BASIC_AUTH_PASSWORD          | password for webhook and monitoring authentication       | yes      |
| LISTEN_HOST                  | defaults to "127.0.0.1"                                  | no       |
| LISTEN_PORT                  | defaults to 22000                                        | no       |
| DEBUG                        | set 1 to enable debug log                                | no       |
| KEY_SERVER                   | default is set to https://keys.openpgp.org               | no       |


https://docs.zammad.org/en/latest/api/intro.html



### Monitoring



### Docker



### Example output
