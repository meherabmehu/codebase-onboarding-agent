import os
import requests
import streamlit as st
import streamlit.components.v1 as components

# Configure page settings
st.set_page_config(
    page_title="Codebase Onboarding Tutor",
    page_icon="🤖",
    layout="centered", # Centered layout is elegant and focused
    initial_sidebar_state="expanded"
)

# Backend URL configuration (FastAPI server endpoint)
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

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
    components.html(html_code, height=380, scrolling=True)

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

# --- SIDEBAR: BACKEND CONNECT & REPO INGESTION ---
with st.sidebar:
    st.title("🤖 Codebase Tutor")
    st.write("An interactive onboarding agent communicating with a decoupled FastAPI backend.")
    st.divider()
    
    # 1. Backend URL setup
    st.markdown("### 🔌 API Service Configuration")
    backend_input = st.text_input("FastAPI Endpoint URL", value=BACKEND_URL)
    if backend_input != BACKEND_URL:
        BACKEND_URL = backend_input
        
    st.divider()
    
    # 2. Ingest repo
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
        
    if st.button("Ingest & Index Codebase", disabled=not repo_url):
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
                    st.success("🎉 Codebase loaded and cached successfully!")
                else:
                    st.error(f"Ingestion failed: {resp.text}")
            except Exception as e:
                st.error(f"Failed to connect to backend: {e}")
                
    st.divider()
    
    # 3. Progress tracker
    st.markdown("### 🏆 Learning Progress")
    if st.session_state.repo_id and st.session_state.curriculum:
        steps = st.session_state.curriculum.get("steps", [])
        total_steps = len(steps)
        completed = len(st.session_state.completed_steps)
        progress_pct = completed / total_steps if total_steps > 0 else 0.0
        
        st.progress(progress_pct, text=f"Progress: {completed} / {total_steps} Steps")
        
        for step in steps:
            step_num = step["step_number"]
            title = step["title"]
            is_comp = step_num in st.session_state.completed_steps
            icon = "✅" if is_comp else ("🎯" if step_num == st.session_state.active_step else "🔒")
            bold_start = "**" if step_num == st.session_state.active_step else ""
            bold_end = "**" if step_num == st.session_state.active_step else ""
            st.write(f"{icon} {bold_start}Step {step_num}: {title}{bold_end}")
    else:
        st.caption("Load a repository to track onboarding progress.")

# --- MAIN CONTENT CONTAINER ---
if st.session_state.repo_id:
    # 1. Fetch Architecture and Curriculum if they aren't loaded in cache
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
        
    # Double check payload validity
    if st.session_state.curriculum and st.session_state.architecture:
        arch = st.session_state.architecture
        curr = st.session_state.curriculum
        steps = curr.get("steps", [])
        total_steps = len(steps)
        
        # Header showing current active lesson
        st.title("🤖 Codebase Onboarding Agent")
        st.caption(f"Connected to FastAPI Service at `{BACKEND_URL}`")
        st.divider()
        
        active_step_id = st.session_state.active_step
        step_meta = next((s for s in steps if s["step_number"] == active_step_id), steps[0])
        
        # Active Step Banner
        st.markdown(f"### 🎯 Active Lesson: Step {active_step_id} of {total_steps} — **{step_meta['title']}**")
        st.info(f"**Description / Rationale**: {step_meta['rationale']}\n\n**Focus Files**: {', '.join(step_meta['file_paths'])}")
        
        # Tabs
        tab_chat, tab_quiz, tab_diagram, tab_path = st.tabs([
            "💬 Interactive Tutor Q&A", 
            "✍️ Knowledge Check Quiz", 
            "🗺️ Module Blueprint Diagram",
            "📚 Curriculum Timeline"
        ])
        
        # --- TAB 1: TUTOR CHAT ---
        with tab_chat:
            st.markdown("#### Ask Your Onboarding Tutor")
            st.write("Submit questions about the codebase structure, classes, or design history. The agent retrieves code chunks and cites actual git history.")
            
            # Suggestion quick question
            st.write("💡 *Suggested question for this step:*")
            cols = st.columns(2)
            suggested_q = ""
            
            if repo_option == "setup.py (Demo)":
                if cols[0].button("Why does this project use a custom UploadCommand?"):
                    suggested_q = "Why does this project have a custom UploadCommand instead of just using twine directly?"
                if cols[1].button("How does the versioning system work?"):
                    suggested_q = "Trace how versioning is parsed and managed in setup.py."
            else:
                if cols[0].button("Who is the main contributor to this step's files?"):
                    suggested_q = f"Which developer most recently updated these files: {', '.join(step_meta['file_paths'])}?"
                if cols[1].button("Give me a conceptual walk-through."):
                    suggested_q = f"Walk me through the design patterns used in this step's files: {', '.join(step_meta['file_paths'])}."
                    
            # Render chat history
            for msg in st.session_state.chat_history:
                with st.chat_message(msg["role"], avatar="🤖" if msg["role"] == "assistant" else "👤"):
                    st.markdown(msg["content"])
                    
            user_q = st.chat_input("Ask a question about the code design...")
            if suggested_q:
                user_q = suggested_q
                
            if user_q:
                # Render user message
                with st.chat_message("user", avatar="👤"):
                    st.markdown(user_q)
                st.session_state.chat_history.append({"role": "user", "content": user_q})
                
                # Make HTTP call to FastAPI backend /ask
                with st.spinner("Tutor is thinking..."):
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
                            grounded = data.get("grounded", False)
                            
                            # Render answer
                            with st.chat_message("assistant", avatar="🤖"):
                                st.markdown(answer)
                                if citations:
                                    st.markdown("---")
                                    st.markdown("**Citations & Sources:**")
                                    for idx, cite in enumerate(citations):
                                        ref_lbl = f"Ref: `{cite['ref']}`" if cite['ref'] else "Logical Inference"
                                        st.markdown(f"{idx+1}. **[{cite['type'].upper()}]** {ref_lbl} | *\"{cite['excerpt']}\"*")
                                        
                            st.session_state.chat_history.append({"role": "assistant", "content": answer})
                        else:
                            st.error(f"Error from Tutor service: {resp.text}")
                    except Exception as e:
                        st.error(f"Failed to communicate with Tutor service: {e}")
                st.rerun()

        # --- TAB 2: COMPREHENSION QUIZ ---
        with tab_quiz:
            st.markdown(f"#### Concept Check: Step {active_step_id}")
            
            # Fetch active step quiz question
            quiz_q_data = None
            try:
                resp = requests.get(f"{BACKEND_URL}/quiz/{st.session_state.repo_id}/{active_step_id}")
                if resp.status_code == 200:
                    quiz_q_data = resp.json()
                else:
                    st.error(f"Failed to load quiz from backend: {resp.text}")
            except Exception as e:
                st.error(f"Failed to connect to quiz service: {e}")
                
            if quiz_q_data:
                st.markdown(f"❓ **Question**: *{quiz_q_data['question']}*")
                
                # Answer box
                stored_ans = ""
                if active_step_id in st.session_state.quiz_grades:
                    stored_ans = st.session_state.quiz_grades[active_step_id][2]
                    
                user_answer = st.text_area(
                    "Write your technical explanation below:",
                    value=stored_ans,
                    height=120,
                    key=f"text_ans_step_{active_step_id}"
                )
                
                if st.button("Submit My Explanation", type="primary"):
                    with st.spinner("Tutor is evaluating your answer..."):
                        try:
                            # Submit to POST /quiz/submit
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
                            
                # Display results
                if active_step_id in st.session_state.quiz_grades:
                    passed, feedback, ans = st.session_state.quiz_grades[active_step_id]
                    st.divider()
                    if passed:
                        st.success("🎉 **PASS — Concept Mastered!**")
                        st.markdown(feedback)
                        
                        # Next lesson unlock
                        if active_step_id < total_steps:
                            if st.button("Unlock Next Step 🔓"):
                                st.session_state.active_step = active_step_id + 1
                                st.rerun()
                        else:
                            st.balloons()
                            st.success("🎓 **CONGRATULATIONS! You have completed all lessons and successfully onboarded!**")
                    else:
                        st.error("❌ **REVISION SUGGESTED**")
                        st.markdown(feedback)

        # --- TAB 3: DIAGRAM ---
        with tab_diagram:
            st.markdown("#### System Component Blueprint")
            st.write("This diagram displays the structural dependency tree of the repository. See how the different architectural layers connect together.")
            render_mermaid(arch.get("mermaid_diagram", "graph TD\n  A[No diagram loaded]"))
            st.divider()
            st.markdown("#### Written System Overview")
            st.write(arch.get("written_overview", ""))

        # --- TAB 4: CURRICULUM PATHWAY ---
        with tab_path:
            st.markdown("#### Onboarding Curriculum Roadmap")
            st.write("Here is the learning pathway sequenced for this repository. Click on any step to activate that lesson.")
            
            for step in steps:
                sid = step["step_number"]
                st_title = step["title"]
                st_desc = step["rationale"]
                
                is_comp = sid in st.session_state.completed_steps
                is_act = (sid == st.session_state.active_step)
                
                icon = "✅" if is_comp else ("🎯" if is_act else "🔒")
                
                st.markdown(f"##### {icon} **Step {sid}: {st_title}**")
                st.caption(f"Rationale: {st_desc}")
                st.caption(f"Concepts: {', '.join(step.get('concepts', []))}")
                if not is_act:
                    if st.button(f"Activate Lesson {sid}", key=f"btn_activate_step_path_{sid}"):
                        st.session_state.active_step = sid
                        st.rerun()
                st.divider()
else:
    # App Landing Page
    st.title("🤖 Codebase Onboarding Agent")
    st.caption("A clean, interactive tutor that teaches you repositories using their real historical commits.")
    
    st.info("👈 Please start the FastAPI backend on port 8000, then input your repository and click 'Ingest & Index Codebase' in the sidebar to begin!")
    
    # Beautiful visual features card
    st.markdown("""
    ### Key Features of this Onboarding Workspace:
    1. **💬 Interactive Q&A**: Ask "why" design decisions were made, and get answers grounded in real commit and PR metadata.
    2. **✍️ Knowledge Checks**: Answer open-ended comprehension check questions for each curriculum step, graded instantly by the agent.
    3. **🗺️ Component Blueprints**: View interactive module-level import diagrams showing how components relate.
    4. **📚 Structured Timelines**: Go step-by-step from base persistence and settings up to delivery endpoints.
    """)
