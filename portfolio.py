import csv
import gspread
import logging
import requests

PORTFOLIO_REGIONS = [
    "USA",
    "Europe",
    "Emerging Markets",
    "Japan",
    "Pacific ex Japan",
    "World Small Cap",
]


def get_ratios(overhead=0.1):
    url = "https://marketcaps.site/indices.csv"
    r = requests.get(url)
    r.raise_for_status()
    text = r.iter_lines(decode_unicode=True)
    reader = csv.reader(text, delimiter=",")
    results = {}
    total = 0
    for row in reader:
        if len(row) > 1 and row[0] in PORTFOLIO_REGIONS:
            total += float(row[1])
            results[row[0]] = float(row[1])
    for key, value in results.items():
        results[key] = round((value / total) * (1 - overhead), 4)
    return results


def update_portfolio_ratios(worksheet: gspread.worksheet.Worksheet):
    try:
        ratios = get_ratios()
    except requests.exceptions.RequestException as e:
        logging.error("Failed to fetch portfolio ratios: {}".format(e))
        return

    logging.info("Updating portfolio ratios: {}".format(ratios))

    cell_list = []
    for region, ratio in ratios.items():
        cell = worksheet.find(region, in_column=15)
        if cell is None:
            logging.warning("Region {} not found in portfolio sheet".format(region))
            continue
        cell_to_update = worksheet.cell(cell.row, 17)
        cell_to_update.value = ratio
        cell_list.append(cell_to_update)

    logging.info("Updating cells: {}".format(cell_list))
    worksheet.update_cells(cell_list, gspread.utils.ValueInputOption.user_entered)
