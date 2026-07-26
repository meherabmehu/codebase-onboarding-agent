import os
import requests
import streamlit as st
import streamlit.components.v1 as components

# Configure page settings
st.set_page_config(
    page_title="Codebase Onboarding Tutor",
    page_icon="🤖",
    layout="wide", # Let's use wide layout so we can put learning maps and workspace side-by-side!
    initial_sidebar_state="expanded"
)

# Backend URL configuration
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# Inject premium custom CSS to style Streamlit into a clean, modern SaaS training academy
st.markdown("""
<style>
    /* Styling the Main Lesson Cards */
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
    .step-title {
        font-size: 1.4em;
        font-weight: bold;
        color: #2c3e50;
        margin-top: 5px;
        margin-bottom: 10px;
    }
    .rationale-text {
        font-size: 0.95em;
        color: #5d6d7e;
        line-height: 1.5;
        margin-bottom: 15px;
    }
    .step-list-item {
        background-color: #f8f9f9;
        border-left: 4px solid #4a90e2;
        padding: 8px 12px;
        margin: 5px 0;
        border-radius: 4px;
        font-size: 0.9em;
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
if "active_step" not in st.session_state:
    st.session_state.active_step = 1
if "completed_steps" not in st.session_state:
    st.session_state.completed_steps = set()
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "quiz_grades" not in st.session_state:
    st.session_state.quiz_grades = {}  # step_number: (passed, feedback, user_answer)
if "architecture" not in st.session_state:
    st.session_state.architecture = None
if "curriculum" not in st.session_state:
    st.session_state.curriculum = None

# --- SIDEBAR: API SETTINGS & CODEBASE TRIGGER ---
with st.sidebar:
    st.title("🤖 Codebase Tutor")
    st.write("Your interactive AI onboarding assistant.")
    st.divider()
    
    # 1. Backend URL setup
    st.markdown("### 🔌 Connection Configurations")
    backend_input = st.text_input("FastAPI Endpoint URL", value=BACKEND_URL)
    if backend_input != BACKEND_URL:
        BACKEND_URL = backend_input
        
    st.divider()
    
    # 2. Ingest repo
    st.markdown("### 📁 Select Repository")
    repo_option = st.selectbox(
        "Choose Codebase to Ingest",
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
        
    st.write("👇 *Click the button below to load this codebase:*")
    if st.button("🚀 Ingest & Index Codebase", disabled=not repo_url, type="primary", use_container_width=True):
        with st.spinner("⚡ Connecting to FastAPI backend to clone, parse, and index..."):
            try:
                # Call POST /ingest
                resp = requests.post(f"{BACKEND_URL}/ingest", json={"repo_url": repo_url})
                if resp.status_code == 200:
                    data = resp.json()
                    st.session_state.repo_id = data["repo_id"]
                    st.session_state.active_step = 1
                    st.session_state.completed_steps = set()
                    st.session_state.chat_history = []
                    st.session_state.quiz_grades.clear()
                    st.session_state.architecture = None
                    st.session_state.curriculum = None
                    st.success("🎉 Codebase loaded and active!")
                else:
                    st.error(f"Ingestion failed: {resp.text}")
            except Exception as e:
                st.error(f"Failed to connect to backend: {e}")
                
    st.divider()
    
    # 3. Quick Navigation timeline
    if st.session_state.repo_id and st.session_state.curriculum:
        st.markdown("### 🗺️ Curriculum Guide")
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

# --- MAIN CONTENT CONTROLLER ---
if not st.session_state.repo_id:
    # LANDING PAGE (Onboarding state: No repo loaded yet)
    st.markdown("<h1 style='text-align: center; color: #2c3e50;'>🚀 Welcome to your Codebase Tutor!</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; font-size: 1.1em; color: #7f8c8d; margin-bottom: 40px;'>An interactive onboarding cockpit that teaches you software repositories step-by-step.</p>", unsafe_allow_html=True)
    
    # Large 3-Step Guided Instruction Board
    st.markdown("### 👈 Let's get started in 2 simple clicks:")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class='lesson-card' style='height: 240px;'>
            <div class='badge' style='background-color: #e67e22;'>Step 1</div>
            <h4 style='color: #2c3e50;'>Select Codebase</h4>
            <p style='font-size: 0.9em; color: #5d6d7e;'>Look at the left sidebar. Make sure the dropdown is set to <b>setup.py (Demo)</b> (or paste your own repo!).</p>
        </div>
        """, unsafe_allow_html=True)
        
    with col2:
        st.markdown("""
        <div class='lesson-card' style='height: 240px;'>
            <div class='badge' style='background-color: #27ae60;'>Step 2</div>
            <h4 style='color: #2c3e50;'>Click Ingest</h4>
            <p style='font-size: 0.9em; color: #5d6d7e;'>Click the orange <b>🚀 Ingest & Index Codebase</b> button in the sidebar to download and index your files.</p>
        </div>
        """, unsafe_allow_html=True)
        
    with col3:
        st.markdown("""
        <div class='lesson-card' style='height: 240px;'>
            <div class='badge' style='background-color: #2980b9;'>Step 3</div>
            <h4 style='color: #2c3e50;'>Start Learning!</h4>
            <p style='font-size: 0.9em; color: #5d6d7e;'>Your screen will instantly transform into an interactive study dashboard complete with chatbots, diagrams, and quizzes!</p>
        </div>
        """, unsafe_allow_html=True)
        
    # Features highlights below
    st.divider()
    st.markdown("### 💡 What this workspace does:")
    f_col1, f_col2 = st.columns(2)
    with f_col1:
        st.markdown("🗣️ **Interactive Chat Q&A**: Ask the Tutor any 'why was this built this way' questions. It searches files and cites real git commit authors and dates.")
        st.markdown("🗺️ **Component Blueprint**: View an interactive, visual flowchart showing how modules import and depend on each other.")
    with f_col2:
        st.markdown("📚 **Curriculum Timeline**: Follow a sequential path going from configuration Bedrocks up to core operational controllers.")
        st.markdown("✍️ **Comprehension Quizzes**: Take open-ended quizzes at each step. Your answers are graded instantly to track and verify your progress.")

else:
    # STUDY ROOM (State: Codebase active!)
    try:
        if st.session_state.architecture is None:
            with st.spinner("Analyzing architecture..."):
                resp = requests.get(f"{BACKEND_URL}/architecture/{st.session_state.repo_id}")
                if resp.status_code == 200:
                    st.session_state.architecture = resp.json()
                    
        if st.session_state.curriculum is None:
            with st.spinner("Designing curriculum..."):
                resp = requests.get(f"{BACKEND_URL}/curriculum/{st.session_state.repo_id}")
                if resp.status_code == 200:
                    st.session_state.curriculum = resp.json()
    except Exception as e:
        st.error(f"Error communicating with FastAPI backend: {e}")
        st.stop()
        
    if st.session_state.curriculum and st.session_state.architecture:
        arch = st.session_state.architecture
        curr = st.session_state.curriculum
        steps = curr.get("steps", [])
        total_steps = len(steps)
        
        active_step_id = st.session_state.active_step
        step_meta = next((s for s in steps if s["step_number"] == active_step_id), steps[0])
        
        # Header
        repo_title = repo_option if repo_option != "⚡ Link Custom GitHub Repo" else repo_url.split("github.com/")[-1]
        st.markdown(f"<h2 style='color: #2c3e50; margin-bottom: 5px;'>📖 Active Study Room: {repo_title}</h2>", unsafe_allow_html=True)
        st.caption(f"Connected to FastAPI Service at `{BACKEND_URL}`")
        
        # --- PREMIER 2-COLUMN SPLIT SIDE-BY-SIDE STUDY INTERFACE ---
        col_left, col_right = st.columns([1.1, 1.3])
        
        # =========================================================================
        # LEFT COLUMN: CURRICULUM, INSTRUCTIONS & MODULE DIAGRAM (Passive Context)
        # =========================================================================
        with col_left:
            # Lesson Detail Card
            st.markdown(f"""
            <div class='lesson-card'>
                <div class='badge'>Lesson Step {active_step_id} of {total_steps}</div>
                <div class='step-title'>{step_meta['title']}</div>
                <div class='rationale-text'><b>Goal</b>: {step_meta['rationale']}</div>
                <div style='font-size: 0.9em; font-weight: bold; color: #2c3e50; margin-bottom: 5px;'>📁 Target files to understand:</div>
                {" ".join([f"<span class='step-list-item'>{f}</span>" for f in step_meta['file_paths']])}
            </div>
            """, unsafe_allow_html=True)
            
            # Module blueprint map
            with st.expander("🗺️ View Codebase Module Blueprint Flow", expanded=True):
                st.caption("This visual map displays how system files and components connect together:")
                render_mermaid(arch.get("mermaid_diagram", "graph TD\n  A[No diagram loaded]"))
                
            # Full Curriculum Timeline Card
            with st.expander("📚 Your Full Curriculum Pathway"):
                st.write("Follow this timeline to fully onboard to this repository:")
                for step in steps:
                    sid = step["step_number"]
                    is_comp = sid in st.session_state.completed_steps
                    is_act = (sid == active_step_id)
                    icon = "✅" if is_comp else ("🎯" if is_act else "🔒")
                    bold = "**" if is_act else ""
                    st.write(f"{icon} {bold}Step {sid}: {step['title']}{bold}")
                    st.caption(step["rationale"])
                    
        # =========================================================================
        # RIGHT COLUMN: TUTOR CONVERSATION & PRACTICE QUIZ (Interactive Workspace)
        # =========================================================================
        with col_right:
            # Main Tab Controller
            tab_chat, tab_quiz = st.tabs(["💬 Chat with your AI Tutor", "✍️ Complete Lesson Quiz"])
            
            # --- TAB 1: TUTOR CHAT ---
            with tab_chat:
                st.markdown("#### Talk to your Onboarding Tutor")
                st.caption("Ask questions about why methods were built, who authored them, or how the configuration operates.")
                
                # Big Welcoming Call To Action Box (so they know what to ask)
                st.markdown("""
                <div style='background-color: #ebf5fb; border-left: 4px solid #3498db; padding: 12px 15px; border-radius: 4px; margin-bottom: 15px;'>
                    <b>🎓 Tutor Tip</b>: Click one of the suggested buttons below to instantly ask me an architectural 'why' question about this lesson's files!
                </div>
                """, unsafe_allow_html=True)
                
                # suggested question triggers
                st.write("👉 *Click a suggested question to run it instantly:*")
                cols = st.columns(2)
                suggested_q = ""
                
                if repo_option == "setup.py (Demo)":
                    if active_step_id == 1:
                        if cols[0].button("📝 What metadata is defined in setup.py?", use_container_width=True):
                            suggested_q = "What standard package metadata parameters (name, version, license) are declared in setup.py?"
                        if cols[1].button("📁 Where are classifiers specified?", use_container_width=True):
                            suggested_q = "How are packaging classifier categories specified in setup.py, and what is their role?"
                    elif active_step_id == 2:
                        if cols[0].button("🛠️ What base class does UploadCommand use?", use_container_width=True):
                            suggested_q = "Which class does UploadCommand subclass, and what interface operations does it define?"
                        if cols[1].button("❓ Why override command configurations?", use_container_width=True):
                            suggested_q = "Why does setup.py subclass custom commands instead of executing scripts directly?"
                    elif active_step_id == 3:
                        if cols[0].button("🚀 Why use custom UploadCommand?", use_container_width=True):
                            suggested_q = "Why does this project have a custom UploadCommand instead of just using twine directly?"
                        if cols[1].button("📦 How are artifacts built?", use_container_width=True):
                            suggested_q = "Trace how the custom UploadCommand executes subprocess calls to build and compile source distributions."
                else:
                    if cols[0].button("👩‍💻 Who is the main contributor to this step?", use_container_width=True):
                        suggested_q = f"Which developer most recently updated these files: {', '.join(step_meta['file_paths'])}?"
                    if cols[1].button("💡 Give me a conceptual walk-through.", use_container_width=True):
                        suggested_q = f"Walk me through the design patterns used in this step's files: {', '.join(step_meta['file_paths'])}."
                        
                st.divider()
                
                # Chat History Box
                if not st.session_state.chat_history:
                    # If empty history, show a friendly greetings
                    with st.chat_message("assistant", avatar="🤖"):
                        st.markdown(f"Hello! I am your Onboarding Tutor. I have indexed the files for **Step {active_step_id}: {step_meta['title']}**. Click one of the suggested questions above, or type any custom query below to learn why this code was built this way!")
                else:
                    for msg in st.session_state.chat_history:
                        with st.chat_message(msg["role"], avatar="🤖" if msg["role"] == "assistant" else "👤"):
                            st.markdown(msg["content"])
                            
                # Query input
                user_q = st.chat_input("Ask me anything about these files (e.g. 'Why was this written this way?')")
                if suggested_q:
                    user_q = suggested_q
                    
                if user_q:
                    # Render user message
                    with st.chat_message("user", avatar="👤"):
                        st.markdown(user_q)
                    st.session_state.chat_history.append({"role": "user", "content": user_q})
                    
                    # Call API
                    with st.spinner("Tutor is reading code and git logs..."):
                        try:
                            resp = requests.post(f"{BACKEND_URL}/ask", json={
                                "repo_id": st.session_state.repo_id,
                                "question": user_q,
                                "step_number": active_step_id
                            })
                            if resp.status_code == 200:
                                data = resp.json()
                                answer = data["answer"]
                                citations = data.get("citations", [])
                                
                                with st.chat_message("assistant", avatar="🤖"):
                                    st.markdown(answer)
                                    if citations:
                                        st.markdown("---")
                                        st.markdown("**Citations & Sources retrieved:**")
                                        for idx, cite in enumerate(citations):
                                            ref_lbl = f"Ref: `{cite['ref']}`" if cite['ref'] else "Logical Inference"
                                            st.markdown(f"{idx+1}. **[{cite['type'].upper()}]** {ref_lbl} | *\"{cite['excerpt']}\"*")
                                            
                                st.session_state.chat_history.append({"role": "assistant", "content": answer})
                            else:
                                st.error(f"Error from Tutor service: {resp.text}")
                        except Exception as e:
                            st.error(f"Failed to communicate with Tutor service: {e}")
                    st.rerun()

            # --- TAB 2: PRACTICE QUIZ ---
            with tab_quiz:
                st.markdown("#### Test Your Understanding to Advance")
                st.caption("Answer this conceptual open-ended check question. Your answer will be evaluated instantly against required technical keywords.")
                
                quiz_q_data = None
                try:
                    resp = requests.get(f"{BACKEND_URL}/quiz/{st.session_state.repo_id}/{active_step_id}")
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
                                })
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
                            st.info("💡 **Study Tip**: Try asking the Tutor in the first tab for details about this topic to refine your explanation!")
    else:
        st.title("🤖 Codebase Onboarding Agent")
        st.write("Loading study room...")
