from dotenv import dotenv_values
import json

import time


# import telebot
# bot = telebot.TeleBot(env["TELEGRAM_API_KEY"])
from telethon import TelegramClient
from telethon.tl.types import Channel, Message, User, PeerUser, MessageReplyHeader

import logging

logging.basicConfig(
    format="[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s", level=logging.WARNING
)


t = time.time()

env = dotenv_values()
username = env["TELEGRAM_USER"]
phone = env["TELEGRAM_PHONE"]
app_id = env["TELEGRAM_APP_ID"]
api_hash = env["TELEGRAM_API_HASH"]

channel_id = int(env["TELEGRAM_CHANNEL_ID"])  # 564660774 #- Me

client = TelegramClient(username, app_id, api_hash)


uknown_users = {}
known_users = {411323238: "Андрій", 596110122: "Микола", 564660774: "Володя"}


async def get_user_name(from_user: PeerUser | None) -> str:
    if from_user is None:
        return "Незнайомець"

    key = from_user.user_id

    if (name := known_users.get(key, "")) != "":
        return name

    user = uknown_users.get(key, "")
    if user == "":
        entity_user: User = await client.get_entity(from_user)

        if entity_user.first_name is not None:
            user = entity_user.first_name

        if entity_user.last_name is not None:
            user += " " if user != "" else "" + entity_user.last_name

        uknown_users[key] = user

    return user


async def get_message_history(channel: Channel) -> tuple[list[str], int]:
    all_messages = []

    async for message in client.iter_messages(channel, reverse=True):
        # print("Received a type: ", repr(message))
        if isinstance(message, Message):
            user_name = await get_user_name(message.from_id)

            msg = {
                "user_id": message.from_id.user_id,
                "full_name": user_name,
                "text": message.text,
                "time": message.date,
                "reply_to": None,
            }

            # print("Message to reply: ", repr(message.reply_to))
            if message.reply_to and isinstance(message.reply_to, MessageReplyHeader):
                reply_msg: Message = await client.get_messages(
                    channel, ids=message.reply_to.reply_to_msg_id
                )
                if reply_msg:
                    msg["reply_to"] = {
                        "user_id": reply_msg.from_id.user_id,
                        "name": await get_user_name(reply_msg.from_id),
                        "text": reply_msg.text,
                    }

            # # "file_mime_type": message.file.mime_type if message.media else None,
            # "reply_to": message.reply_to.reply_to_peer_id.user_id
            # if message.reply_to is not None
            # else None,

            all_messages.append(msg)

    return all_messages


async def main():
    my_channel: Channel = await client.get_entity(channel_id)
    # print("Channel info:", my_channel.stringify())

    channel_messages = await get_message_history(my_channel)

    with open("chat_history.json", "w") as outfile:
        json.dump(channel_messages, outfile, default=str, ensure_ascii=False, indent=4)

    # await client.run_until_disconnected()


with client:
    client.loop.run_until_complete(main())


print("Elapsed time is %f seconds." % time.time() - t)

# client.start()

# print("Client Created")
# # Ensure you're authorized
# if not client.is_user_authorized():
#     client.send_code_request(phone)
#     try:
#         client.sign_in(phone, input('Enter the code: '))
#     except SessionPasswordNeededError:
#         client.sign_in(password=input('Password: '))
