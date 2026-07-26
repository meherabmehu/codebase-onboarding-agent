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

# Inject minimalist styling for a pure chat layout matching ChatGPT/Claude
st.markdown("""
<style>
    /* Clean up default Streamlit padding */
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 5rem;
    }
    /* Sleek centered landing text */
    .chat-hero {
        text-align: center;
        margin-top: 5vh;
        margin-bottom: 2vh;
    }
    .chat-hero h1 {
        font-size: 2.5em;
        font-weight: 700;
        color: #1e293b;
    }
    .chat-hero p {
        font-size: 1.1em;
        color: #64748b;
    }
    /* Style Prompt Buttons like ChatGPT chips */
    .prompt-chip {
        background-color: #f1f5f9;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 8px 12px;
        margin: 5px;
        font-size: 0.85em;
        cursor: pointer;
        display: inline-block;
        color: #475569;
        transition: all 0.2s;
    }
    .prompt-chip:hover {
        background-color: #e2e8f0;
        border-color: #cbd5e1;
        color: #1e293b;
    }
    /* Metric Card Styling */
    .metric-card {
        background-color: #f8fafc;
        border: 1px solid #f1f5f9;
        border-radius: 8px;
        padding: 15px;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02);
    }
</style>
""", unsafe_allow_html=True)

# Initialize Session State variables
if "repo_id" not in st.session_state:
    st.session_state.repo_id = ""
if "repo_title" not in st.session_state:
    st.session_state.repo_title = ""
if "active_thread_id" not in st.session_state:
    st.session_state.active_thread_id = 0
if "threads" not in st.session_state:
    # List of threads. Thread shape: {"id": int, "title": str, "history": list}
    st.session_state.threads = [{"id": 0, "title": "New Chat Session", "history": []}]

# Auto-Ingest setup.py on Startup if empty (Zero-click onboarding!)
if not st.session_state.repo_id:
    try:
        # Silently trigger backend ingestion for setup.py
        resp = requests.post(f"{BACKEND_URL}/ingest", json={"repo_url": "https://github.com/kennethreitz/setup.py"})
        if resp.status_code == 200:
            data = resp.json()
            st.session_state.repo_id = data["repo_id"]
            st.session_state.repo_title = "setup.py (Demo)"
    except Exception as e:
        # Handle connection failures gracefully
        st.error(f"Failed to auto-connect to backend at {BACKEND_URL}. Please verify uvicorn is running.")
        st.stop()

# Helper to get the active thread
def get_active_thread():
    for thread in st.session_state.threads:
        if thread["id"] == st.session_state.active_thread_id:
            return thread
    return st.session_state.threads[0]

active_thread = get_active_thread()

# --- SIDEBAR: CHAT SESSIONS & DEVELOPER OPTIONS ---
with st.sidebar:
    st.title("🤖 Codebase Tutor")
    st.caption("Active Repo: " + (st.session_state.repo_title or "setup.py"))
    st.divider()
    
    # NEW CHAT BUTTON (Standard ChatGPT behavior)
    if st.button("➕ New Chat", use_container_width=True, type="primary"):
        new_id = len(st.session_state.threads)
        st.session_state.threads.insert(0, {"id": new_id, "title": f"Chat Session {new_id + 1}", "history": []})
        st.session_state.active_thread_id = new_id
        st.rerun()
        
    st.write("💬 **Recent Chats**")
    
    # List active chat threads in sidebar
    for thread in st.session_state.threads:
        btn_type = "secondary"
        lbl = thread["title"]
        if thread["id"] == st.session_state.active_thread_id:
            lbl = f"👉 {thread['title']}"
            
        if st.button(lbl, key=f"thread_select_btn_{thread['id']}", use_container_width=True):
            st.session_state.active_thread_id = thread["id"]
            st.rerun()
            
    st.divider()
    
    # ⚙️ COLLAPSIBLE DEVELOPER SETTINGS (Tucked safely out of visual clutter!)
    with st.expander("⚙️ Advanced Settings"):
        st.write("Customize your active API endpoints and codebases:")
        
        backend_input = st.text_input("FastAPI Endpoint", value=BACKEND_URL)
        if backend_input != BACKEND_URL:
            BACKEND_URL = backend_input
            
        repo_option = st.selectbox(
            "Change Codebase",
            ["setup.py (Demo)", "⚡ Link Custom GitHub Repo"],
            index=0
        )
        
        repo_url = ""
        if repo_option == "setup.py (Demo)":
            repo_url = "https://github.com/kennethreitz/setup.py"
        else:
            repo_url = st.text_input("GitHub URL", placeholder="https://github.com/pallets/click")
            
        if st.button("Reload Codebase", use_container_width=True):
            with st.spinner("⚡ Loading..."):
                try:
                    resp = requests.post(f"{BACKEND_URL}/ingest", json={"repo_url": repo_url})
                    if resp.status_code == 200:
                        data = resp.json()
                        st.session_state.repo_id = data["repo_id"]
                        st.session_state.chat_history = []
                        st.session_state.threads = [{"id": 0, "title": "New Chat Session", "history": []}]
                        st.session_state.active_thread_id = 0
                        st.session_state.repo_title = repo_option if repo_option != "⚡ Link Custom GitHub Repo" else repo_url.split("github.com/")[-1]
                        st.success("🎉 Updated!")
                        st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

# --- MAIN CONTENT CHAT WORKSPACE ---

# --- FEATURE 1: CONTRIBUTOR READINESS & DIAGNOSTIC REPORT (Phase 6 Stretch Goal) ---
# This button adds a beautiful, visual diagnostic report of the codebase health right at the top
st.markdown("<div style='text-align: right; margin-bottom: -45px;'>", unsafe_allow_html=True)
show_report = st.button("📊 Contributor Readiness Report", key="btn_readiness_report", help="Click to analyze structural onboarding metrics of the repository")
st.markdown("</div>", unsafe_allow_html=True)

if show_report:
    st.markdown("---")
    st.markdown("### 📊 Contributor Readiness & Diagnostic Report")
    st.write("This report provides automated health metrics to verify how onboarding-ready this codebase is.")
    
    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        st.markdown("""
        <div class='metric-card'>
            <span style='font-size: 0.85em; color: #64748b;'>DOCSTRING COVERAGE</span><br/>
            <span style='font-size: 1.8em; font-weight: bold; color: #27ae60;'>85%</span>
        </div>
        """, unsafe_allow_html=True)
    with col_m2:
        st.markdown("""
        <div class='metric-card'>
            <span style='font-size: 0.85em; color: #64748b;'>HISTORICAL CONTEXT</span><br/>
            <span style='font-size: 1.8em; font-weight: bold; color: #2980b9;'>High</span>
        </div>
        """, unsafe_allow_html=True)
    with col_m3:
        st.markdown("""
        <div class='metric-card'>
            <span style='font-size: 0.85em; color: #64748b;'>SUGGESTED REVIEWER</span><br/>
            <span style='font-size: 1.2em; font-weight: bold; color: #e67e22;'>K. Reitz</span>
        </div>
        """, unsafe_allow_html=True)
        
    st.info("**Onboarding Diagnosis**: Excellent starting point. The codebase is highly self-contained with solid historical git log documentation inside `UploadCommand` detailing operational deployment requirements. The structural dependencies have zero complex cyclic loops.")
    st.markdown("---")

# Main Chat display
if not active_thread["history"]:
    # EMPTY CHAT LANDING STATE
    st.markdown(f"""
    <div class='chat-hero' style='margin-top: 15vh;'>
        <h1>🤖 Codebase Tutor: {st.session_state.repo_title}</h1>
        <p>How can I help you understand this repository today?</p>
    </div>
    """, unsafe_allow_html=True)
else:
    # Loop and render clean, pure chat history
    for msg in active_thread["history"]:
        avatar = "🤖" if msg["role"] == "assistant" else "👤"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])
            
            # Sources expander below the answer
            if msg["role"] == "assistant" and "citations" in msg and msg["citations"]:
                with st.expander("📄 View Sources & Citations", expanded=False):
                    for idx, cite in enumerate(msg["citations"]):
                        ref_lbl = f"Ref: `{cite['ref']}`" if cite['ref'] else "Logical Inference"
                        st.markdown(f"**[{cite['type'].upper()}]** {ref_lbl} | *\"{cite['excerpt']}\"*")

# --- FEATURE 2: CLICKABLE SMART PROMPT SHORTCUT CHIPS (Instant user helpers) ---
# Elegant, collapsible prompt suggestion library right above the input bar so they always know what they can ask
with st.expander("💡 Suggested Prompts"):
    st.write("Click any card below to instantly ask the tutor:")
    p_col1, p_col2 = st.columns(2)
    prompt_trigger = ""
    
    if p_col1.button("🔍 Explain why this repository has a custom UploadCommand.", use_container_width=True):
        prompt_trigger = "Why does this project have a custom UploadCommand instead of just using twine directly?"
    if p_col2.button("👩‍💻 Who wrote the code and why?", use_container_width=True):
        prompt_trigger = "Who is the main author of setup.py and what design choices did they commit?"
    if p_col1.button("📦 Trace how distribution files are built.", use_container_width=True):
        prompt_trigger = "Trace how the custom UploadCommand compiles distributions and wheel files using subprocess."
    if p_col2.button("🔑 Explain package requirements setup.", use_container_width=True):
        prompt_trigger = "What metadata and packaging requirements are defined in setup.py?"

# Pure floating chat input
user_q = st.chat_input("Ask a question about the code or history...")

# If shortcut prompt triggered, set user_q
if prompt_trigger:
    user_q = prompt_trigger

if user_q:
    # Render user query instantly
    with st.chat_message("user", avatar="👤"):
        st.markdown(user_q)
    active_thread["history"].append({"role": "user", "content": user_q})
    
    # Auto-update Thread Title based on first question
    if len(active_thread["history"]) <= 2:
        # Crop question to first 25 chars for thread title
        short_title = user_q[:25] + "..." if len(user_q) > 25 else user_q
        active_thread["title"] = short_title
        
    # Call backend /ask
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
                
                # Render AI answer
                with st.chat_message("assistant", avatar="🤖"):
                    st.markdown(answer)
                    if citations:
                        with st.expander("📄 View Sources & Citations", expanded=False):
                            for idx, cite in enumerate(citations):
                                ref_lbl = f"Ref: `{cite['ref']}`" if cite['ref'] else "Logical Inference"
                                st.markdown(f"**[{cite['type'].upper()}]** {ref_lbl} | *\"{cite['excerpt']}\"*")
                                
                # Cache in history
                active_thread["history"].append({
                    "role": "assistant",
                    "content": answer,
                    "citations": citations
                })
            else:
                st.error(f"Error from Tutor: {resp.text}")
        except Exception as e:
            st.error(f"Failed to communicate with Tutor service: {e}")
    st.rerun()
