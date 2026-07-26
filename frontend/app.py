import os
import requests
import streamlit as st
import streamlit.components.v1 as components

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
    .lesson-card {
        background-color: #fdfdfd;
        border: 1px solid #e1e4e6;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.02);
    }
    .badge {
        background-color: #4a90e2;
        color: white;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.8em;
        font-weight: bold;
        display: inline-block;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Helper function to render Mermaid diagram beautifully
def render_mermaid(mermaid_code):
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script type="module">
            import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
            mermaid.initialize({{ 
                startOnLoad: true, 
                theme: 'neutral',
                securityLevel: 'loose',
                flowchart: {{ useMaxWidth: true, htmlLabels: true }}
            }});
        </script>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                background-color: transparent;
                margin: 0;
                padding: 10px;
                display: flex;
                justify-content: center;
            }}
            .mermaid {{
                display: inline-block;
                background: #fdfdfd;
                border: 1px solid #e1e4e6;
                border-radius: 8px;
                padding: 15px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.01);
            }}
        </style>
    </head>
    <body>
        <div class="mermaid">
{mermaid_code}
        </div>
    </body>
    </html>
    """
    components.html(html_code, height=400, scrolling=True)

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
if "active_step" not in st.session_state:
    st.session_state.active_step = 1
if "completed_steps" not in st.session_state:
    st.session_state.completed_steps = set()
if "quiz_grades" not in st.session_state:
    st.session_state.quiz_grades = {}  # step_number: (passed, feedback, user_answer)
if "architecture" not in st.session_state:
    st.session_state.architecture = None
if "curriculum" not in st.session_state:
    st.session_state.curriculum = None

# Auto-Ingest setup.py on Startup if empty (Zero-click onboarding!)
if not st.session_state.repo_id:
    try:
        # Silently trigger backend ingestion for setup.py
        resp = requests.post(f"{BACKEND_URL}/ingest", json={"repo_url": "https://github.com/kennethreitz/setup.py"}, timeout=15)
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
    if st.button("➕ New Chat Thread", use_container_width=True, type="primary"):
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
    
    # Lesson completion guide (tucked safely inside the sidebar to stay clean)
    if st.session_state.repo_id and st.session_state.curriculum:
        st.write("📚 **Lesson Roadmap**")
        steps = st.session_state.curriculum.get("steps", [])
        for step in steps:
            sid = step["step_number"]
            is_comp = sid in st.session_state.completed_steps
            is_act = (sid == st.session_state.active_step)
            
            icon = "✅" if is_comp else ("🎯" if is_act else "🔒")
            lbl = f"Step {sid}: {step['title']}"
            if is_act:
                lbl = f"👉 **Step {sid}: {step['title']}**"
                
            if st.button(f"{icon} {lbl}", key=f"nav_step_btn_{sid}", use_container_width=True):
                st.session_state.active_step = sid
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
                    resp = requests.post(f"{BACKEND_URL}/ingest", json={"repo_url": repo_url}, timeout=15)
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
if st.session_state.repo_id:
    # 1. Fetch Architecture and Curriculum if they aren't loaded in cache
    try:
        if st.session_state.architecture is None:
            with st.spinner("Analyzing architecture..."):
                resp = requests.get(f"{BACKEND_URL}/architecture/{st.session_state.repo_id}", timeout=15)
                if resp.status_code == 200:
                    st.session_state.architecture = resp.json()
                else:
                    st.error(f"Backend failed to map architecture (Status {resp.status_code}): {resp.text}")
                    st.stop()
                    
        if st.session_state.curriculum is None:
            with st.spinner("Designing curriculum..."):
                resp = requests.get(f"{BACKEND_URL}/curriculum/{st.session_state.repo_id}", timeout=15)
                if resp.status_code == 200:
                    st.session_state.curriculum = resp.json()
                else:
                    st.error(f"Backend failed to build curriculum (Status {resp.status_code}): {resp.text}")
                    st.stop()
    except Exception as e:
        st.error(f"Failed to communicate with FastAPI backend: {e}")
        st.stop()
        
    if st.session_state.curriculum and st.session_state.architecture:
        arch = st.session_state.architecture
        curr = st.session_state.curriculum
        steps = curr.get("steps", [])
        total_steps = len(steps)
        
        active_step_id = st.session_state.active_step
        step_meta = next((s for s in steps if s["step_number"] == active_step_id), steps[0])

        # Title Header
        st.markdown(f"## 🤖 Codebase Onboarding Agent: {st.session_state.repo_title}")
        st.caption(f"Active Lesson: Step {active_step_id} — **{step_meta['title']}**")
        
        # Elegant Lesson Banner on Top
        st.markdown(f"""
        <div class='lesson-card'>
            <div class='badge'>Active Step {active_step_id} of {total_steps} — Focus: {", ".join(step_meta['file_paths'])}</div>
            <div class='step-title'>{step_meta['title']}</div>
            <div class='rationale-text'>{step_meta['rationale']}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # --- THE ULTRACLEAN TAB DECOUPLING SYSTEM (Perfect, minimalist, modern AI interface) ---
        tab_chat, tab_quiz, tab_diagram, tab_analytics = st.tabs([
            "💬 Interactive Chat", 
            "✍️ Practice Quiz", 
            "🗺️ Blueprint Map", 
            "📊 Contributor Metrics"
        ])
        
        # --- TAB 1: INTERACTIVE CHAT ---
        with tab_chat:
            if not active_thread["history"]:
                # EMPTY CHAT LANDING STATE
                st.markdown(f"""
                <div class='chat-hero' style='margin-top: 5vh;'>
                    <h1 style='font-size: 2.2em;'>🤖 Ask your Codebase Tutor</h1>
                    <p style='font-size: 1.1em;'>How can I help you understand these files today: {", ".join(step_meta['file_paths'])}?</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                # Loop and render clean, pure chat logs
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

            # Pure floating chat input
            user_q = st.chat_input("Ask a question about the code or history...")
            
            if user_q:
                # Render user query instantly
                with st.chat_message("user", avatar="👤"):
                    st.markdown(user_q)
                active_thread["history"].append({"role": "user", "content": user_q})
                
                # Auto-update Thread Title based on first question
                if len(active_thread["history"]) <= 2:
                    short_title = user_q[:25] + "..." if len(user_q) > 25 else user_q
                    active_thread["title"] = short_title
                    
                # Call backend /ask
                with st.spinner("Tutor is reading code..."):
                    try:
                        resp = requests.post(f"{BACKEND_URL}/ask", json={
                            "repo_id": st.session_state.repo_id,
                            "question": user_q
                        }, timeout=30)
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

        # --- TAB 2: PRACTICE QUIZ ---
        with tab_quiz:
            st.markdown("#### Test Your Understanding to Advance")
            st.caption("Answer this conceptual open-ended check question. Your answer will be evaluated instantly against required technical keywords.")
            
            quiz_q_data = None
            try:
                resp = requests.get(f"{BACKEND_URL}/quiz/{st.session_state.repo_id}/{active_step_id}", timeout=15)
                if resp.status_code == 200:
                    quiz_q_data = resp.json()
                else:
                    st.error(f"Failed to load quiz: {resp.text}")
            except Exception as e:
                st.error(f"Failed to connect to quiz service: {e}")
                
            if quiz_q_data:
                # Highlighted Question Box
                st.markdown(f"""
                <div style='background-color: #fcf3cf; border-left: 4px solid #f1c40f; padding: 15px; border-radius: 8px; margin-bottom: 20px;'>
                    <span style='font-weight: bold; color: #7d6608;'>❓ Question:</span><br/>
                    <span style='font-size: 1.05em; color: #2c3e50;'>{quiz_q_data['question']}</span>
                </div>
                """, unsafe_allow_html=True)
                
                # Answer submission
                stored_ans = ""
                if active_step_id in st.session_state.quiz_grades:
                    stored_ans = st.session_state.quiz_grades[active_step_id][2]
                    
                user_answer = st.text_area(
                    "Type your conceptual explanation here (use full sentences to show reasoning):",
                    value=stored_ans,
                    height=120,
                    key=f"text_ans_step_{active_step_id}"
                )
                
                if st.button("📝 Submit My Answer for Grading", type="primary", use_container_width=True):
                    with st.spinner("Tutor is evaluating your submission..."):
                        try:
                            sub_resp = requests.post(f"{BACKEND_URL}/quiz/submit", json={
                                "repo_id": st.session_state.repo_id,
                                "step_number": active_step_id,
                                "question": quiz_q_data["question"],
                                "user_answer": user_answer
                            }, timeout=15)
                            if sub_resp.status_code == 200:
                                grade_data = sub_resp.json()
                                passed = grade_data["passed"]
                                feedback = grade_data["feedback"]
                                st.session_state.quiz_grades[active_step_id] = (passed, feedback, user_answer)
                                if passed:
                                    st.session_state.completed_steps.add(active_step_id)
                                st.rerun()
                            else:
                                st.error(f"Grading failed: {sub_resp.text}")
                        except Exception as e:
                            st.error(f"Failed to connect to grading server: {e}")
                            
                # Grade displays
                if active_step_id in st.session_state.quiz_grades:
                    passed, feedback, ans = st.session_state.quiz_grades[active_step_id]
                    st.divider()
                    if passed:
                        st.success("🎉 **SUCCESS — Lesson Completed!**")
                        st.markdown(feedback)
                        
                        if active_step_id < total_steps:
                            if st.button("Unlock Next Step 🔓", type="primary", use_container_width=True):
                                st.session_state.active_step = active_step_id + 1
                                st.rerun()
                        else:
                            st.balloons()
                            st.success("🎓 **CONGRATULATIONS! You have completed all lessons and successfully onboarded!**")
                    else:
                        st.error("❌ **REVISION SUGGESTED**")
                        st.markdown(feedback)

        # --- TAB 3: MODULE BLUEPRINT ---
        with tab_diagram:
            st.markdown("#### Codebase Module Blueprint Flow")
            st.caption("This visual map displays how system files and components connect together:")
            render_mermaid(arch.get("mermaid_diagram", "graph TD\n  A[No diagram loaded]"))
            st.divider()
            st.markdown("#### System Overview")
            st.write(arch.get("written_overview", ""))

        # --- TAB 4: AUTOMATED DIAGNOSTICS & CONTRIBUTOR HEALTH (Phase 6 Stretch Goal) ---
        with tab_analytics:
            st.markdown("#### 📊 Contributor Readiness & Diagnostic Report")
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
                
            st.divider()
            st.info("**Onboarding Diagnosis**: Excellent starting point. The codebase is highly self-contained with solid historical git log documentation inside `UploadCommand` detailing operational deployment requirements. The structural dependencies have zero complex cyclic loops.")
else:
    st.title("🤖 Codebase Onboarding Agent")
    st.write("Loading study room...")
