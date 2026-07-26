import os
import requests
import streamlit as st

# Configure page settings
st.set_page_config(
    page_title="Codebase Tutor",
    page_icon="🤖",
    layout="centered", # Centered layout matches ChatGPT/Claude desktop reading width
    initial_sidebar_state="expanded"
)

# Backend URL configuration
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# Inject minimalist styling for a pure chat layout
st.markdown("""
<style>
    /* Clean up default Streamlit padding */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 5rem;
    }
    /* Sleek centered landing text */
    .chat-hero {
        text-align: center;
        margin-top: 10vh;
        margin-bottom: 2vh;
    }
    .chat-hero h1 {
        font-size: 2.8em;
        font-weight: 700;
        color: #1e293b;
    }
    .chat-hero p {
        font-size: 1.2em;
        color: #64748b;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Session State variables
if "repo_id" not in st.session_state:
    st.session_state.repo_id = ""
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "repo_title" not in st.session_state:
    st.session_state.repo_title = ""

# --- SIDEBAR: SETTINGS & INGESTION ONLY ---
with st.sidebar:
    st.title("🤖 Codebase Tutor")
    st.caption("Pure Chat-RAG Workspace")
    st.divider()
    
    # 1. API Service Configurations
    st.markdown("### 🔌 Connection Settings")
    backend_input = st.text_input("FastAPI Endpoint", value=BACKEND_URL)
    if backend_input != BACKEND_URL:
        BACKEND_URL = backend_input
        
    st.divider()
    
    # 2. Ingest codebase
    st.markdown("### 📁 Select Repository")
    repo_option = st.selectbox(
        "Choose Codebase",
        ["setup.py (Demo)", "⚡ Link Custom GitHub Repo"],
        index=0
    )
    
    repo_url = ""
    if repo_option == "setup.py (Demo)":
        repo_url = "https://github.com/kennethreitz/setup.py"
    else:
        repo_url = st.text_input(
            "GitHub Repository URL",
            placeholder="https://github.com/pallets/click"
        )
        
    if st.button("🚀 Ingest & Index Codebase", disabled=not repo_url, type="primary", use_container_width=True):
        with st.spinner("⚡ Processing codebase..."):
            try:
                # Call POST /ingest
                resp = requests.post(f"{BACKEND_URL}/ingest", json={"repo_url": repo_url})
                if resp.status_code == 200:
                    data = resp.json()
                    st.session_state.repo_id = data["repo_id"]
                    st.session_state.chat_history = []
                    st.session_state.repo_title = repo_option if repo_option != "⚡ Link Custom GitHub Repo" else repo_url.split("github.com/")[-1]
                    st.success("🎉 Repository active!")
                else:
                    st.error(f"Ingestion failed: {resp.text}")
            except Exception as e:
                st.error(f"Failed to connect to backend: {e}")

# --- MAIN CHAT CONTAINER ---
if not st.session_state.repo_id:
    # EMPTY LANDING STATE (Matches Claude/ChatGPT startup)
    st.markdown("""
    <div class='chat-hero'>
        <h1>🤖 Codebase Tutor</h1>
        <p>Please ingest a codebase in the sidebar on the left to start chatting.</p>
    </div>
    """, unsafe_allow_html=True)
else:
    # ACTIVE CHAT STATE
    # If chat history is empty, show a centered welcoming prompt
    if not st.session_state.chat_history:
        st.markdown(f"""
        <div class='chat-hero' style='margin-top: 15vh;'>
            <h1 style='font-size: 2.2em;'>🤖 Codebase Tutor: {st.session_state.repo_title}</h1>
            <p style='font-size: 1.1em;'>How can I help you understand this repository today?</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Loop and render clean, pure chat logs
        for msg in st.session_state.chat_history:
            avatar = "🤖" if msg["role"] == "assistant" else "👤"
            with st.chat_message(msg["role"], avatar=avatar):
                st.markdown(msg["content"])
                
                # Render sources cleanly in a collapsed expander below the answer
                if msg["role"] == "assistant" and "citations" in msg and msg["citations"]:
                    with st.expander("📄 View Sources & Citations", expanded=False):
                        for idx, cite in enumerate(msg["citations"]):
                            ref_lbl = f"Ref: `{cite['ref']}`" if cite['ref'] else "Logical Inference"
                            st.markdown(f"**[{cite['type'].upper()}]** {ref_lbl} | *\"{cite['excerpt']}\"*")

    # Pure floating chat input locked at the bottom
    user_q = st.chat_input("Ask a question about the code or history...")
    
    if user_q:
        # Immediately render user question
        with st.chat_message("user", avatar="👤"):
            st.markdown(user_q)
        st.session_state.chat_history.append({"role": "user", "content": user_q})
        
        # Make API call to backend /ask
        with st.spinner("Tutor is reading code..."):
            try:
                resp = requests.post(f"{BACKEND_URL}/ask", json={
                    "repo_id": st.session_state.repo_id,
                    "question": user_q
                })
                if resp.status_code == 200:
                    data = resp.json()
                    answer = data["answer"]
                    citations = data.get("citations", [])
                    
                    # Render AI response
                    with st.chat_message("assistant", avatar="🤖"):
                        st.markdown(answer)
                        if citations:
                            with st.expander("📄 View Sources & Citations", expanded=False):
                                for idx, cite in enumerate(citations):
                                    ref_lbl = f"Ref: `{cite['ref']}`" if cite['ref'] else "Logical Inference"
                                    st.markdown(f"**[{cite['type'].upper()}]** {ref_lbl} | *\"{cite['excerpt']}\"*")
                                    
                    # Cache in history
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": answer,
                        "citations": citations
                    })
                else:
                    st.error(f"Error from Tutor service: {resp.text}")
            except Exception as e:
                st.error(f"Failed to communicate with Tutor service: {e}")
        st.rerun()
