"""Translate detection labels into the target language."""
from app.utils.config import Config


class Translator:
    def __init__(self, config: Config):
        self.config = config
        self.target_lang = config.get("audio.language", "en")

    def translate(self, label: str) -> str:
        raise NotImplementedError
