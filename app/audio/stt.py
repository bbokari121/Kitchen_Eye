# listens to mic and converts speech -> text (user input)
import io
import wave
import threading
import speech_recognition as sr
import pyaudio
from app.utils.config import Config

_CHUNK = 1024
_FORMAT = pyaudio.paInt16
_CHANNELS = 1
_RATE = 16000


class STT:
    def __init__(self, config: Config):
        self.config = config
        self.recognizer = sr.Recognizer()
        self._pa = pyaudio.PyAudio()
        self._recording = False
        self._frames = []
        self._thread = None

    def start_listening(self):
        """Open mic and begin recording in a background thread."""
        self._frames = []
        self._recording = True
        self._thread = threading.Thread(target=self._record, daemon=True)
        self._thread.start()
        print("Listening...")

    def _record(self):
        input_device = self.config.get("audio.input_device_index", None)
        open_kwargs = dict(
            format=_FORMAT,
            channels=_CHANNELS,
            rate=_RATE,
            input=True,
            frames_per_buffer=_CHUNK,
        )
        if input_device is not None:
            open_kwargs["input_device_index"] = int(input_device)
        stream = self._pa.open(**open_kwargs)
        while self._recording:
            data = stream.read(_CHUNK, exception_on_overflow=False)
            self._frames.append(data)
        stream.stop_stream()
        stream.close()

    def stop_and_recognize(self) -> str:
        """
        Stop recording and convert captured audio to text.

        Returns:
            str: Recognized text, or empty string on failure.
        """
        self._recording = False
        if self._thread:
            self._thread.join()

        if not self._frames:
            return ""

        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(_CHANNELS)
            wf.setsampwidth(self._pa.get_sample_size(_FORMAT))
            wf.setframerate(_RATE)
            wf.writeframes(b"".join(self._frames))
        buf.seek(0)

        try:
            with sr.AudioFile(buf) as source:
                audio = self.recognizer.record(source)
            text = self.recognizer.recognize_google(audio)
            print(f"You said: {text}")
            return text
        except sr.UnknownValueError:
            print("Speech not recognized")
            return ""
        except sr.RequestError as e:
            print(f"API error: {e}")
            return ""
        except Exception as e:
            print(f"Error: {e}")
            return ""
