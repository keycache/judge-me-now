import json
from typing import List, Tuple

from src.app.constants import SYSTEM_PROMPT_INTERVIEWER
from src.app.gemini_client import GeminiClient
from src.app.schemas.interview import Difficulty, Question
from src.app.session_manager import SessionManager


def process_jd_and_create_session(
    image_inputs: List[Tuple[bytes, str]], api_key: str
) -> str:
    """
    Orchestrates the extraction of interview questions from one or more JD images.
    Makes 3 separate LLM calls to generate 20 questions per difficulty level (Easy, Medium, Hard).
    Saves the combined 60 questions to a new session directory on disk.

    Returns:
        The generated session_id (str).
    """

    client = GeminiClient(api_key=api_key)
    all_questions: List[Question] = []

    # We iterate over the 3 difficulty levels to ensure smaller, more reliable JSON outputs per call.
    difficulties = [Difficulty.EASY, Difficulty.MEDIUM, Difficulty.HARD]

    for difficulty in difficulties:
        print(f"Generating 20 {difficulty.value} questions...")

        # Tailor the user prompt for the specific difficulty level
        schema_hint = json.dumps(
            {
                "questions": [
                    {
                        "value": "...",
                        "category": ["..."],
                        "difficulty": difficulty.value,
                        "answer": "...",
                    }
                ]
            }
        )
        user_prompt = (
            f"Please analyze the provided Job Description image(s). "
            f"Generate exactly 20 {difficulty.value}-level interview questions "
            f"(both technical and behavioral as appropriate for the role). "
            f"For each question, provide a detailed, ideal answer that covers main edge cases. "
            f"Ensure the 'difficulty' field is set to '{difficulty.value}' for all questions in this batch. "
            f"Return ONLY valid JSON with this exact shape: {schema_hint}. "
            "Do not wrap in markdown fences, do not add commentary or extra keys."
        )

        try:
            # Call the LLM (this returns a Pydantic QuestionList object)
            question_list = client.generate_questions_from_image(
                image_inputs=image_inputs,
                system_prompt=SYSTEM_PROMPT_INTERVIEWER,
                user_prompt=user_prompt,
            )

            # Append the generated questions to our master list
            all_questions.extend(question_list.questions)
            print(
                f"Successfully generated {len(question_list.questions)} {difficulty.value} questions."
            )

        except Exception as e:
            # If one batch fails, we log it but raise the exception so the UI can show an error
            print(f"Failed to generate {difficulty.value} questions. Error: {e}")
            raise RuntimeError(
                f"Failed during {difficulty.value} question generation: {e}"
            )

    # Generate a new session and save all 60 questions to the file system
    session_id = SessionManager.create_session()
    SessionManager.save_questions(session_id, all_questions)

    print(
        f"Session {session_id} created successfully with {len(all_questions)} total questions."
    )

    return session_id
