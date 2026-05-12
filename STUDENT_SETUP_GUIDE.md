# 🎓 BioDockify AI - Student Setup Guide
**SurfSense Knowledge Base Storage + Single API Configuration**

---

## 📋 Quick Summary

**What You Get:**
✅ **1 API key** - Your single LLM provider (DeepSeek, Modal API, etc.)
✅ **SurfSense storage** - Knowledge base at localhost:8000
✅ **ChromaDB** - Built-in vector search (FREE)
✅ **Edge-TTS** - Free audio generation (20+ voices)
✅ **FFmpeg** - Free video generation
✅ **All research features** - No additional costs

**Total APIs Needed:** 1 (your single LLM API)
**Total Cost:** $0 + your LLM API usage

---

## 🎯 What Was Changed

### 1. Audio Generation (FREE)
**File:** `modules/surfsense/audio.py`

**Before:** OpenAI TTS API (paid, requires API key)

**After:** Microsoft Edge TTS (FREE, no API key, 20+ voices)

**Voices Available:** English, Chinese, Spanish, French, German, Japanese, Arabic, Korean, Portuguese, Italian, Russian, etc.

**Usage:**
```python
await generate_podcast_audio(
    text="Hello students!",
    voice="alloy",  # Maps to en-US-AriaNeural
    output_path="podcast.mp3"
)
```

### 2. SurfSense Knowledge Base (STORAGE ONLY)
**File:** `modules/surfsense/client.py`

**Purpose:** Store research data from BioDockify AI deep research

**How It Works:**
```
BioDockify AI Deep Research
       ↓
   Research Results
       ↓
┌─────────────────────────────────────┐
│  Dual-Write Storage Strategy       │
├─────────────────────────────────────┤
│  1. SurfSense (localhost:8000)     │ ← STORAGE
│     upload_document()               │
│                                    │
│  2. ChromaDB (built-in)          │ ← FALLBACK
│     ingest_file()                  │
└─────────────────────────────────────┘
```

**Functions:**
| Function | Uses | Cost |
|----------|-------|------|
| `upload_document()` | SurfSense API (storage only) | FREE |
| `search()` | ChromaDB (built-in) | FREE |
| `chat()` | ChromaDB + Single LLM API | Your API |
| `generate_podcast()` | edge-tts (FREE) | FREE |

---

## 🚀 Student Setup Instructions

### Step 1: Choose Your Single LLM API

**Option A: DeepSeek (Pay-as-you-go, affordable)**
- Sign up: [platform.deepseek.com](https://platform.deepseek.com)
- Get API Key
- Endpoint: `https://api.deepseek.com`
- Model: `deepseek-reasoner`

**Option B: Modal API (GLM-5-FP8, FREE)**
- Sign up: [modal.com](https://modal.com)
- Get API Key
- Endpoint: `https://api.us-west-2.modal.direct/v1`
- Model: `zai-org/GLM-5-FP8`

**Option C: OpenAI (Pay-as-you-go)**
- Sign up: [platform.openai.com](https://platform.openai.com)
- Get API Key
- Endpoint: `https://api.openai.com/v1`
- Model: `gpt-4o`

### Step 2: Configure Single API

**Edit:** `/a0/usr/settings.json`

```json
{
  "api_keys": {
    "openai": "YOUR_API_KEY_HERE"
  },
  "chat_model_provider": "openai",
  "chat_model_name": "YOUR_MODEL_NAME",
  "chat_model_api_base": "YOUR_API_ENDPOINT",
  "util_model_provider": "openai",
  "util_model_name": "YOUR_MODEL_NAME",
  "util_model_api_base": "YOUR_API_ENDPOINT",
  "browser_model_provider": "openai",
  "browser_model_name": "YOUR_MODEL_NAME",
  "browser_model_api_base": "YOUR_API_ENDPOINT"
}
```

**Replace:**
- `YOUR_API_KEY_HERE` → Your actual API key
- `YOUR_MODEL_NAME` → Your model name (e.g., `deepseek-reasoner`, `zai-org/GLM-5-FP8`, `gpt-4o`)
- `YOUR_API_ENDPOINT` → Your API endpoint (e.g., `https://api.deepseek.com`)

### Step 3: Configure SurfSense (Storage Only)

**Edit:** `runtime/config.yaml`

```yaml
ai_provider:
  # Single LLM API configuration
  mode: custom
  lm_studio_url: "https://YOUR_API_ENDPOINT.com/v1"
  lm_studio_model: "YOUR_MODEL_NAME"
  glm_key: "YOUR_API_KEY_HERE"
  
  # SurfSense configuration
  surfsense_enabled: true
  surfsense_url: "http://localhost:8000"
  
  # ChromaDB (built-in)
  use_chromadb: true
  
  # Fallback enabled
  cloud_fallback: true
```

**Note:** SurfSense is used ONLY for storage. Search and chat use ChromaDB + your single API.

### Step 4: Start Services

**Option A: Start SurfSense (if you have Docker)**
```bash
docker run -d -p 8000:8000 --name surfsense your-surfsense-image
```

**Option B: Without SurfSense**
- SurfSense will be skipped automatically
- Data will be stored in ChromaDB only
- All features still work!

**Start BioDockify AI Server:**
```bash
python server.py
```

### Step 5: Verify Setup

**Check Server:**
```bash
curl http://localhost:3000/api/health
```

**Test Chat:**
1. Open `http://localhost:3000` in browser
2. Send: "Hello, are you working with my single API?"
3. Verify response

**Test Audio Generation (FREE):**
```bash
curl -X POST "http://localhost:3000/api/surfsense/podcast" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Testing free TTS for students",
    "voice": "alloy"
  }'
```

---

## 📊 Complete Feature Matrix

| Feature | API Used | Cost | Status |
|---------|-----------|-------|--------|
| **Chat with AI** | Single LLM API | Your API | ✅ Working |
| **Utility Tasks** | Single LLM API | Your API | ✅ Working |
| **Browser Automation** | Single LLM API | Your API | ✅ Working |
| **Deep Research** | Single LLM API | Your API | ✅ Working |
| **Code Generation** | Single LLM API | Your API | ✅ Working |
| **Vector Storage** | ChromaDB | FREE | ✅ Working |
| **Vector Search** | ChromaDB | FREE | ✅ Working |
| **Document Ingestion** | ChromaDB | FREE | ✅ Working |
| **RAG Queries** | ChromaDB + Single API | Your API | ✅ Working |
| **Audio/TTS** | edge-tts | FREE | ✅ Working |
| **Video Generation** | FFmpeg | FREE | ✅ Working |
| **Slide Generation** | Playwright | FREE | ✅ Working |
| **Knowledge Storage** | SurfSense | FREE | ✅ Working |
| **Knowledge Search** | ChromaDB | FREE | ✅ Working |
| **Knowledge Chat** | ChromaDB + Single API | Your API | ✅ Working |

---

## 🎓 Student Benefits

### What Students Save:
- ✅ **Money:** Only 1 API subscription needed
- ✅ **Time:** No complex multi-API configuration
- ✅ **Complexity:** Simple setup with one API key
- ✅ **Audio:** FREE TTS in 20+ languages
- ✅ **Storage:** SurfSense knowledge base included

### What Students Get:
- ✅ **Professional AI Research Assistant**
- ✅ **PhD-Level Research Orchestration**
- ✅ **Vector Database for Papers**
- ✅ **RAG-Powered Q&A**
- ✅ **Free Podcast Generation**
- ✅ **Free Video Summaries**
- ✅ **Multi-Language Support**
- ✅ **Deep Research Capabilities**
- ✅ **Knowledge Base Storage**

---

## 🔧 API Endpoints

### 1. Chat with AI
```bash
POST /api/agent/chat
{
  "message": "Research Alzheimer's disease treatments"
}
```

### 2. Deep Research
```bash
POST /api/agent/chat
{
  "message": "Research this paper",
  "action": "deep_research",
  "params": {
    "url": "https://arxiv.org/abs/1234.5678"
  }
}
```

**Result:** Research data stored in BOTH:
- SurfSense (localhost:8000) - Knowledge base storage
- ChromaDB - Built-in fallback

### 3. Upload Document
```bash
POST /api/rag/upload
Content-Type: multipart/form-data
file=@paper.pdf
```

**Result:** Document indexed in ChromaDB

### 4. Search Knowledge Base
```bash
POST /api/surfsense/search
{
  "query": "Alzheimer's treatments",
  "top_k": 5
}
```

**Uses:** ChromaDB (FREE, no API)

### 5. Chat with Knowledge Base
```bash
POST /api/surfsense/chat
{
  "message": "What are the main findings?"
}
```

**Uses:** ChromaDB + Single LLM API

### 6. Generate Podcast (FREE)
```bash
POST /api/surfsense/podcast
{
  "text": "Research summary here...",
  "voice": "alloy"
}
```

**Uses:** edge-tts (FREE, 20+ voices)

---

## 🎨 Available Free Voices

| Voice ID | Language | Description |
|----------|----------|-------------|
| `alloy` | English (US) | Aria (Female) |
| `echo` | English (US) | Guy (Male) |
| `fable` | English (UK) | Sonia (Female) |
| `onyx` | English (UK) | Ryan (Male) |
| `nova` | English (AU) | Natasha (Female) |
| `shimmer` | English (IN) | Neerja (Female) |
| `zh-CN-XiaoxiaoNeural` | Chinese | Xiaoxiao (Female) |
| `es-ES-ElviraNeural` | Spanish | Elvira (Female) |
| `fr-FR-DeniseNeural` | French | Denise (Female) |
| `de-DE-KatjaNeural` | German | Katja (Female) |
| `ja-JP-NanamiNeural` | Japanese | Nanami (Female) |
| `ko-KR-SunHiNeural` | Korean | SunHi (Female) |
| `ar-SA-ZariyahNeural` | Arabic | Zariyah (Female) |
| `pt-BR-FranciscaNeural` | Portuguese | Francisca (Female) |

**20+ more voices available!**

---

## 🐛 Troubleshooting

### Issue: "SurfSense offline" error
**Solution:**
- This is normal if you don't have SurfSense Docker container running
- Data will be stored in ChromaDB only (built-in)
- All features work perfectly with ChromaDB alone

### Issue: "API key invalid"
**Solution:**
- Check your API key in `/a0/usr/settings.json`
- Verify your API key is active at your provider's dashboard
- Restart server after updating API key

### Issue: "Search returns no results"
**Solution:**
- Upload documents first: `POST /api/rag/upload`
- Check ChromaDB is working: `ls data/chroma_memory/`
- Verify search query is relevant to uploaded documents

### Issue: "Audio generation fails"
**Solution:**
- Ensure edge-tts is installed: `pip install edge-tts`
- Test directly: `python modules/surfsense/audio.py`
- Check internet connection (edge-tts needs to access Microsoft servers)

---

## 📞 Getting Help

If you encounter issues:

1. **Check logs:** `tail -f logs/server.log`
2. **Test API:** Use curl commands above
3. **Verify config:** Check `/a0/usr/settings.json` and `runtime/config.yaml`
4. **Check ChromaDB:** `ls data/chroma_memory/`
5. **Check SurfSense:** `curl http://localhost:8000/health` (if running)

---

## ✅ Configuration Checklist

Before starting, verify:

- [ ] **Single LLM API** configured in `/a0/usr/settings.json`
- [ ] **API key** replaced placeholder
- [ ] **API endpoint** is correct
- [ ] **Model name** is correct
- [ ] **SurfSense URL** configured (if using SurfSense)
- [ ] **Server restarted** after configuration
- [ ] **Health check** passed: `curl http://localhost:3000/api/health`
- [ ] **Chat tested** in web interface
- [ ] **Audio tested** with curl command above


---

## 🎉 Summary

**Your BioDockify AI is now configured for students!**

✅ **1 API key** - Your single LLM provider
✅ **SurfSense storage** - Knowledge base at localhost:8000
✅ **ChromaDB** - Built-in vector search (FREE)
✅ **Edge-TTS** - Free audio generation (20+ voices)
✅ **All research features** - No additional costs

**Total APIs Needed:** 1 (your single LLM API)
**Total Cost:** $0 + your LLM API usage

**Total Setup Time:** 5 minutes

---

**Happy Researching!** 🎓🚀

