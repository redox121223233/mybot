import requests
import json

class TelegramAPI:
    def __init__(self, token):
        self.token = token
        self.api_url = f"https://api.telegram.org/bot{token}"

    def request(self, method, params=None, files=None):
        url = f"{self.api_url}/{method}"
        resp = requests.post(url, data=params, files=files)
        return resp.json()

    def send_message(self, chat_id, text, reply_markup=None):
        data = {"chat_id": chat_id, "text": text}
        if reply_markup:
            data["reply_markup"] = json.dumps(reply_markup)
        return self.request("sendMessage", params=data)

    def send_sticker(self, chat_id, sticker_file):
        return self.request("sendSticker", params={"chat_id": chat_id}, files={"sticker": sticker_file})

    def get_file(self, file_id):
        return requests.get(f"{self.api_url}/getFile", params={"file_id": file_id}).json()["result"]

    def download_file(self, file_path, dest):
        url = f"https://api.telegram.org/file/bot{self.token}/{file_path}"
        r = requests.get(url)
        with open(dest, "wb") as f:
            f.write(r.content)
