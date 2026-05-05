# converts text -> speech (app talking back)
import pyttsx3
from app.utils.config import Config


class TTS:
    def __init__(self, config: Config):
        self.config = config
        self.language = config.get("audio.language", "en")
        self.engine = pyttsx3.init()
        # Slower default rate for better clarity in spoken guidance.
        self.engine.setProperty("rate", config.get("audio.tts_rate", 135))
        self.engine.setProperty("volume", config.get("audio.tts_volume", 1.0))

    def speak(self, text: str):
        """
        Speak the given text using text-to-speech.
        
        Args:
            text (str): The text to speak.
        """
        if not text:
            return
        
        self.engine.say(text)
        self.engine.runAndWait()
