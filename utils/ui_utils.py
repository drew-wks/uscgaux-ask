import os  # needed for local testing
import requests
import streamlit as st
from pathlib import Path


parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Apply global font styling
GLOBAL_STYLE = """
    <style>
        html, body, [class*="st-"] {font-family: "Source Sans Pro", "Arial", "Helvetica", sans-serif !important;}
    </style>
    """

# Hide Streamlit's default UI elements while preserving sidebar toggle
HIDE_STREAMLIT_UI = """
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
    </style>
    """

BLOCK_CONTAINER = """
        <style>
                .block-container {
                    padding-top: 1rem;
                    padding-bottom: 1rem;
                    padding-left: 3rem;
                    padding-right: 3rem;
                }
        </style>
        """

BLOCK_CONTAINER_2 = """
        <style>
                .block-container {
                    padding-top: 0rem;
                    padding-bottom: 1rem;
                    padding-left: 2rem;
                    padding-right: 2rem;
                }
        </style>
        """

FOOTER = """
    <style>
        .app-footer {
            bottom: 0;
            position: sticky;
            font-size: smaller;
            width: 700px;
            margin: auto;
            background: white;
            padding: 10px;
            border-top: 1px solid #ccc;
            text-align: left;
        }
    </style>
    <br><br>
    <div class="app-footer">
        <a href="Terms_of_service" target="_self">Terms of service</a>
    </div>
    """

LOGO = "https://raw.githubusercontent.com/drew-wks/ASK/main/images/ASK_logotype_color.png?raw=true"


def apply_styles():
    st.markdown(GLOBAL_STYLE, unsafe_allow_html=True)
    st.markdown(HIDE_STREAMLIT_UI, unsafe_allow_html=True)
    st.markdown(BLOCK_CONTAINER_2, unsafe_allow_html=True)
    st.image(LOGO, use_container_width=True)


@st.cache_data
def get_openai_api_status():
    """Notify user if OpenAI is down so they don't blame the app"""

    components_url = "https://status.openai.com/api/v2/components.json"
    status_message = ""

    try:
        response = requests.get(components_url, timeout=10)
        # Raises an HTTPError if the HTTP request returned an unsuccessful status code
        response.raise_for_status()
        components_info = response.json()
        components = components_info.get("components", [])

        # Find the component that represents the API
        chat_component = next(
            (
                component
                for component in components
                if component.get("name", "").lower() == "chat"
            ),
            None,
        )

        if chat_component:
            status_message = chat_component.get("status", "unknown")
            return (
                f"ChatGPT API status: {status_message}"
                if status_message != "operational"
                else "ChatGPT API is operational"
            )
        else:
            return "ChatGPT API component not found"

    except requests.exceptions.HTTPError as http_err:
        return f"API check failed (HTTP error): {repr(http_err)}"
    except requests.exceptions.Timeout:
        return "API check timed out"
    except requests.exceptions.RequestException as req_err:
        return f"API check failed (Request error): {repr(req_err)}"
    except Exception as err:
        return f"API check failed (Unknown error): {repr(err)}"


def get_markdown(markdown_file):
    return Path(markdown_file).read_text()


def main():
    print("Running utils.py directly")
    # You can include test code for utility functions here, if desired


if __name__ == "__main__":
    main()
