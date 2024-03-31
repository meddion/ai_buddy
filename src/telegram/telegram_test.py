import unittest
import json
import logging
from telegram.channel import Messages, Channel
import telethon
from dotenv import dotenv_values


class TestTelegramChannel(unittest.TestCase):
    temp_file = "./misc/temp_history.json"

    def test_json_serialization(self):
        json_data = """
        [{
            "user_id": 596110122,
            "name": "Микола",
            "text": "а ми будемо хайпувати на всіх темах",
            "time": "2023-05-08 11:32:09+00:00",
            "media": null,
            "reply_to": null
        },
        {
            "user_id": 564660774,
            "name": "Володя",
            "text": "ну в одного ще поки залисини; але правду мовиш",
            "time": "2023-05-08 11:34:10+00:00",
            "media": null,
            "reply_to": {
                "user_id": 596110122,
                "name": "Микола",
                "text": "це якихось два лисих тіпа, які вирішили хайпанути на темі",
                "media": null
            }
        }]"""

        dict_data = json.loads(json_data)
        msgs_from_dict = Messages.from_dict(dict_data)
        msgs = [msg for msg in msgs_from_dict]
        self.assertEqual(len(msgs), 2)

        msgs_from_dict.save(self.temp_file)

        msgs_from_file = Messages.from_file(self.temp_file)

        self.assertEqual(msgs_from_file.toJSON(), msgs_from_dict.toJSON())

    def test_integration_history_fetch(self):
        """An integration test that calls Telegram."""
        env = dotenv_values()
        username = env["TELEGRAM_USER"]
        app_id = env["TELEGRAM_APP_ID"]
        api_hash = env["TELEGRAM_API_HASH"]
        channel_id = int(env["TELEGRAM_CHANNEL_ID"])  # 564660774 #- Me

        client = telethon.TelegramClient(
            username,
            app_id,
            api_hash,
        )

        async def test_search():
            tchannel = await client.get_entity(channel_id)
            chan = Channel(client, tchannel)
            search_query = "пиво"
            history = await chan.history(search=search_query)
            msgs = [msg for msg in history]
            self.assertNotEqual(len(msgs), 0)

        with client:
            client.loop.run_until_complete(test_search())

        async def test_picking():
            tchannel = await client.get_entity(channel_id)
            chan = Channel(client, tchannel)

            history = await chan.history()

            msgs = [msg for msg in history]
            self.assertNotEqual(len(msgs), 0)

        with client:
            client.loop.run_until_complete(test_picking())

    def tearDown(self) -> None:
        import os

        try:
            os.remove(self.temp_file)
        except Exception as err:
            logging.warn(f"On deleting {self.temp_file}: {err}")
