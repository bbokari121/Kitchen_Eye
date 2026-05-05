# converts text -> speech (app talking back)
from app.utils.config import Config


class TTS:
    def __init__(self, config: Config):
        self.config = config
        self.language = config.get("audio.language", "en")

    def speak(self, text: str):
        raise NotImplementedError
