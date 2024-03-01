from pconf import Pconf


def init_config():
    Pconf.env(
        match="^BUDGET_EXTRA_TXN__[A-Z]{3}$",
        separator="__",
        whitelist=[
            "BUDGET",
            "DROPBOX_APP_KEY",
            "DROPBOX_APP_SECRET",
            "GSPREAD_AUTHORIZED_USER_FILENAME",
            "GSPREAD_CREDENTIALS_FILENAME",
            "GSPREAD_SHEET_NAME",
            "LOG_LEVEL",
        ],
    )

    Pconf.defaults(
        {
            "DROPBOX_OAUTH_TOKEN_FILENAME": "/run/secrets/token-dropbox.json",
            "GSPREAD_AUTHORIZED_USER_FILENAME": "/run/secrets/token.json",
            "GSPREAD_CREDENTIALS_FILENAME": "/run/secrets/credentials.json",
            "LOG_LEVEL": "INFO",
        }
    )


def get_config():
    return Pconf.get()
