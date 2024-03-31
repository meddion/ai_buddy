from dotenv import dotenv_values
from telethon import TelegramClient
from telethon.types import User
from telethon import events
from telegram.channel import Channel
from ai import BuddyAI, Response
import logging

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


if __name__ == "__main__":
    env = dotenv_values()
    session_name = "telegram_bot"
    app_id = env["TELEGRAM_APP_ID"]
    api_hash = env["TELEGRAM_API_HASH"]
    bot_token = env["TELEGRAM_API_KEY"]
    channel_id = int(env["TELEGRAM_CHANNEL_ID"])

    bot = TelegramClient(session_name, app_id, api_hash).start(bot_token=bot_token)

    buddy_ai: BuddyAI = BuddyAI(with_query_chain=False, with_context=False)

    @bot.on(events.NewMessage(incoming=True, chats=[channel_id]))
    async def message_handler(event: events.NewMessage.Event):
        sender: User = await event.get_sender()
        sender_name = await Channel.name_from_user(sender)

        human_message = f"{sender_name}: {event.raw_text}"
        log.debug(f"Human message to AI: '{human_message}'")

        resp: Response = buddy_ai(human_message)

        # chat = await event.get_chat()
        # await bot.send_message(entity=chat.id, message=resp.answer)
        await event.respond(resp.answer)

    bot.run_until_disconnected()
