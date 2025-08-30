
import base64
import os  # needed for local testing
import sys
import streamlit as st
st.set_page_config(page_title="ASK Auxiliary Source of Knowledge", initial_sidebar_state="collapsed")
from utils.backends_bridge import load_table_and_date
from uscgaux import stui, stu


stui.apply_ui_styles()


back = st.button("< Back to App", type="primary")
if back:
    st.switch_page("ui.py")


tab1, tab2, tab3, tab4, tab5 = st.tabs(["Overview", "Library", "FAQs", "Product Roadmap", "Feedback"])

with tab1:
    overview = stui.get_markdown("docs/ask_overview.md")
    st.markdown(overview, unsafe_allow_html=True)
    

with tab2:
    try:
        df, last_update_date = load_table_and_date()
    except Exception:
        st.error("Library is unavailable due to a dependency issue. Please try again later.")
        df, last_update_date = (None, "")
    overview = stui.get_markdown("docs/library_overview.md")

    if df is not None:
        num_items = len(df)
        st.markdown("#### Library Overview")
        st.markdown(f"ASK is loaded with **{num_items}** national documents (almost 9000 pages) including USCG Directives, CHDIRAUX documents and documents issued by the USCG Auxiliary National leadership. All these documents are located in public sections of the USCG and USCG Auxiliary websites (cgaux.org uscg.mil).  No secure content is included (i.e., content requiring Member Zone or CAC access). All documents are national in scope as of right now. Regional requirements may vary, so check with your local AOR leadership for the final word. ")
        st.markdown(f"{overview}")
        st.markdown("#### Library Catalog")
        st.markdown(f"{num_items} items. Last update: {last_update_date}")  

        # Display the DataFrame
        desired_cols = ['title', 'publication_number', 'organization', 'issue_date', 'expiration_date', 'scope', 'unit']
        available_cols = [col for col in desired_cols if col in df.columns]
        display_df = df[available_cols]
        edited_df = st.data_editor(display_df, use_container_width=True, hide_index=False, disabled=True)
        isim = f'ASK_catalog_export{last_update_date}.csv'
        indir = edited_df.to_csv(index=False)
        b64 = base64.b64encode(indir.encode(encoding='utf-8')).decode(encoding='utf-8')  
        linko_final = f'<a href="data:file/csv;base64,{b64}" download="{isim}">Click to download the catalog</a>'
        st.markdown(linko_final, unsafe_allow_html=True)

    else:
        # Display the original markdown file content if df is None
        overview = stui.get_markdown("docs/library_overview.md")
        st.markdown(overview, unsafe_allow_html=True)


with tab3:
    overview = stui.get_markdown("docs/faqs.md")
    st.markdown(overview, unsafe_allow_html=True)

with tab4:
    roadmap = stui.get_markdown("docs/roadmap.md")
    st.markdown(roadmap, unsafe_allow_html=True)
    
    
with tab5:
    st.markdown("#### Feedback")
    st.markdown("ASK's mission is to provide USCG Auxiliary members efficient, accuracete and easy access to the authoritative source of knowledge on any topic in the Auxiliary.")
    st.markdown('If you would like to help ASK acheive this mission, **please reach out!**')
                
    st.markdown('''Presently, ASK works by analyzing documents that are the most current official policy that exists at a national level. 
            If you see a document missing from the libary or should be removed, please let us know.''')  
    
    st.markdown('''If you find an error or ommision in a response, please let me know. Be sure to include the exact question asked
            and a reference to the applicable policy (doc and page).''')  
                
    st.markdown('Send an email to uscgaux.drew@wks.us.''')
    

st.markdown(stui.FOOTER, unsafe_allow_html=True) 
