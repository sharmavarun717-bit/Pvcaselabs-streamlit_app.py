# Document Management page moved into ICSR Case Processing as the Documents tab.
# This file is retained in the repository for compatibility but is intentionally
# not linked in app navigation; built-in page navigation is disabled in
# .streamlit/config.toml. Open the main app and select ICSR Case Processing > Documents.
import streamlit as st

st.set_page_config(page_title="PV Case Lab", page_icon="🧬", layout="wide")
st.info("Document Management is now available inside ICSR Case Processing, after the Narrative tab. Return to the main app to upload or view case documents.")
