import os

import requests
import streamlit as st

from dotenv import load_dotenv

load_dotenv()

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")

st.set_page_config(page_title="Insurance Knowledge Search", page_icon="📄")
st.title("Insurance Knowledge Search")

if "history" not in st.session_state:
    st.session_state.history = []

source_label = st.sidebar.radio("Quelle", ["Alle", "Confluence", "Jira"])
source_filter = None if source_label == "Alle" else source_label.lower()

question = st.chat_input("Frage stellen...")
if question:
    payload = {"question": question, "source": source_filter}
    response = requests.post(f"{API_BASE_URL}/ask", json=payload, timeout=60)
    response.raise_for_status()
    st.session_state.history.append((question, response.json()))

for question, result in reversed(st.session_state.history):
    with st.chat_message("user"):
        st.write(question)
    with st.chat_message("assistant"):
        st.write(result["answer"])
        trace = result.get("trace")
        if trace:
            with st.expander("Agent trace"):
                st.write(f"Route: {trace['route_source']}")
                st.write(f"Route reason: {trace['route_reason']}")
                st.write(f"Rewrite changed: {trace['rewrite_changed']}")
                st.write(f"Rewritten query: {trace['rewritten_query']}")
                st.write(f"Evidence: {trace['evidence_status']}")
                st.write(f"Evidence reason: {trace['evidence_reason']}")
        for source in result["sources"]:
            with st.expander(f"[{source['id']}] {source['title']} ({source['source']})"):
                st.write(source["content"])
                st.markdown(f"[Original öffnen]({source['url']})")
