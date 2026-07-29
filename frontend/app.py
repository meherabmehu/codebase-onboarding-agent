import os
import json
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

# Local Thread Persistence (Matches ChatGPT/Claude persistent sidebar history!)
CHAT_HISTORY_FILE = "chat_history.json"

def load_threads():
    """Loads chat threads from local JSON file to survive browser refreshes."""
    if os.path.exists(CHAT_HISTORY_FILE):
        try:
            with open(CHAT_HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return [{
        "id": 0, 
        "title": "New Chat Session", 
        "history": [],
        "total_files": 0,
        "total_chunks": 0,
        "total_classes": 0,
        "total_functions": 0,
        "visited_files": [],
        "visited_chunks": [],
        "has_git_history": False,
        "has_pr_discussions": False
    }]

def save_threads():
    """Saves active chat threads to local JSON file."""
    try:
        with open(CHAT_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(st.session_state.threads, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

# Initialize Session State variables
if "repo_id" not in st.session_state:
    st.session_state.repo_id = ""
if "repo_title" not in st.session_state:
    st.session_state.repo_title = ""
if "active_thread_id" not in st.session_state:
    st.session_state.active_thread_id = 0
if "threads" not in st.session_state:
    st.session_state.threads = load_threads()
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

# Helper to get the active thread
def get_active_thread():
    for thread in st.session_state.threads:
        if thread["id"] == st.session_state.active_thread_id:
            return thread
    return st.session_state.threads[0]

active_thread = get_active_thread()

# Auto-Ingest setup.py on Startup if empty (Zero-click onboarding!)
if not st.session_state.repo_id:
    try:
        # Silently trigger backend ingestion for setup.py
        resp = requests.post(f"{BACKEND_URL}/ingest", json={"repo_url": "https://github.com/kennethreitz/setup.py"}, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            st.session_state.repo_id = data["repo_id"]
            st.session_state.repo_title = "setup.py (Demo)"
            
            # Baseline counts for startup thread
            if len(st.session_state.threads) > 0:
                first_thread = st.session_state.threads[0]
                if not first_thread.get("total_files"):
                    first_thread["total_files"] = data["total_files_count"]
                    first_thread["total_chunks"] = data["chunks_indexed"]
                    first_thread["total_classes"] = data["total_classes_count"]
                    first_thread["total_functions"] = data["total_functions_count"]
                    first_thread["visited_files"] = []
                    first_thread["visited_chunks"] = []
                    first_thread["has_git_history"] = False
                    first_thread["has_pr_discussions"] = False
                    save_threads()
    except Exception as e:
        # Handle connection failures gracefully
        st.error(f"Failed to auto-connect to backend at {BACKEND_URL}. Please verify uvicorn is running.")
        st.stop()

# --- SIDEBAR: CHAT SESSIONS & DEVELOPER OPTIONS ---
with st.sidebar:
    st.title("🤖 Codebase Tutor")
    st.caption("Active Repo: " + (st.session_state.repo_title or "setup.py"))
    st.divider()
    
    # NEW CHAT BUTTON (Standard ChatGPT behavior)
    if st.button("➕ New Chat Thread", use_container_width=True, type="primary"):
        new_id = len(st.session_state.threads)
        st.session_state.threads.insert(0, {
            "id": new_id, 
            "title": f"Chat Session {new_id + 1}", 
            "history": [],
            "total_files": 0,
            "total_chunks": 0,
            "total_classes": 0,
            "total_functions": 0,
            "visited_files": [],
            "visited_chunks": [],
            "has_git_history": False,
            "has_pr_discussions": False
        })
        st.session_state.active_thread_id = new_id
        save_threads()
        st.rerun()
        
    st.write("💬 **Recent Chats**")
    
    # List active chat threads in sidebar
    for thread in st.session_state.threads:
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
                        st.session_state.threads = [{
                            "id": 0, 
                            "title": "New Chat Session", 
                            "history": [],
                            "total_files": data["total_files_count"],
                            "total_chunks": data["chunks_indexed"],
                            "total_classes": data["total_classes_count"],
                            "total_functions": data["total_functions_count"],
                            "visited_files": [],
                            "visited_chunks": [],
                            "has_git_history": False,
                            "has_pr_discussions": False
                        }]
                        st.session_state.active_thread_id = 0
                        st.session_state.repo_title = repo_option if repo_option != "⚡ Link Custom GitHub Repo" else repo_url.split("github.com/")[-1]
                        save_threads()
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
                    
                    # Update thread metrics baseline if they were empty or uninitialized
                    if not active_thread.get("total_files"):
                        active_thread["total_files"] = st.session_state.architecture.get("total_files_count", 0)
                        active_thread["total_chunks"] = st.session_state.architecture.get("total_chunks_count", 0)
                        save_threads()
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

        # Title Header (Prisine minimalist header)
        st.markdown(f"## 🤖 Codebase Onboarding Agent: {st.session_state.repo_title}")
        st.caption("A clean, interactive assistant that teaches you the codebase entirely through natural conversation.")
        
        # --- THE ULTRACLEAN TAB DECOUPLING SYSTEM ---
        tab_chat, tab_quiz, tab_analytics = st.tabs([
            "💬 Interactive Chat", 
            "✍️ Practice Quiz", 
            "📊 Contributor Metrics"
        ])
        
        # --- TAB 1: INTERACTIVE CHAT ---
        with tab_chat:
            if not active_thread["history"]:
                # EMPTY CHAT LANDING STATE
                st.markdown(f"""
                <div class='chat-hero' style='margin-top: 5vh;'>
                    <h1 style='font-size: 2.2em;'>🤖 Ask your Codebase Tutor</h1>
                    <p style='font-size: 1.1em;'>How can I help you understand this repository today?</p>
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
                    
                save_threads()
                
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
                            ret_files = data.get("retrieved_files", []) or []
                            ret_chunks = data.get("retrieved_chunks", []) or []
                            
                            # Ensure clean metrics keys exist in the persistent thread
                            if "visited_files" not in active_thread:
                                active_thread["visited_files"] = []
                            if "visited_chunks" not in active_thread:
                                active_thread["visited_chunks"] = []
                            if "has_git_history" not in active_thread:
                                active_thread["has_git_history"] = False
                            if "has_pr_discussions" not in active_thread:
                                active_thread["has_pr_discussions"] = False
                                
                            # Update visited elements with DUPLICATE PROTECTION (Sets hashes under-the-hood)
                            for f in ret_files:
                                if f not in active_thread["visited_files"]:
                                    active_thread["visited_files"].append(f)
                            for c in ret_chunks:
                                if c not in active_thread["visited_chunks"]:
                                    active_thread["visited_chunks"].append(c)
                                    
                            # Parse citation properties
                            for cite in citations:
                                if cite["type"] == "commit":
                                    active_thread["has_git_history"] = True
                                if cite["type"] == "pr":
                                    active_thread["has_pr_discussions"] = True
                                    active_thread["has_git_history"] = True
                            
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
                            save_threads()
                        else:
                            st.error(f"Error from Tutor: {resp.text}")
                    except Exception as e:
                        st.error(f"Failed to communicate with Tutor service: {e}")
                st.rerun()

        # --- TAB 2: PRACTICE QUIZ ---
        with tab_quiz:
            st.markdown("#### Test Your Understanding to Advance")
            st.caption("Answer this conceptual open-ended check question. Your answer will be evaluated instantly against required technical keywords.")
            
            num_exchanges = len(active_thread["history"])
            
            # UX ONBOARDING FIX: If no conversation has started, show ONLY the friendly note and hide input boxes!
            if num_exchanges == 0:
                st.info("📝 **Comprehension Quiz Pending**\n\nTo start your lesson quiz, please go to the **'💬 Interactive Chat'** tab and start a conversation about the codebase! The tutor will dynamically analyze your conversation topic and generate a customized quiz question to test your knowledge.")
            else:
                quiz_q_data = None
                try:
                    # PERFORMANCE OPTIMIZATION: Post request with active thread history context to trigger ADAPTIVE quizzes based on active chat conversation topics!
                    resp = requests.post(f"{BACKEND_URL}/quiz", json={
                        "repo_id": st.session_state.repo_id,
                        "step_number": active_step_id,
                        "chat_history": active_thread["history"]
                    }, timeout=15)
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
                        <span style='font-weight: bold; color: #7d6608;'>❓ Question (Based on your Chat Topics):</span><br/>
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
                            st.error("❌ **REVISION SUGGESTED**")
                            st.markdown(feedback)

        # --- TAB 3: DYNAMIC REAL-TIME PROGRESS & DIAGNOSTIC METRICS (COMPREHENSIVELY REFACETORED FROM SCRATCH!) ---
        with tab_analytics:
            st.markdown("#### 📊 Dynamic Repository Metrics & Diagnostic Report")
            st.write("These metrics track codebase properties and update in real-time based on your actual active discussion depth!")
            
            num_exchanges = len(active_thread["history"])
            
            # Retrieve the LOCKED baseline counts from current thread state
            total_files = active_thread.get("total_files", 0) or arch.get("total_files_count", 1) or 1
            total_chunks = active_thread.get("total_chunks", 0) or arch.get("total_chunks_count", 1) or 1
            
            # Fetch visited lists (duplicate protected via list-membership checks during appending)
            visited_files_list = active_thread.get("visited_files", [])
            visited_files_count = len(visited_files_list)
            
            has_git = active_thread.get("has_git_history", False)
            has_pr = active_thread.get("has_pr_discussions", False)
            
            # Sourced project owner (100% dynamically resolved)
            dynamic_owner = arch.get("project_owner", "Unknown")
            
            # 1. REVISION STATE: Check if conversation has actually started
            if num_exchanges == 0:
                dynamic_coverage = "0%"
                dynamic_files_explored = f"0 / {total_files}"
                dynamic_context_tier = "Low"
                diagnosis_msg = "Please type and send your first message in the '💬 Interactive Chat' tab to initiate real-time diagnostics."
                
                coverage_pct = 0.0
            else:
                # Calculate Repository Coverage based on absolute baseline totals (never retrieved elements!)
                coverage_pct = (visited_files_count / total_files) * 100
                if coverage_pct == 0:
                    dynamic_coverage = "0%"
                elif coverage_pct < 1:
                    dynamic_coverage = f"{coverage_pct:.2f}%"
                else:
                    dynamic_coverage = f"{coverage_pct:.1f}%"
                
                # Files Explored based on absolute baseline totals
                dynamic_files_explored = f"{visited_files_count} / {total_files}"
                
                # Historical Context levels mapped strictly to context richness
                if visited_files_count == 0:
                    dynamic_context_tier = "Low"
                elif visited_files_count == 1 and not has_git:
                    dynamic_context_tier = "Low"
                elif visited_files_count > 1 and not has_git:
                    dynamic_context_tier = "Medium"
                elif has_git and not has_pr:
                    dynamic_context_tier = "High"
                else:
                    dynamic_context_tier = "Comprehensive"
                    
                diagnosis_msg = f"Onboarding Diagnostics: Sourced repository owner is {dynamic_owner}. As you retrieve more codebase files or git logs in the chat, Repository Coverage and Historical Context will dynamically shift real-time!"
                
            # 2. DEBUG REQUIREMENT: Output precise states to backend console for verification
            print("======================================================", flush=True)
            print("📊 METRICS DEBUG REPORT (STREAMLIT CONSOLE)", flush=True)
            print(f"Total Indexed Files: {total_files}", flush=True)
            print(f"Visited Files: {visited_files_list}", flush=True)
            print(f"Coverage Formula: {visited_files_count} / {total_files}", flush=True)
            print(f"Coverage Result: {coverage_pct:.2f}%", flush=True)
            print("======================================================", flush=True)
                
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            with col_m1:
                st.markdown(f"""
                <div class='metric-card'>
                    <span style='font-size: 0.8em; color: #64748b;'>REPO COVERAGE</span><br/>
                    <span style='font-size: 1.8em; font-weight: bold; color: #27ae60;'>{dynamic_coverage}</span>
                </div>
                """, unsafe_allow_html=True)
            with col_m2:
                st.markdown(f"""
                <div class='metric-card'>
                    <span style='font-size: 0.8em; color: #64748b;'>FILES EXPLORED</span><br/>
                    <span style='font-size: 1.8em; font-weight: bold; color: #1e3a8a;'>{dynamic_files_explored}</span>
                </div>
                """, unsafe_allow_html=True)
            with col_m3:
                st.markdown(f"""
                <div class='metric-card'>
                    <span style='font-size: 0.8em; color: #64748b;'>HISTORICAL CONTEXT</span><br/>
                    <span style='font-size: 1.4em; font-weight: bold; color: #2980b9; margin-top: 5px; display: inline-block;'>{dynamic_context_tier}</span>
                </div>
                """, unsafe_allow_html=True)
            with col_m4:
                st.markdown(f"""
                <div class='metric-card'>
                    <span style='font-size: 0.8em; color: #64748b;'>PROJECT OWNER</span><br/>
                    <span style='font-size: 1.1em; font-weight: bold; color: #e67e22; margin-top: 8px; display: inline-block;'>{dynamic_owner}</span>
                </div>
                """, unsafe_allow_html=True)
                
            st.divider()
            st.info(f"💡 **Diagnosis**: {diagnosis_msg}")
else:
    st.title("🤖 Codebase Onboarding Agent")
    st.write("Loading study room...")
