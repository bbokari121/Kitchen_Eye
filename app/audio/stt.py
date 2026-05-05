# listens to mic and converts speech -> text (user input)
from app.utils.config import Config


class STT:
    def __init__(self, config: Config):
        self.config = config

    def listen(self) -> str:
        raise NotImplementedError
