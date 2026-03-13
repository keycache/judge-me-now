from src.app.constants import SYSTEM_PROMPT_EVALUATOR
from src.app.gemini_client import GeminiClient
from src.app.schemas.interview import Evaluation, Question


def evaluate_candidate_response(
    audio_bytes: bytes, mime_type: str, question: Question, api_key: str
) -> Evaluation:
    """
    Evaluates a candidate's recorded audio response against the ideal answer.

    Args:
        audio_bytes (bytes): The raw audio data recorded by the user.
        mime_type (str): The mime type of the audio (e.g., 'audio/wav' or 'audio/webm').
        question (Question): The Pydantic Question object containing the question text and ideal answer.
        api_key (str): The user's Gemini API key.

    Returns:
        Evaluation: A Pydantic object containing the score, feedback, gaps, and ideal model answer.
    """

    print(f"(Evaluator) Evaluating response for question: {question.value[:50]}...")

    # Construct a specific user prompt injecting the context of the question
    user_prompt = f"""
    The candidate has provided an audio recording as their response.

    Question Asked:
    "{question.value}"

    Ideal Expected Answer / Key Points:
    "{question.answer}"

    Please listen to the attached audio file.
    Compare the candidate's spoken response to the ideal expected answer.
    Evaluate their performance strictly based on the rubric provided in your system instructions.

    Ensure your output is a valid JSON object matching the Evaluation schema:
    {Evaluation.model_json_schema()}

    Do not include $defs $schema or any extra keys. Return only the JSON object with the evaluation results.
    """

    # Initialize the client with the dynamic API key
    client = GeminiClient(api_key=api_key)

    # Call the evaluation method which handles the multimodal audio request
    evaluation = client.evaluate_audio_response(
        audio_bytes=audio_bytes,
        audio_mime_type=mime_type,
        system_prompt=SYSTEM_PROMPT_EVALUATOR,
        user_prompt=user_prompt,
    )

    print(f"(Evaluator) Evaluation complete. Score: {evaluation.score}/10")

    return evaluation
