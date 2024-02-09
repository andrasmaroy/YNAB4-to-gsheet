from config import init_config, get_config
from dbx import find_latest_yfull
from dropbox import Dropbox


if __name__ == "__main__":
    init_config()
    config = get_config()
    dbx = Dropbox(config["DROPBOX_ACCESS_TOKEN"])
    main_budget_data = find_latest_yfull(dbx, config["BUDGET"])
