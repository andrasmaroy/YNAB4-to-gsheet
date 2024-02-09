from config import init_config, get_config
from dbx import find_latest_yfull
from dropbox import Dropbox
from gsheet import create_sheets
from gspread import oauth


if __name__ == "__main__":
    init_config()
    config = get_config()
    dbx = Dropbox(config["DROPBOX_ACCESS_TOKEN"])
    gc = oauth(
        credentials_filename=config["GSPREAD_CREDENTIALS_FILENAME"],
        authorized_user_filename=config["GSPREAD_AUTHORIZED_USER_FILENAME"],
    )
    main_budget_data = find_latest_yfull(dbx, config["BUDGET"])
    spreadsheet = gc.open(config["GSPREAD_SHEET_NAME"])
    create_sheets(spreadsheet, list(config["BUDGET_EXTRA_TXN"].keys()))
