import streamlit as st

# Import UI constants
from src.ui.constants import PAGE_ICON, PAGE_TITLE, STATE_API_KEY, STATE_SESSION_ID

# Import UI components
from src.ui.interview_view import render_interview_view
from src.ui.sidebar import render_sidebar


def main():
    """
    Main entry point for the AI Interviewer Streamlit application.
    Handles page routing and conditional rendering based on session state.
    """
    # 1. Page Configuration (Must be the first Streamlit command)
    st.set_page_config(
        page_title=PAGE_TITLE,
        page_icon=PAGE_ICON,
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # 2. Render the Sidebar (Always visible)
    render_sidebar()

    # 3. Application Routing / Main Content Area

    # State A: User hasn't provided an API key yet
    if not st.session_state.get(STATE_API_KEY):
        st.title(f"{PAGE_ICON} {PAGE_TITLE}")
        st.info("👋 Welcome to your personal AI Interviewer!")
        st.write(
            "To get started, please enter your **Google Gemini API Key** "
            "in the sidebar on the left."
        )
        st.markdown(
            "*(Don't have an API key? You can get a free one from "
            "[Google AI Studio](https://aistudio.google.com/app/apikey).)*"
        )
        return

    # State B: API key provided, but no active interview session
    if not st.session_state.get(STATE_SESSION_ID):
        st.title(f"{PAGE_ICON} {PAGE_TITLE}")
        st.success("API Key successfully loaded! ✅")
        st.write("### Next Steps:")
        st.markdown(
            """
            Please look at the sidebar on the left and choose one of the following:

            *   **New Session**: Upload an image (screenshot) of a Job Description. The AI will analyze it and generate 60 highly tailored interview questions (Easy, Medium, Hard).
            *   **Load Session**: Resume a previously generated interview from your local history.
            """
        )
        return

    # State C: API key provided AND an active session is loaded -> Show the Interview UI
    render_interview_view()


if __name__ == "__main__":
    main()
