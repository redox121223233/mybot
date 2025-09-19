
from utils.logger import logger

class AIManager:
    def __init__(self, api=None):
        self.api = api

    def enhance_image(self, input_path, output_path):
        logger.info("AI enhance: %s -> %s", input_path, output_path)
        return output_path
