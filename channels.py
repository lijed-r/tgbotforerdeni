from telethon import TelegramClient

api_id = 31602734
api_hash = '626c1101baf346da1676ff957a7fceec'

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
