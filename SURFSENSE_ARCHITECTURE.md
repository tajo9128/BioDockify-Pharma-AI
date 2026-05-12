# 🏗️ SurfSense Architecture - Internal Knowledge Base & Output Generator

**Date:** 2026-02-14
**Purpose:** Full storage and output functions for BioDockify AI research data

---

## 📋 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    BioDockify AI (Research Collector)                │
│  - Web scraping                                                   │
│  - Research paper extraction                                       │
│  - Data collection                                                 │
│  - Deep research orchestration                                    │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ upload_document()
                         │ (Research Data)
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│              SurfSense (Internal Knowledge Base)                  │
│              localhost:8000 - NO EXTERNAL API CALLS               │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  📦 STORAGE LAYER                                                 │
│  ───────────────────────────────────────────────────────────   │
│  • Stores all research data from BioDockify AI                     │
│  • Dual-write: SurfSense + ChromaDB                              │
│  • No external API calls for storage                             │
│  • Internal knowledge repository                                │
│                                                                   │
│  🔍 SEARCH LAYER                                                  │
│  ───────────────────────────────────────────────────────────   │
│  • Uses ChromaDB (built-in, FREE)                                │
│  • Internal vector search                                         │
│  • No external API calls                                          │
│  • Returns relevant research documents                            │
│                                                                   │
│  💬 CHAT LAYER                                                    │
│  ───────────────────────────────────────────────────────────   │
│  • Searches ChromaDB for context                                 │
│  • Uses Single LLM API for answer generation                     │
│  • Returns answers with citations                                 │
│  • No SurfSense API calls                                         │
│                                                                   │
│  🎧 AUDIO OUTPUT LAYER                                            │
│  ───────────────────────────────────────────────────────────   │
│  • Uses edge-tts (FREE, 20+ voices)                             │
│  • No API key required                                            │
│  • Multi-language support                                        │
│  • Generates MP3 audio files                                     │
│                                                                   │
│  🎥 VIDEO OUTPUT LAYER                                             │
│  ───────────────────────────────────────────────────────────   │
│  • Uses FFmpeg (FREE)                                             │
│  • Generates MP4 video files                                      │
│  • Combines slides + audio                                        │
│  • No API calls                                                   │
│                                                                   │
│  📊 SLIDES OUTPUT LAYER                                           │
│  ───────────────────────────────────────────────────────────   │
│  • Uses Playwright (FREE)                                        │
│  • Generates PNG slide images                                    │
│  • Renders markdown to visual slides                             │
│  • No API calls                                                   │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Data Flow

### 1. Research Data Collection

```
BioDockify AI Deep Research
│
├─> Web Scraping (Playwright)
│   └─> Research papers, articles, papers
│
├─> Content Extraction
│   └─> Title, abstract, content, metadata
│
└─> Research Result
    │
    └─> upload_document() to SurfSense
        │
        ├─> SurfSense Storage (localhost:8000)
        │   └─> Full research data storage
        │
        └─> ChromaDB (built-in)
            └─> Vector indexing for search
```

### 2. Knowledge Retrieval

```
User Query
│
└─> search() in SurfSense
    │
    └─> ChromaDB.search()
        │
        └─> Returns relevant research documents
            │
            ├─> Text content
            ├─> Source (paper URL, file)
            └─> Metadata (date, author, etc.)
```

### 3. Chat with Knowledge Base

```
User Question
│
├─> Search ChromaDB for context
│   └─> Get relevant research documents
│
├─> Build prompt with context
│   └─> "Based on these research papers..."
│
└─> Call Single LLM API
    │
    └─> Get answer with citations
```

### 4. Audio Output (FREE)

```
Text Content (research summary)
│
└─> generate_podcast()
    │
    └─> edge-tts (FREE, 20+ voices)
        │
        └─> MP3 audio file
            ├─> English, Chinese, Spanish, etc.
            ├─> No API key required
            └─> High-quality neural TTS
```

### 5. Video Output (FREE)

```
Markdown Content
│
├─> generate_slides()
│   └─> Playwright (FREE)
│       └─> PNG slide images
│
├─> generate_podcast()
│   └─> edge-tts (FREE)
│       └─> MP3 audio file
│
└─> create_video_summary()
    └─> FFmpeg (FREE)
        └─> MP4 video file
```

---

## 🔒 Security & Privacy

### External API Calls

| Component | Uses External API? | Which API? | API Key Required? |
|-----------|-------------------|------------|-------------------|
| **Storage** | ❌ No | Internal | No |
| **Search** | ❌ No | ChromaDB (built-in) | No |
| **Chat** | ✅ Yes | Single LLM API | Yes (your API) |
| **Audio** | ❌ No | edge-tts (FREE) | No |
| **Video** | ❌ No | FFmpeg (FREE) | No |
| **Slides** | ❌ No | Playwright (FREE) | No |

**Total External APIs Needed: 1** (Single LLM API for chat only)

### Data Privacy

- ✅ **Storage:** Internal SurfSense (localhost:8000) - no external cloud
- ✅ **Search:** ChromaDB (local vector store)
- ✅ **Audio:** edge-tts (Microsoft Edge servers for TTS)
- ✅ **Video:** FFmpeg (local processing)
- ✅ **Slides:** Playwright (local rendering)

---

## 📦 SurfSense Functions Breakdown

### Storage Functions

| Function | Purpose | API Calls |
|-----------|---------|-----------|
| `upload_document()` | Stores research data | SurfSense API (internal) |
| `_sync_to_surfsense()` | Dual-write to SurfSense + ChromaDB | SurfSense API (internal) |

### Search Functions

| Function | Purpose | API Calls |
|-----------|---------|-----------|
| `search()` | Searches knowledge base | ChromaDB (built-in, FREE) |
| `list_documents()` | Lists stored documents | ChromaDB (built-in, FREE) |

### Chat Functions

| Function | Purpose | API Calls |
|-----------|---------|-----------|
| `chat()` | Answers questions with citations | ChromaDB + Single LLM API |

### Output Functions (FREE)

| Function | Purpose | API Calls | Technology |
|-----------|---------|-----------|-----------|
| `generate_podcast()` | Generates audio | No | edge-tts (FREE) |
| `create_video_summary()` | Generates video | No | FFmpeg (FREE) |
| `generate_slides()` | Generates slides | No | Playwright (FREE) |

---

## 🎓 Student Benefits

### Cost Savings

- ✅ **Storage:** FREE (SurfSense internal)
- ✅ **Search:** FREE (ChromaDB built-in)
- ✅ **Audio:** FREE (edge-tts, 20+ voices)
- ✅ **Video:** FREE (FFmpeg)
- ✅ **Slides:** FREE (Playwright)

### Only 1 API Needed

- ✅ **Single LLM API** - For chat with knowledge base
- ✅ **All other functions** - FREE, no API needed

### Features Available

- ✅ **Web Scraping** - Research paper collection
- ✅ **Deep Research** - PhD-level orchestration
- ✅ **Knowledge Storage** - SurfSense full storage
- ✅ **Vector Search** - ChromaDB built-in
- ✅ **Chat with Knowledge** - RAG-powered Q&A
- ✅ **Audio Generation** - 20+ languages, FREE
- ✅ **Video Generation** - Summary videos, FREE
- ✅ **Slides Generation** - Visual presentations, FREE

---

## 🚀 Configuration

### Single API Configuration

**File:** `/a0/usr/settings.json`

```json
{
  "api_keys": {
    "openai": "YOUR_API_KEY_HERE"
  },
  "chat_model_name": "YOUR_MODEL_NAME",
  "chat_model_api_base": "YOUR_API_ENDPOINT"
}
```

### SurfSense Configuration

**File:** `runtime/config.yaml`

```yaml
ai_provider:
  # Single LLM API for chat
  mode: custom
  lm_studio_url: "https://YOUR_API_ENDPOINT.com/v1"
  lm_studio_model: "YOUR_MODEL_NAME"
  glm_key: "YOUR_API_KEY_HERE"
  
  # SurfSense internal storage
  surfsense_enabled: true
  surfsense_url: "http://localhost:8000"
  
  # ChromaDB built-in
  use_chromadb: true
```

---

## 📊 API Endpoints

### Research & Storage

| Endpoint | Purpose | Uses External API? |
|----------|---------|-------------------|
| `POST /api/agent/chat` (action=deep_research) | Web scraping & research | Single LLM API |
| `POST /api/surfsense/upload` | Upload document | No (internal) |
| `POST /api/rag/upload` | Ingest to ChromaDB | No (internal) |

### Knowledge Retrieval

| Endpoint | Purpose | Uses External API? |
|----------|---------|-------------------|
| `POST /api/surfsense/search` | Search knowledge base | No (ChromaDB) |
| `POST /api/surfsense/chat` | Chat with knowledge base | Single LLM API |

### Output Functions (FREE)

| Endpoint | Purpose | Uses External API? |
|----------|---------|-------------------|
| `POST /api/surfsense/podcast` | Generate audio | No (edge-tts) |
| `POST /api/surfsense/video` | Generate video | No (FFmpeg) |
| `POST /api/surfsense/slides` | Generate slides | No (Playwright) |

---

## ✅ Architecture Verification

### Storage ✓
- [x] BioDockify AI collects research data
- [x] Data stored in SurfSense (localhost:8000)
- [x] Dual-write to ChromaDB for backup
- [x] No external API calls for storage

### Search ✓
- [x] Internal ChromaDB vector search
- [x] No external API calls for search
- [x] Returns relevant research documents
- [x] Includes citations and metadata

### Chat ✓
- [x] Searches ChromaDB for context
- [x] Uses single LLM API for answers
- [x] Returns answers with citations
- [x] No SurfSense API calls

### Output Functions ✓
- [x] Audio: edge-tts (FREE, 20+ voices)
- [x] Video: FFmpeg (FREE)
- [x] Slides: Playwright (FREE)
- [x] No API keys needed for output

---

## 🎉 Summary

**SurfSense is configured as:**

✅ **Internal Knowledge Base** - Stores all research data from BioDockify AI
✅ **Storage Layer** - Full storage of research papers and data
✅ **Output Generator** - Free audio, video, and slides
✅ **No External APIs** - Except single LLM API for chat
✅ **Student Friendly** - 1 API key, FREE outputs

**Total APIs Needed:** 1 (Single LLM API for chat)
**Total Cost:** $0 + your LLM API usage

---

**Your SurfSense knowledge base is ready for student research!** 🎓🚀

