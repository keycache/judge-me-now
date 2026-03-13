import json
import re
from typing import Any, Dict, List, Optional, Tuple

from google.genai import Client, types

from src.app.constants import Model
from src.app.schemas.interview import Evaluation, QuestionList


class GeminiClient:
    def __init__(self, api_key: str):
        """
        Initialize the Gemini Client with the API key provided from the Streamlit UI.
        """
        self.client = Client(api_key=api_key)

    def _clean_json_string(self, text: str) -> str:
        """
        Helper method to strip markdown formatting if Gemini returns the JSON
        wrapped in ```json ... ``` blocks.
        """
        text = text.strip()
        if text.startswith("```json"):
            text = text[len("```json") :]
        if text.startswith("```"):
            text = text[len("```") :]
        if text.endswith("```"):
            text = text[: -len("```")]
        return text.strip()

    def _extract_first_json_object(self, text: str) -> str:
        """Best-effort extraction of the first JSON object for lenient parsing."""
        match = re.search(r"\{.*\}", text, re.S)
        if not match:
            raise ValueError("No JSON object found in model response.")
        return match.group(0).strip()

    def generate_questions_from_image(
        self,
        image_inputs: List[Tuple[bytes, str]],
        system_prompt: str,
        user_prompt: str,
        model_name: str = Model.GEMINI_MULTIMODAL_FAST,
    ) -> QuestionList:
        """
        Passes one or more Job Description images to Gemini to generate a list of questions.
        """
        if not image_inputs:
            raise ValueError("At least one JD image is required.")

        config = {"response_mime_type": "application/json"}

        # Allow multiple JD images by appending all image parts before the user prompt text.
        image_parts = [
            types.Part.from_bytes(data=img_bytes, mime_type=img_mime_type)
            for img_bytes, img_mime_type in image_inputs
        ]

        contents = [
            types.Content(
                role="model", parts=[types.Part.from_text(text=system_prompt)]
            ),
            types.Content(
                role="user",
                parts=[*image_parts, types.Part.from_text(text=user_prompt)],
            ),
        ]

        print(f"(GeminiClient.generate_questions) Generating with model: {model_name}")

        response = self.client.models.generate_content(
            model=model_name, contents=contents, config=config
        )

        # Clean and parse the JSON string
        if not response.text:
            raise ValueError("Model returned an empty response.")

        raw_text = response.text
        clean_json = self._clean_json_string(raw_text)

        parsed_data: Optional[Dict[str, Any]] = None
        last_error: Optional[Exception] = None

        # Try strict clean text first, then fall back to a lenient extraction.
        for candidate in [clean_json]:
            try:
                parsed_data = json.loads(candidate)
                break
            except Exception as e:  # json.JSONDecodeError or similar
                last_error = e

        if parsed_data is None:
            try:
                extracted = self._extract_first_json_object(raw_text)
                parsed_data = json.loads(extracted)
            except Exception as e:
                last_error = e

        if parsed_data is None:
            snippet = clean_json[:500]
            print(
                f"(GeminiClient.generate_questions) Failed to parse output: {clean_json}"
            )
            raise ValueError(
                f"Failed to parse LLM output into JSON. Error: {last_error}. Snippet: {snippet}"
            )

        try:
            # Validate and convert dictionary to Pydantic QuestionList object
            return QuestionList.model_validate(parsed_data)
        except Exception as e:
            snippet = json.dumps(parsed_data)[:500] if parsed_data is not None else ""
            raise ValueError(
                f"Failed to validate LLM JSON against QuestionList schema. Error: {e}. Parsed snippet: {snippet}"
            )

    def evaluate_audio_response(
        self,
        audio_bytes: bytes,
        audio_mime_type: str,
        system_prompt: str,
        user_prompt: str,
        model_name: str = Model.GEMINI_MULTIMODAL_FAST,
    ) -> Evaluation:
        """
        Passes the user's recorded audio answer to Gemini to evaluate against the rubric.
        """
        config = {"response_mime_type": "application/json"}

        # Create the audio part
        audio_part = types.Part.from_bytes(data=audio_bytes, mime_type=audio_mime_type)

        contents = [
            types.Content(
                role="model", parts=[types.Part.from_text(text=system_prompt)]
            ),
            types.Content(
                role="user", parts=[audio_part, types.Part.from_text(text=user_prompt)]
            ),
        ]

        print(f"(GeminiClient.evaluate_audio) Evaluating with model: {model_name}")

        response = self.client.models.generate_content(
            model=model_name, contents=contents, config=config
        )

        # Clean and parse the JSON string
        clean_json = self._clean_json_string(response.text)

        try:
            parsed_data: Dict[str, Any] = json.loads(clean_json)
            # Validate and convert dictionary to Pydantic Evaluation object
            return Evaluation.model_validate(parsed_data)
        except Exception as e:
            print(f"(GeminiClient.evaluate_audio) Failed to parse output: {clean_json}")
            raise ValueError(
                f"Failed to parse LLM output into Evaluation schema. Error: {e}"
            )
