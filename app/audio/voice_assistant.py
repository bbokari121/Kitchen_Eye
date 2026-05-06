import queue
import random
import re
import threading
import time
from typing import Callable

import speech_recognition as sr

from app.audio.tts import TTS
from app.utils.config import Config


class VoiceAssistantController:
    _PENDING_PREFIX_TTL_SECONDS = 8.0
    _REPROMPT_COOLDOWN_SECONDS = 2.5
    _REPEAT_OBJECT_PROMPT = "Could you repeat that"

    _QUERY_PREFIXES = ("where", "where is", "where is the", "is the")
    _PHRASE_ALIASES = {
        "cutting bored": "cutting board",
        "cutting bord": "cutting board",
        "where is the cut": "where is the cutting board",
        "where is cut": "where is cutting board",
        "where is board": "where is cutting board",
        "where is bored": "where is cutting board",
        "where is the board": "where is the cutting board",
        "where is the bored": "where is the cutting board",
        "chopping board": "cutting board",
        "frying pan": "frying pan",
        "fry pan": "frying pan",
        "frying pen": "frying pan",
    }
    _OBJECT_ALIASES = {
        "bowl": "bowl",
        "bowls": "bowl",
        "bol": "bowl",
        "boll": "bowl",
        "ball": "bowl",
        "knife": "knife",
        "knives": "knife",
        "knive": "knife",
        "naif": "knife",
        "nite": "knife",
        "cut": "cutting",
        "cutting": "cutting",
        "board": "board",
        "boards": "board",
        "bored": "board",
        "bord": "board",
        "frying": "frying",
        "fry": "frying",
        "friing": "frying",
        "pan": "pan",
        "pans": "pan",
        "pen": "pan",
        "pens": "pan",
        "pun": "pan",
        "pot": "pot",
        "pots": "pot",
        "part": "pot",
        "parts": "pot",
        "port": "pot",
        "ports": "pot",
        "pod": "pot",
        "pods": "pot",
        "spot": "pot",
        "spots": "pot",
        "stove": "stove",
        "stoves": "stove",
        "stov": "stove",
        "store": "stove",
        "stow": "stove",
        "spoon": "spoon",
        "spoons": "spoon",
        "westburn": "spoon",
        "spun": "spoon",
        "soon": "spoon",
        "spatula": "spatula",
        "spatulas": "spatula",
        "spatchula": "spatula",
        "spatuler": "spatula",
        "spatulaa": "spatula",
        "play": "plate",
        "plays": "plate",
        "plait": "plate",
        "pleat": "plate",
        "place": "plate",
        "places": "plate",
        "plate": "plate",
        "plates": "plate",
        "plade": "plate",
        "planet": "plate",
        "play it": "plate",
    }

    ALLOWED_OBJECTS = (
        "bowl",
        "knife",
        "cutting board",
        "frying pan",
        "pan",
        "pot",
        "stove",
        "spoon",
        "spatula",
        "plate",
    )

    def __init__(self, config: Config, on_command_detected: Callable[[str], None]):
        self.config = config
        self.language = config.get("audio.language", "en")
        self._on_command_detected = on_command_detected
        self._recognizer = sr.Recognizer()
        self._recognizer.pause_threshold = 0.8
        self._recognizer.non_speaking_duration = 0.45
        self._recognizer.phrase_threshold = 0.2
        self._tts = TTS(config)
        self._running = False
        self._listener_thread = None
        self._speak_queue = queue.Queue()
        self._is_speaking = threading.Event()
        self._speak_thread = threading.Thread(target=self._speak_worker, daemon=True)
        self._speak_thread.start()
        self._allowed_lookup = self._build_allowed_lookup()
        self._normalized_objects = tuple(self._normalize_text(obj) for obj in self.ALLOWED_OBJECTS)
        self._pending_prefix = ""
        self._pending_prefix_time = 0.0
        self._last_reprompt_time = 0.0

    def start(self):
        if self._running:
            return
        self._running = True
        self._listener_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._listener_thread.start()

    def stop(self):
        self._running = False
        if self._listener_thread is not None:
            self._listener_thread.join(timeout=2)

    def replay(self, text: str):
        if text:
            self._speak_queue.put(text)

    def _speak_worker(self):
        while True:
            text = self._speak_queue.get()
            try:
                # Block microphone processing while assistant audio is playing.
                self._is_speaking.set()
                self._tts.speak(text)
            except Exception as exc:
                print(f"TTS error: {exc}")
            finally:
                self._is_speaking.clear()

    def _listen_loop(self):
        while self._running:
            try:
                with sr.Microphone(sample_rate=16000) as source:
                    self._recognizer.adjust_for_ambient_noise(source, duration=0.4)
                    while self._running:
                        if self._is_speaking.is_set():
                            time.sleep(0.05)
                            continue

                        try:
                            audio = self._recognizer.listen(
                                source,
                                timeout=0.4,
                                phrase_time_limit=4.0,
                            )
                        except sr.WaitTimeoutError:
                            continue

                        recognized = self._recognize_text(audio)
                        if not recognized:
                            continue

                        print(f"Heard: {recognized}")
                        if not self._has_immediate_match(recognized):
                            print("No match found")

                        recognized = self._apply_pending_prefix(recognized)
                        recognized = self._complete_possible_prefix(recognized, source)

                        matched_object = self._match_allowed_object(recognized)
                        if not matched_object:
                            continue

                        reply = self._build_relative_reply(matched_object)
                        print(f"Transcript: {reply}")
                        self._on_command_detected(reply)
                        self._speak_queue.put(reply)
            except Exception as exc:
                print(f"STT loop error: {exc}")

    def _recognize_text(self, audio) -> str:
        try:
            return self._recognizer.recognize_google(audio, language=self.language)
        except sr.UnknownValueError:
            return ""
        except sr.RequestError as exc:
            print(f"STT service error: {exc}")
            return ""

    def _match_allowed_object(self, text: str):
        normalized = self._normalize_text(text)
        normalized = self._apply_object_aliases(normalized)

        # If prefix continuation state is active and only object word was captured,
        # still resolve it to avoid losing "where is" + "object" split speech.
        if self._pending_prefix:
            standalone_object = self._match_standalone_object(normalized)
            if standalone_object:
                self._clear_pending_prefix()
                return standalone_object

        # Also accept standalone object words directly.
        standalone_object = self._match_standalone_object(normalized)
        if standalone_object:
            self._clear_pending_prefix()
            return standalone_object

        exact = self._allowed_lookup.get(normalized)
        if exact:
            self._clear_pending_prefix()
            return exact

        contained = self._match_object_in_sentence(normalized)
        if contained:
            self._clear_pending_prefix()
            return contained

        _, object_fragment = self._extract_query_parts(normalized)
        if not object_fragment:
            return None

        candidates = [
            obj for obj in self._normalized_objects if obj.startswith(object_fragment)
        ]
        if len(candidates) == 1:
            self._clear_pending_prefix()
            return candidates[0]
        return None

    def _match_object_in_sentence(self, normalized_text: str):
        objects_by_length = sorted(self._normalized_objects, key=len, reverse=True)
        for obj in objects_by_length:
            patterns = (
                f"where is the {obj}",
                f"where is {obj}",
                f"is the {obj}",
                f"where the {obj}",
                f"where {obj}",
            )
            if any(pattern in normalized_text for pattern in patterns):
                return obj

        if "where" in normalized_text:
            for obj in objects_by_length:
                if re.search(rf"\b{re.escape(obj)}\b", normalized_text):
                    return obj

        return None

    def _match_standalone_object(self, normalized_text: str):
        normalized_text = normalized_text.strip()

        if normalized_text in self._normalized_objects:
            return normalized_text

        if normalized_text.startswith("the "):
            normalized_text = normalized_text[4:].strip()
            if normalized_text in self._normalized_objects:
                return normalized_text

        if normalized_text in ("cut", "cutting", "cutting board", "board", "bored"):
            return "cutting board"

        candidates = [
            obj for obj in self._normalized_objects if obj.startswith(normalized_text)
        ]
        if len(candidates) == 1:
            return candidates[0]

        for obj in sorted(self._normalized_objects, key=len, reverse=True):
            if re.search(rf"\b{re.escape(obj)}\b", normalized_text):
                return obj
        return None

    def _has_immediate_match(self, text: str) -> bool:
        normalized = self._apply_object_aliases(self._normalize_text(text))

        if self._match_standalone_object(normalized):
            return True

        if normalized in self._allowed_lookup:
            return True

        if self._match_object_in_sentence(normalized):
            return True

        _, object_fragment = self._extract_query_parts(normalized)
        if object_fragment:
            candidates = [
                obj for obj in self._normalized_objects if obj.startswith(object_fragment)
            ]
            if len(candidates) == 1:
                return True

        return False

    def _build_allowed_lookup(self):
        lookup = {}
        for obj in self.ALLOWED_OBJECTS:
            normalized_obj = self._normalize_text(obj)
            lookup[f"where {normalized_obj}"] = normalized_obj
            lookup[f"where the {normalized_obj}"] = normalized_obj
            lookup[f"where is {normalized_obj}"] = normalized_obj
            lookup[f"where is the {normalized_obj}"] = normalized_obj
            lookup[f"is the {normalized_obj}"] = normalized_obj
        return lookup

    def _apply_pending_prefix(self, text: str) -> str:
        if not self._pending_prefix:
            return text

        if (time.monotonic() - self._pending_prefix_time) > self._PENDING_PREFIX_TTL_SECONDS:
            self._clear_pending_prefix()
            return text

        normalized = self._normalize_text(text)
        if normalized in self._QUERY_PREFIXES:
            self._set_pending_prefix(normalized)
        return text

    def _complete_possible_prefix(self, text: str, source) -> str:
        combined = text
        normalized = self._normalize_text(combined)
        if normalized in self._QUERY_PREFIXES:
            self._set_pending_prefix(normalized)
            print("Listening Again")
            self._emit_repeat_object_prompt()
            return combined

        for _ in range(2):
            normalized = self._normalize_text(combined)
            if not self._looks_incomplete_query(normalized):
                return combined

            if self._is_speaking.is_set():
                break

            try:
                continuation_audio = self._recognizer.listen(
                    source,
                    timeout=1.2,
                    phrase_time_limit=2.2,
                )
            except sr.WaitTimeoutError:
                break

            continuation = self._recognize_text(continuation_audio)
            if not continuation:
                break

            combined = f"{combined} {continuation}".strip()

        normalized = self._normalize_text(combined)
        if self._looks_incomplete_query(normalized):
            prefix, _ = self._extract_query_parts(normalized)
            self._set_pending_prefix(prefix or normalized)
            print("Listening Again")
            if normalized in self._QUERY_PREFIXES:
                self._emit_repeat_object_prompt()

        return combined

    def _emit_repeat_object_prompt(self):
        now = time.monotonic()
        if (now - self._last_reprompt_time) < self._REPROMPT_COOLDOWN_SECONDS:
            return

        self._last_reprompt_time = now
        self._on_command_detected(self._REPEAT_OBJECT_PROMPT)
        self._speak_queue.put(self._REPEAT_OBJECT_PROMPT)

    def _set_pending_prefix(self, prefix: str):
        if not prefix:
            return
        self._pending_prefix = prefix
        self._pending_prefix_time = time.monotonic()

    def _clear_pending_prefix(self):
        self._pending_prefix = ""
        self._pending_prefix_time = 0.0

    def _looks_incomplete_query(self, normalized_text: str) -> bool:
        normalized_text = self._apply_object_aliases(normalized_text)

        if normalized_text in self._QUERY_PREFIXES:
            return True

        prefix, object_fragment = self._extract_query_parts(normalized_text)
        if not prefix:
            return False
        if not object_fragment:
            return True
        if normalized_text in self._allowed_lookup:
            return False
        if len(object_fragment) < 3:
            return True

        candidates = [
            obj for obj in self._normalized_objects if obj.startswith(object_fragment)
        ]
        if len(candidates) == 1:
            return False
        return len(candidates) > 1

    def _extract_query_parts(self, normalized_text: str):
        for prefix in sorted(self._QUERY_PREFIXES, key=len, reverse=True):
            prefix_with_space = f"{prefix} "
            if normalized_text.startswith(prefix_with_space):
                return prefix, normalized_text[len(prefix_with_space):].strip()
            if normalized_text == prefix:
                return prefix, ""
        return "", ""

    def _apply_object_aliases(self, normalized_text: str) -> str:
        if not normalized_text:
            return normalized_text

        for phrase, replacement in self._PHRASE_ALIASES.items():
            normalized_text = normalized_text.replace(phrase, replacement)

        words = normalized_text.split()
        replaced = [self._OBJECT_ALIASES.get(word, word) for word in words]
        return " ".join(replaced)

    @staticmethod
    def _build_relative_reply(obj_name: str) -> str:
        direction = random.choice(("left", "right", "ahead"))
        if direction == "ahead":
            return f"{obj_name} is directly ahead"

        modifier = "slightly " if random.choice((True, False)) else ""
        return f"{obj_name} is {modifier}to the {direction}"

    @staticmethod
    def _normalize_text(text: str) -> str:
        lowered = text.lower().strip()
        lowered = lowered.replace("where's", "where is")
        cleaned = re.sub(r"[^a-z0-9\s]", "", lowered)
        return " ".join(cleaned.split())