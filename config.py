from pconf import Pconf


def init_config():
    Pconf.env(
        match="^BUDGET_EXTRA_TXN__[A-Z]{3}$",
        separator="__",
        whitelist=[
            "BUDGET",
            "DROPBOX_ACCESS_TOKEN",
            "GSPREAD_AUTHORIZED_USER_FILENAME",
            "GSPREAD_CREDENTIALS_FILENAME",
            "GSPREAD_SHEET_NAME",
        ],
    )

    Pconf.defaults(
        {
            "GSPREAD_AUTHORIZED_USER_FILENAME": "/run/secrets/token.json",
            "GSPREAD_CREDENTIALS_FILENAME": "/run/secrets/credentials.json",
        }
    )


def get_config():
    return Pconf.get()
