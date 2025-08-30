import os
import sys
import streamlit as st
st.set_page_config(page_title="ASK Auxiliary Source of Knowledge", initial_sidebar_state="collapsed")
from uscgaux import streamlit_ui_utils as stui


stui.apply_ui_styles()


back = st.button("< Back to App", type="primary")
if back:
    st.switch_page("ui.py")

tos = stui.get_markdown("docs/tos.md")

st.markdown("#### Terms of Service")
st.write("")
st.markdown(f"{tos}")

