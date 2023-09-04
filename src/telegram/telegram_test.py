import unittest
import json
from channel import Messages


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

    def tearDown(self) -> None:
        import os

        os.remove(self.temp_file)
