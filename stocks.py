import gspread
import logging
import re
import yfinance as yf

from datetime import datetime, timedelta


class Stocks(object):
    def __init__(self):
        self.portfolio = {}
        self.prices = {}
        self.targets = {}
        self.budget = 0
        self.tolerance = 0.01
        self.penalty_scaling_factor = 1000
        self.spreadsheet = None

    def add_to_portfolio(self, data: dict):
        portfolio = {}
        filter = re.compile(r"^-?\d+ [A-Z]+.[A-Z]+$")
        for txn in data["transactions"]:
            if "checkNumber" not in txn:
                continue
            if not filter.match(txn["checkNumber"]):
                continue
            parts = txn["checkNumber"].split(" ")
            if len(parts) != 2:
                continue
            elif parts[1] not in portfolio:
                portfolio[parts[1]] = int(parts[0])
            else:
                portfolio[parts[1]] += int(parts[0])
        # portfolio = dict((k, v) for k, v in portfolio.items() if v > 0)
        self.portfolio |= portfolio

    def get_historical_rates(self, worksheet):
        """
        Fetch and store historical stock prices in a Google Sheet.

        Sheet structure:
        - Column A: Dates (A3 = formula for last date, A4+ = historical dates)
        - Row 1: Ticker symbols (yfinance format)
        - Row 4+: Price data
        """
        # Step 1: Parse existing sheet structure
        sheet_dates, sheet_tickers, date_to_row = self._parse_sheet_structure(worksheet)

        # Step 2: Identify new vs existing tickers
        new_tickers, existing_tickers = self._identify_ticker_operations(sheet_tickers)

        if not new_tickers and not existing_tickers:
            logging.info("No tickers to process")
            return

        # Step 3: Batch fetch data from yfinance
        all_ticker_data = self._fetch_ticker_data(
            worksheet, new_tickers, existing_tickers, sheet_dates, sheet_tickers
        )

        if not all_ticker_data:
            logging.warning("No data fetched from yfinance")
            return

        # Step 4: Reconcile dates and insert rows if needed
        final_dates, date_to_row = self._reconcile_dates(
            worksheet, sheet_dates, all_ticker_data, date_to_row
        )

        # Step 5: Prepare batch updates
        updates = self._prepare_batch_updates(
            worksheet,
            new_tickers,
            existing_tickers,
            all_ticker_data,
            sheet_tickers,
            date_to_row,
        )

        # Step 6: Execute batch update
        if updates:
            logging.info("Executing batch update with {} changes".format(len(updates)))
            worksheet.batch_update(
                updates, value_input_option=gspread.utils.ValueInputOption.user_entered
            )
            logging.info("Stock price data updated successfully")
        else:
            logging.info("No updates to apply")

    def _parse_sheet_structure(self, worksheet):
        """Parse existing dates and tickers from the sheet."""
        logging.info("Parsing sheet structure")

        # Get all dates from column A (starting at row 4)
        date_cells = worksheet.get("A4:A")
        sheet_dates = []
        date_to_row = {}

        for i, row in enumerate(date_cells, start=4):
            if row and row[0]:
                # Convert YYYY.MM.DD. to YYYY-MM-DD for internal processing
                date_str = self._convert_sheet_date_to_yf(row[0])
                sheet_dates.append(date_str)
                date_to_row[date_str] = i

        # Get all tickers from row 1 (starting at col 2)
        ticker_cells = worksheet.get("1:1")
        sheet_tickers = {}

        if ticker_cells and len(ticker_cells[0]) > 1:
            for col, ticker in enumerate(ticker_cells[0][1:], start=2):
                if ticker:
                    sheet_tickers[ticker] = col

        logging.info(
            "Found {} dates and {} tickers in sheet".format(
                len(sheet_dates), len(sheet_tickers)
            )
        )

        return sheet_dates, sheet_tickers, date_to_row

    def _convert_sheet_date_to_yf(self, date_str):
        """Convert YYYY.MM.DD. format to YYYY-MM-DD format for yfinance."""
        date_obj = datetime.strptime(date_str, "%Y.%m.%d.")
        return date_obj.strftime("%Y-%m-%d")

    def _identify_ticker_operations(self, sheet_tickers):
        """Identify which tickers need backfill vs update."""
        logging.info("Identifying ticker operations")

        new_tickers = []
        existing_tickers = []

        for ticker in self.portfolio.keys():
            if ticker in sheet_tickers:
                existing_tickers.append(ticker)
            else:
                new_tickers.append(ticker)

        logging.info(
            "New tickers: {}, Existing tickers: {}".format(
                len(new_tickers), len(existing_tickers)
            )
        )

        return new_tickers, existing_tickers

    def _detect_all_nan_tickers(self, data, all_tickers):
        """Detect tickers where all Close values are NaN."""
        nan_tickers = []

        for ticker in all_tickers:
            # Single ticker: column is "Close", multiple tickers: column is ("Close", ticker)
            close_col = "Close" if len(all_tickers) == 1 else ("Close", ticker)

            if close_col in data.columns and data[close_col].isna().all():
                nan_tickers.append(ticker)

        return nan_tickers

    def _fetch_ticker_data(
        self, worksheet, new_tickers, existing_tickers, sheet_dates, sheet_tickers
    ):
        """Fetch historical data for all tickers."""
        logging.info("Fetching data from yfinance")

        # Determine date ranges for fetching
        all_tickers = new_tickers + existing_tickers
        fetch_params = {}

        # For new tickers: start from A4 date or earliest available
        if new_tickers:
            if sheet_dates:
                # sheet_dates already in YYYY-MM-DD format
                start_date = sheet_dates[0]
            else:
                # Sheet is empty, use a reasonable default
                start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

            for ticker in new_tickers:
                fetch_params[ticker] = start_date

        # For existing tickers: find last populated cell and fetch from next day
        for ticker in existing_tickers:
            col = sheet_tickers[ticker]
            try:
                last_cells = worksheet.findall(re.compile(r"^.+$"), in_column=col)
                if last_cells:
                    last_row = last_cells[-1].row
                    last_date_str = (
                        sheet_dates[last_row - 4]
                        if last_row - 4 < len(sheet_dates)
                        else None
                    )

                    if last_date_str:
                        last_date = datetime.strptime(last_date_str, "%Y-%m-%d")
                        fetch_params[ticker] = (last_date + timedelta(days=1)).strftime(
                            "%Y-%m-%d"
                        )
                    else:
                        fetch_params[ticker] = sheet_dates[0] if sheet_dates else None
                else:
                    fetch_params[ticker] = sheet_dates[0] if sheet_dates else None
            except Exception as e:
                logging.warning("Error finding last date for {}: {}".format(ticker, e))
                fetch_params[ticker] = sheet_dates[0] if sheet_dates else None

        # Find earliest start date to fetch all at once
        valid_dates = [d for d in fetch_params.values() if d]
        if not valid_dates:
            logging.warning("No valid start dates found")
            return {}

        earliest_start = min(valid_dates)

        # Check if earliest start date is in the future
        today = datetime.now().strftime("%Y-%m-%d")
        if earliest_start > today:
            logging.info(
                "All tickers are up to date (start date {} is in the future)".format(
                    earliest_start
                )
            )
            return {}

        # Batch fetch all tickers
        logging.info(
            "Fetching {} tickers from {}".format(len(all_tickers), earliest_start)
        )

        try:
            data = yf.download(
                all_tickers,
                start=earliest_start,
                end=datetime.today().strftime("%Y-%m-%d"),
                progress=False,
            )

            if data.empty:
                logging.warning("No data returned from yfinance")
                return {}

            # Detect tickers with all NaN Close values
            nan_tickers = self._detect_all_nan_tickers(data, all_tickers)

            if nan_tickers:
                logging.info(
                    "Detected {} tickers with all NaN values, fetching last day only: {}".format(
                        len(nan_tickers), nan_tickers
                    )
                )

                # Retry fetching with period="1d" for each NaN ticker
                for ticker in nan_tickers:
                    try:
                        logging.info("Fetching last day data for {}".format(ticker))
                        day_data = yf.download(ticker, period="1d", progress=False)

                        if not day_data.empty:
                            # Merge the 1-day data into the main dataframe
                            data = data.combine_first(day_data)
                            logging.info(
                                "Successfully fetched 1-day data for {}".format(ticker)
                            )
                        else:
                            logging.warning(
                                "No 1-day data available for {}".format(ticker)
                            )
                    except Exception as e:
                        logging.error(
                            "Error fetching 1-day data for {}: {}".format(ticker, e)
                        )

            # Extract Close prices and convert to dict
            close_data = data.filter(like="Close", axis=1).to_dict(orient="dict")
            result = {}

            for key, prices in close_data.items():
                # key is either 'Close' (single ticker) or ('Close', 'TICKER') (multiple tickers)
                if isinstance(key, tuple):
                    ticker = key[1]
                else:
                    ticker = all_tickers[0]

                # Convert Timestamp keys to YYYY-MM-DD strings, filter out NaN values
                result[ticker] = {
                    timestamp.strftime("%Y-%m-%d"): price
                    for timestamp, price in prices.items()
                    if not (isinstance(price, float) and price != price)  # Skip NaN
                }

            logging.info("Successfully fetched data for {} tickers".format(len(result)))
            return result

        except Exception as e:
            logging.error("Error fetching data from yfinance: {}".format(e))
            return {}

    def _reconcile_dates(self, worksheet, sheet_dates, all_ticker_data, date_to_row):
        """Reconcile dates from yfinance with sheet dates, insert rows as needed."""
        logging.info("Reconciling dates")

        # Collect all unique dates from fetched data
        fetched_dates = set()
        for ticker_data in all_ticker_data.values():
            fetched_dates.update(ticker_data.keys())

        # Merge and sort all dates
        all_dates = sorted(set(sheet_dates) | fetched_dates)

        # Find new dates that need row insertion
        new_dates = sorted(fetched_dates - set(sheet_dates))

        if not new_dates:
            logging.info("No new dates to insert")
            return all_dates, date_to_row

        logging.info("Inserting {} new date rows".format(len(new_dates)))

        # Ensure worksheet has enough rows
        required_rows = len(all_dates) + 4  # +4 for header rows (rows 1-3)
        if worksheet.row_count < required_rows:
            rows_to_add = required_rows - worksheet.row_count
            logging.info("Adding {} rows to worksheet".format(rows_to_add))
            worksheet.add_rows(rows_to_add)

        # Insert rows for new dates at correct positions
        for date in new_dates:
            # Find insertion position
            insert_pos = all_dates.index(date) + 4  # +4 for header rows

            # Update date_to_row mapping for dates after insertion
            for existing_date, row in list(date_to_row.items()):
                if row >= insert_pos:
                    date_to_row[existing_date] = row + 1

            # Add new date to mapping
            date_to_row[date] = insert_pos

        return all_dates, date_to_row

    def _prepare_batch_updates(
        self,
        worksheet,
        new_tickers,
        existing_tickers,
        all_ticker_data,
        sheet_tickers,
        date_to_row,
    ):
        """Prepare batch update data for the sheet."""
        logging.info("Preparing batch updates")

        updates = []

        # Ensure worksheet has enough columns for new tickers
        if new_tickers:
            last_col = max(sheet_tickers.values()) if sheet_tickers else 1
            required_cols = last_col + len(new_tickers)
            if worksheet.col_count < required_cols:
                cols_to_add = required_cols - worksheet.col_count
                logging.info("Adding {} columns to worksheet".format(cols_to_add))
                worksheet.add_cols(cols_to_add)
                for i in range(cols_to_add):
                    worksheet.copy_range(
                        gspread.utils.rowcol_to_a1(2, last_col)
                        + ":"
                        + gspread.utils.rowcol_to_a1(3, last_col),
                        gspread.utils.rowcol_to_a1(2, last_col + i + 1),
                    )

        # Add new ticker columns
        for ticker in new_tickers:
            last_col = max(sheet_tickers.values()) if sheet_tickers else 1
            new_col = last_col + 1
            sheet_tickers[ticker] = new_col

            # Add ticker header
            updates.append(
                {"range": gspread.utils.rowcol_to_a1(1, new_col), "values": [[ticker]]}
            )

        # Add date values and price data
        for ticker, ticker_data in all_ticker_data.items():
            if ticker not in sheet_tickers:
                logging.warning(
                    "Ticker {} not in sheet_tickers, skipping".format(ticker)
                )
                continue

            col = sheet_tickers[ticker]

            for date, price in ticker_data.items():
                if date not in date_to_row:
                    logging.warning(
                        "Date {} not in date_to_row mapping, skipping".format(date)
                    )
                    continue

                row = date_to_row[date]

                # Add date to column A if needed
                updates.append(
                    {"range": gspread.utils.rowcol_to_a1(row, 1), "values": [[date]]}
                )

                # Add price data
                updates.append(
                    {"range": gspread.utils.rowcol_to_a1(row, col), "values": [[price]]}
                )

        return updates
