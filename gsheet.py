import gspread


def create_sheets(spreadsheet: gspread.Spreadsheet, extra_txn_curs: list[str]):
    ynab_sheets = [
        {"name": "Categories", "rows": 4, "cols": 1},
        {"name": "Budgets", "rows": 2, "cols": 2},
        {"name": "Transactions", "rows": 1, "cols": 7},
    ]
    for cur in extra_txn_curs:
        ynab_sheets.append({"name": "Transactions{}".format(cur), "rows": 1, "cols": 7})

    for sheet in ynab_sheets:
        try:
            # Try to get the worksheet; if it doesn't exist, create it
            spreadsheet.worksheet("YNAB/{}".format(sheet["name"]))
        except gspread.exceptions.WorksheetNotFound:
            spreadsheet.add_worksheet(
                title="YNAB/{}".format(sheet["name"]),
                rows=sheet["rows"],
                cols=sheet["cols"],
            )


def store_categories(data, worksheet: gspread.worksheet.Worksheet):
    pass


def store_transactions(data, worksheet: gspread.worksheet.Worksheet):
    pass


def store_budgets(data, worksheet: gspread.worksheet.Worksheet):
    pass
