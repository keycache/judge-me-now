from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class Difficulty(str, Enum):
    EASY = "Easy"
    MEDIUM = "Medium"
    HARD = "Hard"


class Evaluation(BaseModel):
    score: int = Field(
        ...,
        description="Score out of 10 based on the candidate's accuracy, completeness, and communication",
    )
    candidate_answer: str = Field(
        ...,
        description="A text transcription of the candidate's spoken answer for reference",
    )
    feedback: str = Field(
        ...,
        description="Detailed, constructive feedback on the candidate's audio response",
    )
    gaps_identified: List[str] = Field(
        ...,
        description="Specific knowledge gaps, missing edge cases, or incorrect statements in the response",
    )
    model_answer: str = Field(
        ...,
        description="How the ideal answer should have been structured and explained",
    )


class Answer(BaseModel):
    audio_file_path: str = Field(
        ...,
        description="The file path to the candidate's recorded answer audio on disk",
    )
    timestamp: str = Field(
        ...,
        description="The ISO 8601 timestamp of when the answer was submitted",
    )
    evaluation: Optional[Evaluation] = Field(
        None,
        description="The evaluation of the candidate's answer (populated after evaluation)",
    )


class Question(BaseModel):
    value: str = Field(..., description="The question text")
    category: List[str] = Field(
        ...,
        description="The categories associated with the question (e.g., Python, System Design, Behavioral)",
    )
    difficulty: Difficulty = Field(
        ..., description="The difficulty level of the question"
    )
    answer: str = Field(
        ...,
        description="The correct answer to the question, covering most of the cases relevant to the question",
    )
    answers: Optional[List[Answer]] = Field(
        None,
        description="The list of the candidates answers to the question over a period of time",
    )


class QuestionList(BaseModel):
    """Wrapper model to ensure the LLM returns a structured list of questions."""

    questions: List[Question] = Field(
        ..., description="List of generated interview questions"
    )
