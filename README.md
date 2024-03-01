# YNAB4-to-gsheet

Small Python program to perform a one-way synchronization between a YNAB4 budget and a google sheet.

Automatically finds the latest version of the budget regardless which device it was last opened with and uses that for the synchronization.

I won't be documenting the format of the spreadsheet that is the target as there's no sensible format to use for documentation other than stripping out all data and publishing that as a template.

## Setup

In order for this to work one has to do some additional setup:

### Dropbox

Register a Dropbox API app in the [App Console](https://www.dropbox.com/developers/apps). Needs the `files.content.read` permission.

Get an OAuth2 access token from Dropbox using the `dropbox_oauth.py` script. The resulting token will be saved as `token-dropbox.json`, keep it safe.

### Google

Follow the steps in the [official documentation](https://docs.gspread.org/en/latest/oauth2.html#for-end-users-using-oauth-client-id) to enable OAuth Client authentication and save the credentials and token.

## Configuration

The following environment variables are used for configuration:

* **DROPBOX_APP_KEY** - Dropbox APP key from Dropbox App Console above
* **DROPBOX_APP_SECRET** - Dropbox APP secret from Dropbox App Console above
* **DROPBOX_OAUTH_TOKEN_FILENAME** - Dropbox OAuth2 token file, generate with `python dropbox_oauth.py` after installing requirements
* **GSPREAD_AUTHORIZED_USER_FILENAME** - Google OAuth authorized user json file path, defaults to `/run/secrets/token.json`
* **GSPREAD_CREDENTIALS_FILENAME** - Google OAuth credentials json file path, defaults to `/run/secrets/credentials.json`
* **GSPREAD_SHEET_NAME** - Name of the Google Sheet to store data in
* **BUDGET** - YNAB4 budget file inside the YNAB folder (e.g. `Budget~06A6A692.ynab4`)
* **BUDGET_EXTRA_TXN__<CUR>** - Additional budgets to be used for transactions in different currencies (e.g. `BUDGET_EXTRA_TXN__USD='USD Budget~22F69526.ynab4'`)
* **LOG_LEVEL** - Set logging level, defaults to `INFO`

## References

* [Dropbox for Python Developers](https://www.dropbox.com/developers/documentation/python#tutorial)
* [gspread Authentication](https://docs.gspread.org/en/latest/oauth2.html)
* [Reversing the YNAB file format - Part 1: JSON Structure](https://jack.codes/projects/2016/09/13/reversing-the-ynab-file-format-part-1/)
