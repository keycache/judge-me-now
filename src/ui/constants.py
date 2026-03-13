# --- Page Configuration ---
PAGE_TITLE = "🎙️ AI Interviewer"
PAGE_ICON = "👔"

# --- Streamlit Session State Keys ---
# Using constants for session state keys prevents typos across different files
STATE_API_KEY = "api_key"
STATE_SESSION_ID = "session_id"
STATE_QUESTIONS = "questions"  # Stores the loaded list of Question objects
STATE_CURRENT_QUESTION = (
    "current_question"  # Stores the currently selected Question object
)
STATE_EVALUATION = "evaluation"  # Stores the latest Evaluation result

# --- UI Messages ---
MSG_NO_API_KEY = "Please enter your Google Gemini API Key in the sidebar to continue."
MSG_NO_SESSION = "Please create a new session by uploading a Job Description, or load an existing session from the sidebar."
