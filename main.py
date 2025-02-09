import json
import logging

from config import init_config, get_config
from datetime import datetime
from dbx import find_latest_yfull
from dropbox import Dropbox
from dropbox.oauth import OAuth2FlowNoRedirectResult
from gsheet import (
    create_sheets,
    store_budgets,
    store_categories,
    store_transactions,
    is_knowledge_up_to_date,
    update_saved_knowledge,
)
from gspread import oauth
from ksh import update_inflation_rate
from mnb import update_currency_rate


if __name__ == "__main__":
    init_config()
    config = get_config()
    logging.basicConfig(level=config["LOG_LEVEL"].upper())

    logging.info("Initializing Dropbox")
    with open(config["DROPBOX_OAUTH_TOKEN_FILENAME"], "r") as fp:
        token = json.load(fp)
        dbx_oauth_token = OAuth2FlowNoRedirectResult(
            token["access_token"],
            token["account_id"],
            token["user_id"],
            token["refresh_token"],
            datetime.fromisoformat(token["expires_at"]),
            token["scope"],
        )
        dbx = Dropbox(
            oauth2_access_token=dbx_oauth_token.access_token,
            oauth2_refresh_token=dbx_oauth_token.refresh_token,
            oauth2_access_token_expiration=dbx_oauth_token.expires_at,
            app_key=config["DROPBOX_APP_KEY"],
            app_secret=config["DROPBOX_APP_SECRET"],
            scope=dbx_oauth_token.scope.split(),
        )

    logging.info("Initializing Google")
    gc = oauth(
        credentials_filename=config["GSPREAD_CREDENTIALS_FILENAME"],
        authorized_user_filename=config["GSPREAD_AUTHORIZED_USER_FILENAME"],
    )

    main_budget_data = find_latest_yfull(dbx, config["BUDGET"])

    logging.info("Opening spreadsheet")
    spreadsheet = gc.open(config["GSPREAD_SHEET_NAME"])

    create_sheets(spreadsheet, list(config["BUDGET_EXTRA_TXN"].keys()))
    if is_knowledge_up_to_date(
        main_budget_data, spreadsheet.worksheet("YNAB/Transactions")
    ):
        logging.info("Sheet is up to date, skipping")
    else:
        store_categories(main_budget_data, spreadsheet.worksheet("YNAB/Categories"))
        store_budgets(main_budget_data, spreadsheet.worksheet("YNAB/Budgets"))
        store_transactions(main_budget_data, spreadsheet.worksheet("YNAB/Transactions"))
        update_saved_knowledge(
            main_budget_data, spreadsheet.worksheet("YNAB/Transactions")
        )

    for cur, budget in config["BUDGET_EXTRA_TXN"].items():
        data = find_latest_yfull(dbx, budget)
        if is_knowledge_up_to_date(
            data, spreadsheet.worksheet("YNAB/Transactions{}".format(cur))
        ):
            logging.info("Sheet is up to date, skipping")
        else:
            store_transactions(
                data, spreadsheet.worksheet("YNAB/Transactions{}".format(cur))
            )
            update_saved_knowledge(
                data, spreadsheet.worksheet("YNAB/Transactions{}".format(cur))
            )

    for cur, _ in config["BUDGET_EXTRA_TXN"].items():
        update_currency_rate(cur, spreadsheet.worksheet("MNB"))

    update_inflation_rate(spreadsheet.worksheet("KSH"))
