# System Architecture

BioDockify is a hybrid desktop application combining a high-performance native shell with a containerized microservices backend. This architecture ensures cross-platform compatibility while maintaining the performance required for ML tasks.

## High-Level Diagram

```mermaid
graph TD
    User[User] -->|Interacts| UI[Tauri Frontend (React)]
    UI -->|IPC Calls| Core[Rust Core Process]
    Core -->|HTTP/REST| API[FastAPI Backend (Python)]
    
    subgraph "Docker Container / Local Runtime"
        API -->|Orchestrates| Agent[Agent Zero (Orchestrator)]
        Agent -->|Calls| BioNER[BioNER Model (TensorFlow)]
        Agent -->|Calls| GraphDB[(Neo4j Knowledge Graph)]
        Agent -->|Calls| VectorDB[(Chroma/FAISS Vector Store)]
    end
    
    BioNER -->|Reads| PDFs[PDF Documents]
    BioNER -->|Writes| GraphDB
```

## Components

### 1. Frontend (UI)
*   **Tech:** React.js, TailwindCSS, Lucide Icons.
*   **Role:** Renders the interactive dashboard, chat interface, and D3.js/Vis.js graph visualizations.
*   **Communication:** Communicates with the Rust layer via Tauri Commands.

### 2. Desktop Shell (Tauri)
*   **Tech:** Rust.
*   **Role:** Manages the application window, native file system access, and system tray. It acts as a secure proxy between the UI and the Python backend.

### 3. Intelligence Layer (Python)
*   **Tech:** Python 3.10, FastAPI, LangChain.
*   **Role:**
    *   **API:** Exposes endpoints for the UI.
    *   **Agent Zero:** The central logic unit that interprets user intent.
    *   **Tool Registry:** A collection of functional tools (e.g., `lookup_gene`, `parse_pdf`) that the agent can invoke.

### 4. Data Layer
*   **Neo4j:** Stores the structured Knowledge Graph (Nodes & Edges).
*   **Vector Store:** Stores embeddings of text chunks for semantic search.
*   **SQLite:** Stores persistent app configuration and session history.

## Design Decisions

### Why Local-First?
Pharma research involves highly sensitive IP. By running the "Thinking" models and databases locally (or in self-hosted containers), we ensure that **no data leaves the user's premise** by default.

### Why Agentic?
Traditional rigid pipelines break when faced with unstructured/messy data. An **Agentic** approach allows the system to dynamic "re-plan" if a PDF is unreadable or a search yields no results, imitating how a human researcher adapts.
