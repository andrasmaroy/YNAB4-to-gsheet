import gspread

from datetime import datetime


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
    categories = [[], [], [], []]
    for master_category in data.get("masterCategories", []):
        # Empty master category, skip
        if (
            master_category.get("subCategories") is None
            or len(master_category.get("subCategories")) == 0
        ):
            continue

        # Deleted master category, skip
        if master_category.get("isTombstone", False):
            continue

        # All subcategories deleted, skip
        subcategories = list(
            filter(
                lambda sc: not sc.get("isTombstone", False),
                master_category.get("subCategories"),
            )
        )
        if len(subcategories) == 0:
            continue

        categories[0].append(master_category.get("entityId"))
        categories[1].append(master_category.get("name"))
        for i, subcategory in enumerate(subcategories):
            if i > 0:
                categories[0].append(master_category.get("entityId"))
                categories[1].append("")
            categories[2].append(subcategory.get("entityId"))
            categories[3].append(subcategory.get("name"))

    worksheet.clear()
    worksheet.unmerge_cells("2:2")
    worksheet.resize(4, len(categories[0]))
    worksheet.update(categories)
    worksheet.hide_rows(0, 1)
    worksheet.hide_rows(2, 3)

    # Merge master category cells over their subcategories
    start_col = -1
    end_col = -1
    for i, master_category in enumerate(categories[1]):
        if master_category != "":
            if start_col == -1:
                start_col = i
            else:
                end_col = i
        if master_category == "":
            continue
        if start_col != -1 and end_col != -1:
            start_cell = gspread.utils.rowcol_to_a1(2, start_col + 1)
            end_cell = gspread.utils.rowcol_to_a1(2, end_col)
            worksheet.merge_cells("{}:{}".format(start_cell, end_cell))

            start_col = i
            end_col = -1


def store_budgets(data, worksheet: gspread.worksheet.Worksheet):
    budgets = [["", ""], ["", ""]]

    first_transaction_date = datetime.strptime(
        data.get("transactions")[0].get("date"), "%Y-%m-%d"
    )
    for budget in data.get("monthlyBudgets"):
        # Nothing budgeted for the month, skip
        if len(budget.get("monthlySubCategoryBudgets")) == 0:
            continue

        # Only deleted budgets for the month, skip
        if (
            len(
                list(
                    filter(
                        lambda mscb: not mscb.get("isTombstone", False)
                        and mscb.get("budgeted", 0) > 0,
                        budget.get("monthlySubCategoryBudgets"),
                    )
                )
            )
            == 0
        ):
            continue

        # Budget from before starting the budget, skip
        if datetime.strptime(budget.get("month"), "%Y-%m-%d") < first_transaction_date:
            continue

        budgets[0].append(budget.get("entityId"))
        budgets[1].append(budget.get("month"))
        for subcategory_budget in budget.get("monthlySubCategoryBudgets"):
            if subcategory_budget.get("isTombstone", False):
                continue
            row_to_insert = -1
            for i, row in enumerate(budgets):
                if row[0] == subcategory_budget.get("categoryId"):
                    row_to_insert = i
                    break
            if row_to_insert == -1:
                budgets.append([subcategory_budget.get("categoryId"), ""])
                row_to_insert = len(budgets) - 1

            column_to_insert = len(budgets[0]) - 1
            if len(budgets[row_to_insert]) < column_to_insert:
                spaces_needed = column_to_insert - len(budgets[row_to_insert])
                budgets[row_to_insert].extend([0 for _ in range(spaces_needed)])
            budgets[row_to_insert].append(subcategory_budget.get("budgeted"))
    budgets[2][1] = "=ARRAYFORMULA(HLOOKUP(A3:A;'YNAB/Categories'!A$3:ZZ$4;2;false))"

    worksheet.clear()
    worksheet.resize(len(budgets), len(budgets[0]))
    worksheet.update(budgets, raw=False)
    worksheet.freeze(2, 2)
    worksheet.hide_rows(0, 1)
    worksheet.hide_columns(0, 1)


def store_transactions(data, worksheet: gspread.worksheet.Worksheet):
    pass
