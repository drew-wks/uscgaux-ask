import os  # needed for local testing
import uuid
import pandas as pd
import streamlit as st

st.set_page_config(page_title="ASK Auxiliary Source of Knowledge", initial_sidebar_state="collapsed")

from streamlit_feedback import streamlit_feedback
from langsmith import Client
from streamlit_extras.stylable_container import stylable_container


# Config LangSmith
os.environ["LANGCHAIN_API_KEY_ASK"] = st.secrets["LANGCHAIN_API_KEY"] # check which account you are using
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "ui.py on ASK main/cloud" # use this for local testing


from utils.backends_bridge import get_backend_container, fetch_table_and_date
from utils import rag
from uscgaux import stui, stu
import sidebar   

stui.apply_ui_styles()

from langsmith import traceable




# Check Open AI service status
api_status_message = stu.get_openai_api_status()
if "operational" not in api_status_message:
    st.error(f"ASK is currently down due to OpenAI issue: '{api_status_message}.'")
else: 
    st.write("#### Get answers to USCG Auxiliary questions from authoritative sources.")

# Ensure variables exist even if initialization fails
df: pd.DataFrame = pd.DataFrame()
last_update_date: str = ""

try:
    backend_connectors = get_backend_container()
    df, last_update_date = fetch_table_and_date(backend_connectors)
except Exception as exc:
    import logging
    logging.getLogger(__name__).exception("Backend init/fetch failed")
    st.error("ASK is currently unavailable due to a dependency issue. Please try again later.")
    # Fallback to empty catalog so downstream code can render

num_items = len(df)


# Main app body copy
st.markdown(f"ASK uses Artificial Intelligence (AI) to search {num_items} Coast Guard Auxiliary references for answers. This is a working prototype for evaluation. Not an official USCG Auxiliary service. Learn more <a href='Library' target='_self'><b>here</b></a>.", unsafe_allow_html=True)
example_questions = st.empty()
example_questions.write("""  
    **ASK can answer questions such as:**   
    *What are the requirements to run for FC?*  
    *How do I stay current in boat crew?*   
    *¿En que ocasiones es necesario un saludo militar?*   
""")
st.write("  ")


ls_client = Client(api_key=st.secrets["LANGCHAIN_API_KEY"])


def langsmith_feedback(feedback_data):
    """Send user feedback to LangSmith."""
    score = 1.0 if feedback_data["score"] == "👍" else 0.0
    run_id = st.session_state.get("run_id")  
    if run_id:
        print(f"Sending feedback for run_id: {run_id}")
        ls_client.create_feedback(
            run_id=run_id,
            key="user_feedback",
            score=score,
            comment=feedback_data["text"],
        )
    else:
        st.warning("Run ID not found. Feedback not sent.")


@st.cache_data(show_spinner=False)
def cached_rag(question, filter_selections, run_id):
    """Wrapper to run the RAG pipeline with caching & feedback support."""
    return rag.rag(
        user_question=question,
        filter_conditions=filter_selections,
        langsmith_extra={"run_id": run_id}
    )


def initialize_session_states():
    if "run_id" not in st.session_state:
        st.session_state["run_id"] = None
    if "user_question" not in st.session_state:
        st.session_state["user_question"] = None
    if "response" not in st.session_state:
        st.session_state["response"] = None
    if "filter_conditions" not in st.session_state:
        st.session_state.filter_conditions = {}

initialize_session_states()
st.session_state["filter_conditions"] = sidebar.build_sidebar()



# >>> Main RAG pipeline <<<
user_question = st.text_input("Type your question or task here", max_chars=200)

# On new user_question, clear previous response and feedback
if user_question and (user_question != st.session_state["user_question"]):
    st.session_state["user_question"] = user_question
    st.session_state.pop("response", None)
    st.session_state["run_id"] = str(uuid.uuid4())
    print(">>> 🧑‍💼 New user question submited  <<<")

status_placeholder = st.empty()
    # Generate the response only if the question is new
if st.session_state.get("user_question") and "response" not in st.session_state:
    # Generate a response
    with status_placeholder.status(label="Checking documents...", expanded=False) as response_container:
        st.session_state["response"] = cached_rag(
            st.session_state["user_question"], st.session_state.filter_conditions, st.session_state["run_id"]
        )

# Format Response
if st.session_state.get("response"):
    status_placeholder.empty()
    response = st.session_state["response"]
    short_source_list, long_source_list = rag.create_source_lists(response)
    example_questions.empty()  
    # Show active filter summary chip above results
    fc = st.session_state.get("filter_conditions", {}) or {}
    scope = str(fc.get("scope", "National")).strip()
    units = fc.get("units", []) or []
    units_label = ", ".join(units) if units else ("All" if scope in ("District", "Both") else "—")
    chip_html = f"""
        <div style='display:inline-block;padding:6px 10px;border-radius:16px;background:#eef2ff;color:#3730a3;font-size:12px;margin-bottom:8px;'>
            Scope: <b>{scope}</b>{' · Districts: ' + units_label if scope in ('District','Both') else ''}
        </div>
    """
    st.markdown(chip_html, unsafe_allow_html=True)

    st.info(f"**Question:** *{user_question}*\n\n ##### Response:\n{response['answer']}\n\n **Sources:**  \n{short_source_list}\n **Note:** \n ASK can make mistakes. Verify the sources and check your local policies.")
    print("📫  Response delivered to user")

    # Create a container and fill with references
    with st.expander("CLICK HERE FOR FULL SOURCE DETAILS", expanded=False):
        st.write(long_source_list)


    # Show user feedback widget once a response is returned
    user_feedback = streamlit_feedback(
        feedback_type="thumbs",
        optional_text_label="(Optional) Please explain your rating, so we can improve ASK",
        align="flex-start",
        key=f"user_feedback_{st.session_state.run_id}" # 👈 Unique per response to ensure widget resets
    )

    if user_feedback:
        st.write("Thanks for the feedback!")
        langsmith_feedback(user_feedback)

# Lock the chat input container 50 pixels above bottom of viewport
with stylable_container(
    key="bottom_content",
    css_styles="""
        {
            position: fixed;
            bottom: 0px;
            background-color: rgba(255, 255, 255, 1)
        }
        """,
):
    st.markdown(
    """
    <style>
        .stChatFloatingInputContainer {
            bottom: 50px;
            background-color: rgba(255, 255, 255, 1)
        }
    </style>
    """,
    unsafe_allow_html=True,
    )

st.markdown(stui.FOOTER, unsafe_allow_html=True)
