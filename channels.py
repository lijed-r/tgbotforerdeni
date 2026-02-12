from telethon import TelegramClient
from dotenv import load_dotenv
import os

load_dotenv()

api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
phone = os.getenv("PHONE")

client = TelegramClient('session', api_id, api_hash)

async def main():
    dialogs = await client.get_dialogs()
    
    for dialog in dialogs:
        if dialog.is_channel:
            print(f"Название: {dialog.name}")
            print(f"ID: {dialog.id}")
            print("-" * 30)

with client:
    client.loop.run_until_complete(main())
