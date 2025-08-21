import os
import sys
import pytest
import streamlit as st

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# This uses pytest to test the response quality of the RAG pipeline using ground truth questions. It works however langsmith is so much easier to use.

# Skip tests if required secrets are missing
required_secrets = ["LANGCHAIN_API_KEY", "QDRANT_URL", "QDRANT_API_KEY", "OPENAI_API_KEY_ASK"]
try:
    missing = [s for s in required_secrets if st.secrets.get(s) is None]
    if missing:
        pytest.skip(f"Missing Streamlit secrets: {', '.join(missing)}", allow_module_level=True)
except Exception:
    pytest.skip("No Streamlit secrets found", allow_module_level=True)

from utils import ui_utils
from utils import rag
from utils.rag import CONFIG

# Config Langsmith
os.environ["LANGCHAIN_API_KEY"] = st.secrets["LANGCHAIN_API_KEY"]
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "test_response_quality"


def load_questions_from_file(filename="pytests/user_question_list.txt"):
    with open(filename, "r") as file:
        questions = [line.strip() for line in file if line.strip()]
    return questions

questions = load_questions_from_file()

@pytest.mark.parametrize("question", questions)
def test_rag_pipeline_responses(question):

    response, enriched_question = rag.rag(question)
    print({question})
    print({response['answer']})
    # print(f"{response['answer']}")
    
    # Assert the response is not empty
    assert response, f"Response for question '{question}' is empty."



# Run this test file with `pytest -s pytests/test_response_quality.py` 
