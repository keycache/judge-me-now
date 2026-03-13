import io
import mimetypes
import random
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st
from gtts import gTTS

from src.app.evaluator import evaluate_candidate_response
from src.app.schemas.interview import Answer, Evaluation, Question
from src.app.session_manager import SessionManager
from src.ui.constants import (
    MSG_NO_API_KEY,
    MSG_NO_SESSION,
    STATE_API_KEY,
    STATE_CURRENT_QUESTION,
    STATE_EVALUATION,
    STATE_QUESTIONS,
    STATE_SESSION_ID,
)


def _render_evaluation(evaluation: Evaluation, timestamp: str, height="content"):
    with st.container(height=height):
        if evaluation:
            with st.container(
                horizontal=True,
                horizontal_alignment="distribute",
                vertical_alignment="bottom",
            ):
                st.write(f"**Score:** {evaluation.score}/10")
                selection = st.segmented_control(
                    " ",
                    options=["Feedback", "Gaps", "Ideal Answer"],
                    key=f"eval_view_{timestamp}",
                    default="Feedback",
                )
            if selection == "Feedback":
                st.info(evaluation.feedback)
            elif selection == "Gaps":
                if evaluation.gaps_identified:
                    st.markdown(
                        "\n".join([f"- {gap}" for gap in evaluation.gaps_identified])
                    )
                else:
                    st.success("No major knowledge gaps identified!")
            elif selection == "Ideal Answer":
                st.write(evaluation.model_answer)


def _generate_tts_audio(text: str) -> io.BytesIO:
    """Converts text to speech using gTTS and returns an in-memory byte buffer."""
    tts = gTTS(text=text, lang="en", slow=False)
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    fp.seek(0)
    return fp


def render_interview_view():
    """Renders the main Q&A, TTS, Recording, and Evaluation UI."""
    st.header("🎙️ AI Interview Session")

    # 1. Guard clauses to ensure proper setup
    if not st.session_state.get(STATE_API_KEY):
        st.warning(MSG_NO_API_KEY)
        return

    if not st.session_state.get(STATE_SESSION_ID):
        st.info(MSG_NO_SESSION)
        return

    # 2. Load questions for the active session
    session_id = st.session_state[STATE_SESSION_ID]
    try:
        # Cache questions in state to avoid reading disk on every rerun
        if (
            STATE_QUESTIONS not in st.session_state
            or st.session_state.get("loaded_session") != session_id
        ):
            questions = SessionManager.load_questions(session_id)
            st.session_state[STATE_QUESTIONS] = questions
            st.session_state["loaded_session"] = session_id
    except Exception as e:
        st.error(f"Failed to load questions for session {session_id}. Error: {e}")
        return

    questions = st.session_state[STATE_QUESTIONS]

    st.success(
        f"Active Session: `{session_id}` | Questions available: {len(questions)}"
    )
    st.divider()

    # 3. Question Selection
    col1, col2 = st.columns([3, 1])
    with col1:
        # Create a mapping to easily select questions by their text
        question_options = {
            f"[{q.difficulty.value}] {q.category[0]}: {q.value[:60]}...": q
            for q in questions
        }
        selected_q_label = st.selectbox(
            "Select a question:", options=list(question_options.keys()), index=0
        )
        st.session_state[STATE_CURRENT_QUESTION] = question_options[selected_q_label]

    with col2:
        st.write("")  # Spacing
        st.write("")  # Spacing
        if st.button("🎲 Pick Random", use_container_width=True):
            random_q = random.choice(questions)
            # Update state to force the selectbox/UI to update
            st.session_state[STATE_CURRENT_QUESTION] = random_q
            st.session_state.pop(STATE_EVALUATION, None)
            st.rerun()

    # Determine which question is currently active
    current_question: Question = st.session_state.get(
        STATE_CURRENT_QUESTION, question_options[selected_q_label]
    )

    # If the user changed the selectbox manually, update state
    if (
        current_question != question_options[selected_q_label]
        and STATE_CURRENT_QUESTION not in st.session_state
    ):
        current_question = question_options[selected_q_label]
        st.session_state[STATE_CURRENT_QUESTION] = current_question

    # Clear evaluation if the question changes
    if (
        "last_question_value" not in st.session_state
        or st.session_state["last_question_value"] != current_question.value
    ):
        st.session_state.pop(STATE_EVALUATION, None)
        st.session_state["last_question_value"] = current_question.value

    # 4. Display the Question
    st.markdown(
        f"**Category:** `{', '.join(current_question.category)}` | **Difficulty:** `{current_question.difficulty.value}`"
    )
    st.subheader(f"Question: {current_question.value}")

    # 5. Text-to-Speech (TTS)
    # We generate the audio buffer and use st.audio to play it.
    # autoplay=True is supported in Streamlit >= 1.33
    # with st.spinner("Generating audio..."):
    #     tts_buffer = _generate_tts_audio(current_question.value)
    #     st.audio(tts_buffer, format="audio/mp3", autoplay=False)

    st.divider()

    # 6. Audio Recording & Submission
    # st.write("### Your Answer")

    # We use the question's text hash as a key so the audio input resets for new questions
    with st.container(
        horizontal=True, horizontal_alignment="distribute", vertical_alignment="center"
    ):
        audio_data = st.audio_input(
            "Record your answer", key=f"audio_{hash(current_question.value)}"
        )
        new_answer = None
        if st.button("Submit Answer", type="primary", disabled=audio_data is None):
            try:
                audio_bytes = audio_data.read()
                audio_mime = audio_data.type or "audio/wav"

                if not audio_bytes:
                    st.toast(
                        "Captured audio is empty. Please re-record and submit.",
                        duration="infinite",
                        icon="⚠️",
                    )
                    return

                st.toast(
                    f"Captured audio: {len(audio_bytes)/1024:.1f} KB ({audio_mime})",
                    duration="long",
                    icon="ℹ️",
                )

                # Persist audio to disk
                audio_path = SessionManager.save_answer_audio(
                    session_id=session_id,
                    question=current_question,
                    audio_bytes=audio_bytes,
                    mime_type=audio_mime,
                )

                evaluation = evaluate_candidate_response(
                    audio_bytes=audio_bytes,
                    mime_type=audio_mime,
                    question=current_question,
                    api_key=st.session_state[STATE_API_KEY],
                )

                new_answer = Answer(
                    audio_file_path=audio_path,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    evaluation=evaluation,
                )

                updated_answers = list(current_question.answers or [])
                updated_answers.append(new_answer)
                updated_question = current_question.model_copy(
                    update={"answers": updated_answers}
                )

                updated_questions = []
                for q in questions:
                    if q.value == current_question.value:
                        updated_questions.append(updated_question)
                    else:
                        updated_questions.append(q)

                SessionManager.save_questions(session_id, updated_questions)
                st.session_state[STATE_QUESTIONS] = updated_questions
                st.session_state[STATE_CURRENT_QUESTION] = updated_question
                current_question = updated_question
                questions = updated_questions
                st.session_state[STATE_EVALUATION] = evaluation
            except Exception as e:
                st.toast("Evaluation failed", duration="long", icon="⚠️")
                print(f"Error during evaluation: {e}")

    # 7. Display Evaluation Results
    if STATE_EVALUATION in st.session_state:
        evaluation: Evaluation = st.session_state[STATE_EVALUATION]
        st.divider()
        with st.expander("Open to see **Evaluation Results**", expanded=False):
            _render_evaluation(
                evaluation, timestamp="evaluation_timestamp", height="content"
            )
    else:
        st.info("Record and submit your answer to see the evaluation results here.")

    # Past answers playback
    if current_question.answers:
        height_per_answer = 350
        with st.expander(
            f"📁 Past Answers ({len(current_question.answers)})", expanded=False
        ):
            for ans in sorted(current_question.answers, key=lambda a: a.timestamp):
                st.divider()
                col1, col2 = st.columns(2)
                with col1:
                    with st.container(height=height_per_answer):
                        st.caption(f"Recorded at {ans.timestamp}")
                        try:
                            audio_path = Path(ans.audio_file_path)
                            with audio_path.open("rb") as f:
                                guessed_mime, _ = mimetypes.guess_type(audio_path)
                                st.audio(f.read(), format=guessed_mime or "audio/wav")
                            transcription = (
                                f"`{ans.evaluation.candidate_answer}`"
                                if ans.evaluation
                                else "Transcription not available"
                            )
                            st.write(transcription)
                        except FileNotFoundError:
                            st.warning(f"Audio file missing: {ans.audio_file_path}")
                with col2:
                    (
                        _render_evaluation(
                            ans.evaluation,
                            timestamp=ans.timestamp,
                            height=height_per_answer,
                        )
                        if ans.evaluation
                        else st.info("Evaluation not available for this answer yet.")
                    )

            st.divider()
