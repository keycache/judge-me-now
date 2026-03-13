import json
import mimetypes
import re
from datetime import datetime
from typing import List

from src.app.constants import SESSIONS_DIR
from src.app.schemas.interview import Question


class SessionManager:
    """
    Handles local file system operations for creating and persisting interview sessions.
    Saves generated Pydantic Question objects to disk so they can be loaded later.
    """

    @staticmethod
    def _ensure_base_dir():
        """Creates the base data/sessions directory if it doesn't exist."""
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def create_session() -> str:
        """
        Generates a new session ID based on the current timestamp
        and creates the corresponding directory.
        """
        SessionManager._ensure_base_dir()

        # e.g., session_20231027_153022
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_id = f"session_{timestamp}"

        session_path = SESSIONS_DIR / session_id
        session_path.mkdir(parents=True, exist_ok=True)

        return session_id

    @staticmethod
    def save_questions(session_id: str, questions: List[Question]) -> str:
        """
        Serializes a list of Pydantic Question objects and saves them to a JSON file
        in the specified session directory.
        """
        session_path = SESSIONS_DIR / session_id
        session_path.mkdir(parents=True, exist_ok=True)

        file_path = session_path / "questions.json"

        # Convert Pydantic models to dicts using v2 syntax
        data = [q.model_dump() for q in questions]

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

        return str(file_path)

    @staticmethod
    def save_answer_audio(
        session_id: str, question: Question, audio_bytes: bytes, mime_type: str
    ) -> str:
        """
        Persists a recorded answer's audio to disk inside the session directory.
        Returns the full file path for later playback.
        """

        SessionManager._ensure_base_dir()
        session_path = SESSIONS_DIR / session_id
        answers_dir = session_path / "answers"
        answers_dir.mkdir(parents=True, exist_ok=True)

        ext = mimetypes.guess_extension(mime_type) or ".wav"
        safe_slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", question.value[:50]).strip("_")
        safe_slug = safe_slug or "answer"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = answers_dir / f"{safe_slug}_{timestamp}{ext}"

        with open(file_path, "wb") as f:
            f.write(audio_bytes)

        return str(file_path)

    @staticmethod
    def list_sessions() -> List[str]:
        """
        Scans the sessions directory and returns a list of valid session IDs.
        A valid session must contain a questions.json file.
        Returns the list sorted descending (newest first).
        """
        SessionManager._ensure_base_dir()

        valid_sessions = []
        for path in SESSIONS_DIR.iterdir():
            if path.is_dir() and (path / "questions.json").exists():
                valid_sessions.append(path.name)

        # Sort descending so the most recent session appears at the top of the UI list
        return sorted(valid_sessions, reverse=True)

    @staticmethod
    def load_questions(session_id: str) -> List[Question]:
        """
        Reads a session's questions.json file and deserializes it back
        into a list of Pydantic Question objects.
        """
        file_path = SESSIONS_DIR / session_id / "questions.json"

        if not file_path.exists():
            raise FileNotFoundError(
                f"No questions.json found for session: {session_id}"
            )

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Parse the dicts back into Pydantic Question models using v2 syntax
        return [Question.model_validate(q) for q in data]
