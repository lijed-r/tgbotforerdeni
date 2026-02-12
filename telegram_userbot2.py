import asyncio
import random
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from collections import deque
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError, RPCError
from telethon.tl.types import Message


# ==================== НАСТРОЙКИ ====================
load_dotenv()

api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
phone = os.getenv("PHONE")

# Имя session-файла (будет создан автоматически при первом запуске)
session_name = 'userbot'


# Исходные каналы (username или ID)
# Примеры: 'durov', -1001234567890
source_channels = [
    -1003744265339,
    -1003724897076,
    -1003721548812,
    -1003815929642,
    -1002454236862]

# Целевой канал для пересылки (username или ID)
target_channel = -1003897518141

# Анти-спам настройки
MIN_DELAY = 1  # Минимальная задержка перед пересылкой (секунды)
MAX_DELAY = 5  # Максимальная задержка перед пересылкой (секунды)
MAX_FORWARDS_PER_HOUR = 60  # Максимальное количество пересылок в час

# ==================== КОД ПРОГРАММЫ ====================

client = TelegramClient(session_name, api_id, api_hash)

forwards_history = deque()


def log(message, prefix='ℹ️'):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f'[{timestamp}] {prefix} {message}')


def can_forward():
    current_time = datetime.now()
    one_hour_ago = current_time - timedelta(hours=1)
    
    while forwards_history and forwards_history[0] < one_hour_ago:
        forwards_history.popleft()
    
    return len(forwards_history) < MAX_FORWARDS_PER_HOUR


def register_forward():
    forwards_history.append(datetime.now())


def get_forwards_count():
    current_time = datetime.now()
    one_hour_ago = current_time - timedelta(hours=1)
    
    while forwards_history and forwards_history[0] < one_hour_ago:
        forwards_history.popleft()
    
    return len(forwards_history)


def get_time_until_next_slot():
    if not forwards_history:
        return 0
    
    one_hour_later = forwards_history[0] + timedelta(hours=1)
    current_time = datetime.now()
    
    if one_hour_later > current_time:
        return (one_hour_later - current_time).total_seconds()
    return 0


async def send_message_copy(message, source_signature):
    downloaded_files = []

    try:
        # ================= АЛЬБОМ =================
        if message.grouped_id:
            log('Обнаружен альбом, собираю все файлы...', '🖼️')
            await asyncio.sleep(2)

            album_messages = []
            async for msg in client.iter_messages(
                message.chat_id,
                min_id=message.id - 10,
                max_id=message.id + 10
            ):
                if msg.grouped_id == message.grouped_id:
                    album_messages.append(msg)

            album_messages.sort(key=lambda m: m.id)

            caption_text = ""
            for msg in album_messages:
                if msg.text:
                    caption_text = msg.text
                    break

            caption_text = f"{caption_text}\n\n{source_signature}".strip()

            for msg in album_messages:
                if msg.media:
                    file_path = await msg.download_media()
                    if file_path:
                        downloaded_files.append(file_path)

            if downloaded_files:
                await client.send_file(
                    target_channel,
                    downloaded_files,
                    caption=caption_text
                )
                log(f'Альбом из {len(downloaded_files)} файлов отправлен', '📤')
                return True
            return False

        # ================= ОДИНОЧНОЕ МЕДИА =================
        elif message.media:
            log('Скачиваю медиа...', '📥')
            file_path = await message.download_media()

            if not file_path:
                log('Не удалось скачать медиа', '⚠️')
                return False

            downloaded_files.append(file_path)

            caption_text = f"{message.text or ''}\n\n{source_signature}".strip()

            await client.send_file(
                target_channel,
                file_path,
                caption=caption_text,
                force_document=False
            )

            log('Одиночное медиа отправлено', '📤')
            return True

        # ================= ТОЛЬКО ТЕКСТ =================
        elif message.text:
            text = f"{message.text}\n\n{source_signature}"
            await client.send_message(target_channel, text)
            log('Текст скопирован', '📝')
            return True

        else:
            log('Сообщение не содержит текста или медиа', '⚠️')
            return False

    except FloodWaitError as e:
        log(f'FloodWait: ждём {e.seconds} сек', '⏳')
        await asyncio.sleep(e.seconds)
        return await send_message_copy(message, source_signature)

    except Exception as e:
        log(f'Ошибка копирования: {e}', '❌')
        return False

    finally:
        import os
        for f in downloaded_files:
            try:
                if os.path.exists(f):
                    os.remove(f)
                    log(f'Файл удалён: {f}', '🗑️')
            except Exception as cleanup_error:
                log(f'Ошибка удаления файла: {cleanup_error}', '⚠️')



@client.on(events.NewMessage(chats=source_channels))
async def handler(event):
    try:
        if event.message.grouped_id:
            async for msg in client.iter_messages(event.chat_id, limit=1):
                if msg.grouped_id == event.message.grouped_id and msg.id != event.message.id:
                    return
                
        channel = await event.get_chat()
        channel_name = getattr(channel, 'username', None) or getattr(channel, 'title', 'Unknown')
        
        channel = await event.get_chat()
        channel_title = getattr(channel, 'title', None)
        channel_username = getattr(channel, 'username', None)

        if channel_username:
            source_signature = f"🔗 Источник: @{channel_username}"
        elif channel_title:
            source_signature = f"🔗 Источник: {channel_title}"
        else:
            source_signature = f"🔗 Источник: {event.chat_id}"
        log(f'Новый пост из канала "{channel_name}"', '📨')
        
        if not can_forward():
            wait_time = int(get_time_until_next_slot())
            log(f'Превышен лимит ({get_forwards_count()}/{MAX_FORWARDS_PER_HOUR}). Ожидание {wait_time} секунд...', '⚠️')
            await asyncio.sleep(wait_time)
        
        delay = random.randint(MIN_DELAY, MAX_DELAY)
        log(f'Ожидание {delay} секунд перед пересылкой...', '⏳')
        await asyncio.sleep(delay)
        
        try:
            await client.forward_messages(target_channel, event.message)
            register_forward()
            log(f'Переслано в "{target_channel}"', '✅')
            log(f'Пересылок в этом часе: {get_forwards_count()}/{MAX_FORWARDS_PER_HOUR}', '📊')
        except Exception as forward_error:
            error_str = str(forward_error).lower()
            if any(keyword in error_str for keyword in ['chat_forward_restricted', 'noforwards', 'protected chat', 'forward']):
                log('Пересылка ограничена, копирую содержимое...', '🔄')
                if await send_message_copy(event.message, source_signature):
                    register_forward()
                    log(f'Скопировано в "{target_channel}"', '✅')
                    log(f'Пересылок в этом часе: {get_forwards_count()}/{MAX_FORWARDS_PER_HOUR}', '📊')
            else:
                raise
        
    except FloodWaitError as e:
        wait_seconds = e.seconds
        log(f'FloodWait: ожидание {wait_seconds} секунд...', '⚠️')
        await asyncio.sleep(wait_seconds)
        await client.forward_messages(target_channel, event.message)
        register_forward()
        log(f'Переслано после FloodWait', '✅')
        
    except RPCError as e:
        log(f'RPC ошибка: {e}', '❌')
        
    except Exception as e:
        log(f'Неожиданная ошибка: {e}', '❌')


async def main():
    await client.start()
    
    me = await client.get_me()
    log(f'Вход выполнен как: {me.first_name} (@{me.username})', '🔐')
    
    log('Userbot запущен и слушает каналы...', '🤖')
    log(f'Отслеживаемые каналы: {source_channels}', '📋')
    log(f'Целевой канал: {target_channel}', '🎯')
    log(f'Анти-спам: задержка {MIN_DELAY}-{MAX_DELAY}с, лимит {MAX_FORWARDS_PER_HOUR} пересылок/час', '🛡')
    
    await client.run_until_disconnected()


if __name__ == '__main__':
    try:
        client.loop.run_until_complete(main())
    except KeyboardInterrupt:
        log('Остановка userbot...', '🛑')
    except Exception as e:
        log(f'Критическая ошибка: {e}', '❌')
