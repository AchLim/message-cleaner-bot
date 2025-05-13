from dotenv import load_dotenv
from fastapi import FastAPI, Form
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

import os
import time

load_dotenv()

app = FastAPI()
client = WebClient(token=os.environ.get('SLACK_BOT_TOKEN'))

@app.post("/slack/delete-all")
async def delete_all(
    user_id: str = Form(...),
    channel_id: str = Form(...)
):
    deleted = 0
    try:
        cursor = None
        while True:
            response = client.conversations_history(channel=channel_id, limit=100, cursor=cursor)
            messages = [m for m in response["messages"] if m.get("user") == user_id]
            for msg in messages:
                client.chat_delete(channel=channel_id, ts=msg["ts"])
                deleted += 1
                time.sleep(1)  # avoid rate limit

            cursor = response.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                break

        return {"text": f"Deleted {deleted} of your messages in this channel."}
    except SlackApiError as e:
        return {"text": f"Slack API error: {e.response['error']}"}
