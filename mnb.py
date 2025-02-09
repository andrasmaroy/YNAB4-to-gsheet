import gspread
import logging
import re
import requests

from datetime import datetime, timedelta
from lxml import etree


def update_currency_rate(currency: str, worksheet: gspread.worksheet.Worksheet):
    column = worksheet.find(currency, 1)
    if column is None:
        logging.warning("Currency {} not found in MNB sheet".format(currency))
        return

    column = column.col
    last_row = worksheet.findall(re.compile(r"^.+$"), in_column=column)[-1].row

    last_date = worksheet.get(gspread.utils.rowcol_to_a1(last_row, 1))[0][0]
    from_date = datetime.strptime(last_date, "%Y.%m.%d.").date() + timedelta(days=1)
    to_date = datetime.today().strftime("%Y.%m.%d.")

    url = "https://www.mnb.hu/arfolyam-tablazat"
    params = {
        "deviza": "rbCustom",
        "datefrom": from_date,
        "datetill": to_date,
        "order": 1,
        "customdeviza[]": currency,
    }

    logging.info(
        "Fetching MNB data for {}, from {} until {}".format(
            currency, from_date, to_date
        )
    )
    response = requests.get(url, params=params)
    response.raise_for_status()

    root = etree.HTML(response.text)
    content = root.xpath("//table[1]/tbody/tr")

    if last_row + len(content) > worksheet.row_count:
        logging.info("Adding additional {} rows to MNB sheet".format(len(content)))
        worksheet.add_rows(len(content))

    update_data = []

    for i, elem in enumerate(content, start=1):
        mnb_date = elem.getchildren()[0].text
        rate = elem.getchildren()[1].text
        update_data.append(
            {
                "range": gspread.utils.rowcol_to_a1(last_row + i, 2),
                "values": [[mnb_date]],
            }
        )
        update_data.append(
            {
                "range": gspread.utils.rowcol_to_a1(last_row + i, column),
                "values": [[rate]],
            }
        )

    logging.debug("Batch update data: {}".format(update_data))
    if update_data:
        worksheet.batch_update(
            update_data, value_input_option=gspread.utils.ValueInputOption.user_entered
        )

    logging.info("MNB data for {} updated".format(currency))
