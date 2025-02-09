import csv
import gspread
import logging
import requests

from io import StringIO


def fetch_data(url):
    logging.info("Fetching KSH data from {}".format(url))
    response = requests.get(url)

    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        logging.error("Failed to fetch KSH data: {}".format(e))
        return None

    data = response.text
    reader = csv.reader(StringIO(data), delimiter=";")
    return list(reader)


def update_inflation_rate(worksheet: gspread.worksheet.Worksheet):
    url = "https://www.ksh.hu/stadat_files/ara/hu/ara0001.csv"
    data = fetch_data(url)
    if data is None:
        return

    # Remove header
    data = data[2:]
    # We only need the first 2 columns
    for i in range(len(data)):
        data[i] = data[i][:2]

    next_year = int(data[len(data) - 1][0]) + 1

    current_inflation = calculate_inflation_current_year(str(next_year))
    if current_inflation is not None:
        data.append(
            [str(next_year), str(round(current_inflation, 1)).replace(".", ",")]
        )

    offset = 4
    records = worksheet.get_values("A{}:B".format(offset))
    # Convert records to a dictionary for easier comparison
    dict1 = {row[0]: row[1] for row in records}

    update_data = []

    for row in data:
        year, inflation = row[0], row[1]
        if year not in dict1:
            # Add as a new line to the sheet
            r = len(records) + offset
            update_data.append(
                {"range": "A{}:B{}".format(r, r), "values": [[year, inflation]]}
            )
        elif dict1[year] != inflation:
            # Find row and add to updates
            logging.info(
                "Inflation rate for year {} changed from {} to {}".format(
                    year, dict1[year], inflation
                )
            )
            r = list(dict1.keys()).index(year) + offset
            update_data.append(
                {"range": "A{}:B{}".format(r, r), "values": [[year, inflation]]}
            )

    logging.debug("Batch update data: {}".format(update_data))
    if update_data:
        worksheet.batch_update(
            update_data, value_input_option=gspread.utils.ValueInputOption.user_entered
        )
        logging.info("KSH inflation data updated")
    else:
        logging.info("KSH inflation data is up to date")


def calculate_inflation_current_year(year):
    # Fetch data from the first URL
    url = "https://www.ksh.hu/stadat_files/ara/hu/ara0039.csv"
    data = fetch_data(url)
    if data is None:
        return None

    # Remove header
    data = data[2:]

    # We only need the first 3 columns
    for i in range(len(data)):
        data[i] = data[i][:3]

    inflation_values = []
    current_year = None

    for row in data:
        if row[0]:
            current_year = row[0].strip().replace(".", "")
        if not row[0] and current_year:
            row[0] = current_year

        if current_year != year:
            continue

        try:
            inflation = float(row[2].replace(",", "."))
            inflation_values.append(inflation)
        except ValueError:
            continue

    if not inflation_values:
        return None

    return sum(inflation_values) / len(inflation_values)
