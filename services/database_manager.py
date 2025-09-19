
import os, json
from utils.logger import logger

class DatabaseManager:
    def __init__(self, base_dir):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def _path(self, filename):
        return os.path.join(self.base_dir, filename)

    def load(self, filename):
        path = self._path(filename)
        if not os.path.exists(path):
            logger.info("File not found, creating empty: %s", filename)
            self.save(filename, {})
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.exception("load error %s: %s", filename, e)
            self.save(filename, {})
            return {}

    def save(self, filename, data):
        path = self._path(filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info("Saved %s", filename)
