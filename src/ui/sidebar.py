import streamlit as st

from src.app.jd_processor import process_jd_and_create_session
from src.app.session_manager import SessionManager
from src.ui.constants import (
    STATE_API_KEY,
    STATE_CURRENT_QUESTION,
    STATE_EVALUATION,
    STATE_SESSION_ID,
)


def render_sidebar():
    """
    Renders the Streamlit sidebar for API key input and session management.
    Handles uploading new JDs (Images) and loading existing sessions.
    """
    st.sidebar.title("⚙️ Settings & Setup")

    # --- 1. API Key Input ---
    st.sidebar.subheader("1. API Credentials")
    api_key_input = st.sidebar.text_input(
        "Google Gemini API Key",
        type="password",
        value=st.session_state.get(STATE_API_KEY, ""),
        help="Get your key from Google AI Studio.",
    )

    if api_key_input:
        st.session_state[STATE_API_KEY] = api_key_input
    else:
        st.sidebar.warning("API Key is required to proceed.")

    st.sidebar.divider()

    # --- 2. Session Management ---
    st.sidebar.subheader("2. Interview Session")

    # Use tabs to separate New vs Load workflows cleanly
    tab_new, tab_load = st.sidebar.tabs(["New Session", "Load Session"])

    # --- TAB: New Session ---
    with tab_new:
        st.write(
            "Upload one or more Job Description images to generate 60 tailored questions."
        )
        uploaded_files = st.file_uploader(
            "Upload JD Images",
            type=["png", "jpg", "jpeg"],
            help="Upload screenshots or images of the Job Description.",
            accept_multiple_files=True,
        )

        if st.button("Generate Interview", use_container_width=True):
            if not st.session_state.get(STATE_API_KEY):
                st.error("Please enter your API Key above first.")
            elif not uploaded_files:
                st.error("Please upload at least one image file.")
            else:
                with st.spinner(
                    "Analyzing JD and generating 60 questions... This will take a minute."
                ):
                    try:
                        api_key = st.session_state[STATE_API_KEY]

                        image_inputs = [
                            (uploaded_file.read(), uploaded_file.type)
                            for uploaded_file in uploaded_files
                        ]

                        # Call the backend processor
                        session_id = process_jd_and_create_session(
                            image_inputs=image_inputs,
                            api_key=api_key,
                        )

                        # Update session state with the new session
                        st.session_state[STATE_SESSION_ID] = session_id

                        # Clear any previous question/evaluation state
                        st.session_state.pop(STATE_CURRENT_QUESTION, None)
                        st.session_state.pop(STATE_EVALUATION, None)

                        st.success(f"Session Created: {session_id}")
                    except Exception as e:
                        st.error(f"Failed to generate session: {e}")

    # --- TAB: Load Session ---
    with tab_load:
        st.write("Resume a previously generated interview.")
        sessions = SessionManager.list_sessions()

        if not sessions:
            st.info("No previous sessions found on disk.")
        else:
            selected_session = st.selectbox("Select a session", options=sessions)

            if st.button("Load Session", use_container_width=True):
                st.session_state[STATE_SESSION_ID] = selected_session

                # Clear any previous question/evaluation state
                st.session_state.pop(STATE_CURRENT_QUESTION, None)
                st.session_state.pop(STATE_EVALUATION, None)

                st.success(f"Loaded: {selected_session}")

    st.sidebar.divider()

    # --- 3. Active Session Status ---
    if STATE_SESSION_ID in st.session_state:
        st.sidebar.success(f"🟢 Active: {st.session_state[STATE_SESSION_ID]}")
    else:
        st.sidebar.info("⚪ No active session.")
