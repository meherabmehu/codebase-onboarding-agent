# 🤖 Codebase Onboarding Agent (Full-Stack Decoupled MVP)

An expert, interactive, RAG-powered tutor that teaches developers any GitHub repository through its actual evolution history—not just its current code state.

This repository features a **fully decoupled, industry-grade architecture**:
1.  **🚀 Backend (FastAPI)**: Serves high-speed API endpoints for cloning, parsing, semantic indexing, agent orchestration (Architecture Mapper, Curriculum Planner, Tutor Q&A, and Quiz grading).
2.  **💻 Frontend (Streamlit)**: A clean, task-oriented cockpit tab layout that communicates entirely with the backend endpoints via HTTP requests.

---

## 🛠️ Outstanding Project Enhancements Completed

We have optimized and completed the codebase with two crucial production upgrades:

### 1. 📂 Zero-Crash Native Fallback Parser (`backend/app/ingestor/parser.py`)
To bypass C/C++ compilation constraints and `tree-sitter-languages` environment limitations on newer systems (like **Python 3.13+**), we implemented an **elite hybrid fallback engine**:
*   **AST Analysis**: Uses standard library `ast` parsing to map python files, finding class bounds, method signatures, parameters, and decorators.
*   **Regex Fallback**: Uses optimized lexical scanning for Javascript, TypeScript, Go, Java, and other popular files.
*   *If `tree-sitter-languages` is not available, the system falls back gracefully to local AST/Regex parsing, ensuring 100% up-time on all operating systems and Python environments!*

### 2. 🎯 Dynamic Quiz Grading Cache (`backend/app/main.py`)
Previously, quiz submissions were graded against empty expected points. We have engineered a high-fidelity state cache:
*   During `/quiz` generation, the LLM-selected **`expected_points`** are preserved in the active repo state inside our cache.
*   Upon `/quiz/submit`, the **Quiz Grading Agent** retrieves these precise points to grade the student's open-ended answers with pinpoint, conceptual accuracy!

---

## 🚀 How to Run the App (Full-Stack)

Follow these step-by-step instructions to boot the complete workspace:

### 1. Setup Environment & Credentials
Create a `.env` file inside the `backend/` directory:
```env
# LLM Providers (Pick at least one to activate Semantic AI)
GROQ_API_KEY="gsk_..."
ANTHROPIC_API_KEY="sk-ant-..."
VOYAGE_API_KEY="pa-..."  # Recommended for code-aware embeddings

# Configuration Defaults
VECTOR_DB="chroma"
```

### 2. Launch the FastAPI Backend
```bash
# Navigate to backend directory
cd backend

# Create & activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\Activate.ps1

# Install requirements
pip install -r requirements.txt

# Start the uvicorn server
uvicorn app.main:app --reload --port 8000
```
*The API is now running and live at `http://localhost:8000`. You can inspect the interactive docs at `http://localhost:8000/docs`!*

### 3. Launch the Streamlit Frontend
In a new terminal window:
```bash
# Navigate to frontend directory
cd frontend

# Create & activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\Activate.ps1

# Install requirements
pip install -r requirements.txt

# Launch the Streamlit server
streamlit run app.py --server.port 8501
```
*The interactive dashboard will open instantly at `http://localhost:8501`!*

---

## 📂 Repository Layout Map

```text
├── backend/                       # REST API Backend Layer
│   ├── app/
│   │   ├── main.py                # FastAPI routes & cached repo memory
│   │   ├── models.py              # Composable Pydantic data schemas
│   │   ├── config.py              # Environment settings loading
│   │   ├── ingestor/              # Cloning, git walks & fallback parses
│   │   ├── indexer/               # Vector storage & Voyage/Chroma indexes
│   │   └── agents/                # Map, Plan, Tutor & Quiz logic modules
│   └── requirements.txt
│
└── frontend/                      # Streamlit Interactive Client Layer
    ├── app.py                     # Centered, simplified UI tab controllers
    └── requirements.txt
```
