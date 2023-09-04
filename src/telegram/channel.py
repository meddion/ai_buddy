import json
import time
from typing import Optional, Dict
from dataclasses import dataclass, asdict
from dotenv import dotenv_values
from langchain import PromptTemplate
from telethon import TelegramClient
from telethon.tl.types import (
    Channel as TelegramChannel,
    Message as TelegramMessage,
    User,
    PeerUser,
    MessageReplyHeader,
    MessageMediaGeo,
    MessageMediaGeoLive,
    MessageMediaWebPage,
    WebPageEmpty,
)
import logging

log = logging.getLogger(__name__)


@dataclass
class Media:
    type: str


@dataclass
class MessageBase:
    user_id: str
    name: str
    text: str
    media: Optional[Media]


Reply = MessageBase


@dataclass
class Message(MessageBase):
    time: str
    reply_to: Optional[Reply]
    context_text: str = ""  # Gets extended by other fields.


CHAT_HISTORY_DEFAULT_PATH = "./misc/chat_history.json"


class Messages:
    data: list[Message]

    def __init__(self, data: list[Message]) -> None:
        self.data = data

    @staticmethod
    def from_dict(data_dict: list[dict]) -> "Messages":
        messages = [
            Message(
                user_id=msg["user_id"],
                name=msg["name"],
                text=msg["text"],
                time=msg["time"],
                media=msg["media"],
                context_text=msg.get("context_text", ""),
                reply_to=MessageBase(
                    user_id=msg["reply_to"]["user_id"],
                    name=msg["reply_to"]["name"],
                    text=msg["reply_to"]["text"],
                    media=msg["reply_to"]["media"],
                )
                if msg["reply_to"]
                else None,
            )
            for msg in data_dict
        ]

        return Messages(data=messages)

    @staticmethod
    def from_file(file_path: str = CHAT_HISTORY_DEFAULT_PATH) -> "Messages":
        with open(file_path, "r") as f:
            json_str = f.read()
            dict_data = json.loads(json_str)
            return Messages.from_dict(dict_data)

    def toJSON(self) -> str:
        return json.dumps(
            [asdict(msg) for msg in self.data],
            default=str,
            ensure_ascii=False,
            indent=4,
        )

    __repr__ = toJSON

    def __str__(self):
        return "\n".join(
            [f"Message from {msg.name} at {msg.time}: {msg.text}" for msg in self.data]
        )

    def save(self, file_path: str = CHAT_HISTORY_DEFAULT_PATH):
        with open(file_path, "w") as outfile:
            outfile.write(self.toJSON())

    def __iter__(self) -> "Messages":
        self.iter_idx = -1
        return self

    def __next__(self) -> Message:
        self.iter_idx += 1
        if self.iter_idx >= len(self.data):
            raise StopIteration

        return self.data[self.iter_idx]


class MessageFormatter:
    reply_tmpl = PromptTemplate(
        template="у відповідь на повідомлення яке написав {name}:{text}{attachment}",
        input_variables=["name", "text", "attachment"],
    )

    message_tmpl = PromptTemplate(
        template="{name} написав о {time}:{text}{attachment}{reply}",
        input_variables=["name", "time", "text", "attachment", "reply"],
    )

    @classmethod
    def format(cls, message: Message):
        reply = cls.reply(message)
        if reply != "":
            reply = " " + reply

        message.context_text = cls.message_tmpl.format(
            **{
                "name": message.name,
                "time": message.time,
                "text": cls.text(message.text),
                "attachment": cls.attachment(message),
                "reply": reply,
            }
        )

    @classmethod
    def text(cls, text: str) -> str:
        return " '" + text + "'" if text != "" else ""

    @classmethod
    def attachment(cls, msg: Messages | Reply) -> str:
        media_type = cls.media_type(msg.media)
        if media_type == "":
            return ""

        if msg.text != "":
            media_type = " та " + media_type

        return " " + media_type

    @classmethod
    def media_type(cls, media: Optional[Media]) -> str:
        if not media:
            return ""

        match media.type.split("/")[0]:
            case "image":
                content_type = "фотографію"
            case "video":
                content_type = "відео"
            case "audio":
                content_type = "аудіо"
            case "empty-webpage":
                content_type = "веб посилання"
            case "geolocation":
                content_type = "геопозицію"
            case "live-geolocation":
                content_type = "геопозицію в режимі онлайн"
            case _:
                log.warn(f"unknown media type: {media}")
                return ""

        return f"прикріпив {content_type}".upper()

    @classmethod
    def reply(cls, msg: Messages) -> str:
        reply = msg.reply_to
        if not reply:
            return ""

        return cls.reply_tmpl.format(
            **{
                "name": "сам" if reply.user_id == msg.user_id else reply.name,
                "text": cls.text(reply.text),
                "attachment": cls.attachment(reply),
            }
        )


class Channel:
    client: TelegramClient  # Needs to be a user client (not a Telegram bot).
    channel: TelegramChannel

    UNKNOWN_USER_NAME = "Незнайомець"
    user_cache: Dict[int, str] = {
        411323238: "Андрій",
        596110122: "Микола",
        564660774: "Володя",
        6470622385: "Йосип",  # Bot name.
    }

    def __init__(self, client: TelegramClient, channel: TelegramChannel) -> None:
        self.client = client
        self.channel = channel

    async def history(
        self,
        formatters=[MessageFormatter()],
        offset_date=None,
        search: Optional[str] = None,
    ) -> Messages:
        messages: list[Message] = []
        async for tmessage in self.client.iter_messages(
            self.channel, offset_date=offset_date, search=search, reverse=True
        ):
            if isinstance(tmessage, TelegramMessage):
                msg = Message(
                    user_id=tmessage.from_id.user_id,
                    name=await self.name_from_peer(tmessage.from_id),
                    text=tmessage.text,
                    time=tmessage.date,
                    media=self.media(tmessage),
                    reply_to=await self.reply(tmessage),
                )

                for formatter in formatters:
                    formatter.format(msg)

                messages.append(msg)
            else:
                log.warning(
                    f"Received a message of the unsupported type: {type(tmessage)}"
                )

        return Messages(data=messages)

    async def name_from_peer(self, peer: Optional[PeerUser]) -> str:
        if peer is None:
            return self.UNKNOWN_USER_NAME

        key = peer.user_id

        try:
            return self.user_cache[key]
        except KeyError:
            user: User = await self.client.get_entity(peer)

            if user.first_name is not None:
                new_user = user.first_name

            if user.last_name is not None:
                new_user += (" " if user != "" else "") + user.last_name

            self.user_cache[key] = new_user

        return self.user_cache[key]

    @classmethod
    async def name_from_user(self, user: Optional[User]) -> str:
        if user is None:
            return self.UNKNOWN_USER_NAME

        key = user.id

        try:
            return self.user_cache[key]
        except KeyError:
            if user.first_name is not None:
                new_user = user.first_name

            if user.last_name is not None:
                new_user += (" " if user != "" else "") + user.last_name

            self.user_cache[key] = new_user

        return self.user_cache[key]

    def media(self, tmsg: TelegramMessage) -> Optional[Media]:
        if not tmsg.media:
            return None

        def media_type(tmsg: TelegramMessage) -> str:
            if tmsg.file:
                return tmsg.file.mime_type

            if isinstance(tmsg.media, MessageMediaGeo):
                return "geolocation"

            if isinstance(tmsg.media, MessageMediaGeoLive):
                return "live-geolocation"

            if isinstance(tmsg.media, MessageMediaWebPage) and isinstance(
                tmsg.media.webpage, WebPageEmpty
            ):
                return "empty-webpage"

            log.warning("Encountered unsupported media file: ", tmsg.media)

            return ""

        return Media(type=media_type(tmsg))

    async def reply(self, tmsg: TelegramMessage) -> Optional[Reply]:
        if tmsg.reply_to and isinstance(tmsg.reply_to, MessageReplyHeader):
            treply_msg: TelegramMessage = await self.client.get_messages(
                self.channel, ids=tmsg.reply_to.reply_to_msg_id
            )
            if treply_msg:
                return Reply(
                    user_id=treply_msg.from_id.user_id,
                    name=await self.name_from_peer(treply_msg.from_id),
                    text=treply_msg.text,
                    media=self.media(treply_msg),
                )

        return None


async def save_history(
    client: TelegramClient,
    channel_id: int,
    history_path: str = CHAT_HISTORY_DEFAULT_PATH,
) -> None:
    channel = await client.get_entity(channel_id)
    chan = Channel(client, channel)
    messages = await chan.history()
    messages.save(history_path)


if __name__ == "__main__":
    t = time.time()

    env = dotenv_values()
    username = env["TELEGRAM_USER"]
    app_id = env["TELEGRAM_APP_ID"]
    api_hash = env["TELEGRAM_API_HASH"]
    channel_id = int(env["TELEGRAM_CHANNEL_ID"])  # 564660774 #- Me

    client = TelegramClient(
        username,
        app_id,
        api_hash,
    )

    with client:
        client.loop.run_until_complete(save_history(client, channel_id))

    elapsed_time = time.time() - t
    print("Elapsed time is %f seconds." % elapsed_time)
