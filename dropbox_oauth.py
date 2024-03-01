import json
from dropbox import DropboxOAuth2FlowNoRedirect

app_key = input("Enter the app key here: ").strip()
app_secret = input("Enter the app secret here: ").strip()

auth_flow = DropboxOAuth2FlowNoRedirect(
    app_key, app_secret, token_access_type="offline"
)

authorize_url = auth_flow.start()
print("1. Go to: " + authorize_url)
print('2. Click "Allow" (you might have to log in first).')
print("3. Copy the authorization code.")
auth_code = input("Enter the authorization code here: ").strip()

try:
    oauth_result = auth_flow.finish(auth_code)
except Exception as e:
    print("Error: %s" % (e,))
    exit(1)

oauth_dict = {
    "access_token": oauth_result.access_token,
    "account_id": oauth_result.account_id,
    "expires_at": oauth_result.expires_at.isoformat(),
    "refresh_token": oauth_result.refresh_token,
    "scope": oauth_result.scope,
    "user_id": oauth_result.user_id,
}
with open("token-dropbox.json", "w") as fp:
    json.dump(oauth_dict, fp)
