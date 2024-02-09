from dropbox.exceptions import ApiError
import json


def find_latest_yfull(dbx, budget):
    # Find data folder from ymeta
    _, content = dbx.files_download("/YNAB/{}/Budget.ymeta".format(budget))
    data_folder = "/YNAB/{}/{}".format(
        budget, json.loads(content.content)["relativeDataFolderName"]
    )
    mod_times = {}

    # Gather modification dates for yfull files
    for device in dbx.files_list_folder(data_folder).entries:
        try:
            mod_times[device.name] = dbx.files_get_metadata(
                "{}/{}/Budget.yfull".format(data_folder, device.name)
            ).server_modified
        except ApiError:
            pass

    # Find the yfull file with the latest modification date and return its contents
    latest = sorted(mod_times.items(), key=lambda item: item[1])[-1][0]
    _, content = dbx.files_download("{}/{}/Budget.yfull".format(data_folder, latest))
    return json.loads(content.content)
