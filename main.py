from config import init_config, get_config
from dropbox import Dropbox


if __name__ == "__main__":
    init_config()
    config = get_config()
    dbx = Dropbox(config["DROPBOX_ACCESS_TOKEN"])
