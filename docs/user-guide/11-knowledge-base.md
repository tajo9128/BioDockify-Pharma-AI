# Chapter 11: Knowledge Base & Research Memory

## 11.1 Overview
ChromaDB vector store for semantic search and persistent research memory across sessions.

### Access Path
**All Tools → Knowledge Base** (or click 🧠 icon)

---

## 11.2 Adding Documents
- **Upload**: PDF, TXT, MD files
- **Paste**: Text content
- **Auto-ingestion**: Documents chunked and embedded automatically
- **Tags**: Organize by topic/project

---

## 11.3 Semantic Search
- **Query**: Natural language questions
- **Results**: Ranked by cosine similarity
- **Context**: Shows surrounding text for each match
- **Persistent**: Search results survive Docker restarts

---

## 11.4 Knowledge Graph
- **Visualization**: Force-directed graph of document relationships
- **Nodes**: Documents and concepts
- **Edges**: Semantic similarity links
- **Interactive**: Click nodes to view documents

---

## 11.5 Cross-Session Memory
- **Ebbinghaus decay**: 30-day time-decay model
- **Reinforcement**: Frequently accessed knowledge retains higher weight
- **Evolution**: Knowledge base grows across research sessions
- **Backup**: Stored in Docker volume, survives container updates

---

## 11.6 Example: Building a Research Library
1. Upload 50 papers on "nanoparticle drug delivery"
2. Later search "liposomal formulation challenges"
3. View ranked results linking to stored documents
4. Click knowledge graph to see document relationships
5. Tag documents by project for organization
