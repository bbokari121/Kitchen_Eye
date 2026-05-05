# handles logic: understands user request and decides what to say
from app.utils.config import Config


class Assistant:
    def __init__(self, config: Config):
        self.config = config

    def respond(self, user_text: str) -> str:
        raise NotImplementedError
