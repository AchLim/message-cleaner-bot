from fastapi import FastAPI, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv
import requests
import time
import os

load_dotenv()

app = FastAPI()

SLACK_CLIENT_ID = os.getenv("SLACK_CLIENT_ID")
SLACK_CLIENT_SECRET = os.getenv("SLACK_CLIENT_SECRET")
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_OAUTH_REDIRECT_URI = os.getenv("SLACK_OAUTH_REDIRECT_URI")

# Slash Command Route
@app.post("/slack/delete-all")
async def delete_all_messages(
    text: str = Form(None),
    channel_id: str = Form(...),
    user_id: str = Form(...),
):
    user_token = text.strip()  # Get the user token from the text input
    
    if not user_token:
        # Send authorization URL if token is not provided
        auth_url = (
            f"https://slack.com/oauth/v2/authorize"
            f"?client_id={SLACK_CLIENT_ID}"
            f"&scope=chat:write,channels:history,groups:history,im:history,mpim:history"
            f"&user_scope=chat:write,channels:history,groups:history,im:history,mpim:history"
            f"&redirect_uri={SLACK_OAUTH_REDIRECT_URI}"
        )
        return JSONResponse(
            status_code=200,
            content={
                "text": f"To authorize this app to delete your messages, click here:\n<{auth_url}|Authorize App>"
            },
        )

    if not user_token.startswith("xoxp-"):
        return JSONResponse(content={
            "response_type": "ephemeral",
            "text": "❌ Invalid or missing user token.\nPlease call the slash command like:\n`/delete-my-messages xoxp-...`"
        })

    # Proceed to delete messages
    user_client = WebClient(token=user_token)
    deleted = 0

    try:
        cursor = None
        while True:
            response = user_client.conversations_history(channel=channel_id, limit=100, cursor=cursor)
            messages = [m for m in response["messages"] if m.get("user") == user_id]
            for msg in messages:
                try:
                    user_client.chat_delete(channel=channel_id, ts=msg["ts"])
                    deleted += 1
                    time.sleep(1)
                except SlackApiError as e:
                    continue  # skip if not allowed to delete

            cursor = response.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                break

        return {"text": f"Deleted {deleted} of your messages from <#{channel_id}>."}
    except SlackApiError as e:
        return {"text": f"Slack API error: {e.response['error']}"}


# OAuth Callback Handler
@app.get("/slack/oauth")
async def oauth_callback(request: Request):
    code = request.query_params.get("code")
    if not code:
        return {"error": "Authorization code not provided"}

    # Exchange the code for a token
    response = requests.post(
        "https://slack.com/api/oauth.v2.access",
        data={
            "client_id": SLACK_CLIENT_ID,
            "client_secret": SLACK_CLIENT_SECRET,
            "code": code,
            "redirect_uri": SLACK_OAUTH_REDIRECT_URI,
        },
    )
    data = response.json()
    if not data.get("ok"):
        return {"error": data.get("error", "OAuth failed")}

    user_token = data["authed_user"]["access_token"]
    return {
        "message": "Authorization successful!",
        "instruction": "Copy this token and paste it in the slash command like so:",
        "example": "/delete-all user_token=PASTE_HERE",
        "user_token": user_token,
    }
