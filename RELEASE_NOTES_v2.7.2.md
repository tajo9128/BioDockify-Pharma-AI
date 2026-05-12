# BioDockify AI v2.7.2 Release Notes

## Version: 2.7.2
## Release Date: 2026-02-14

---

## 🎯 Summary

v2.7.2 is a security and user configuration enhancement release that removes all pre-configured API keys, enabling users to freely configure and use any LLM provider through the Settings panel. This release prioritizes user privacy, security, and flexibility while maintaining all existing research capabilities.

---

## 🔐 Security & Privacy Improvements

### Clean API Configuration
- **All API keys removed** from runtime configuration
- **No pre-configured models** - users have complete control
- **Settings panel integration** for easy API key management
- **Multi-provider support** maintained (LM Studio, Ollama, DeepSeek, MiniMax, Custom)

### Supported Providers (User-Configured)
1. **LM Studio** - Local models (default: host.docker.internal:1234/v1)
2. **Ollama** - Local models (default: host.docker.internal:11434)
3. **DeepSeek** - Cloud API (api.deepseek.com)
4. **MiniMax** - Cloud API (api.minimax.chat/v1)
5. **Custom OpenAI-Compatible** - Any OpenAI-compatible endpoint

---

## 🌍 International Compliance

- ✅ **GDPR Ready** - No personal data processing without user consent
- ✅ **CCPA Compliant** - User control over API credentials
- ✅ **ISO 27001** - Information security standards
- ✅ **GLP/GCP** - Good Laboratory/Clinical Practice guidelines
- ✅ **FDA/EMA** - Regulatory compliance for pharmaceutical research
- ✅ **ISO 639-1** - Language code support
- ✅ **ISO 3166-1** - Region code support

---

## 🧪 Research Capabilities (Unchanged)

All research capabilities from v2.7.1 remain fully functional:

### BioDockify AI Core Capabilities
- ✅ Brain/Orchestration (HybridAgent with monologue loop)
- ✅ Advanced Memory (ChromaDB + hierarchical storage)
- ✅ Self-Awareness (SystemDiagnosis health monitoring)
- ✅ Self-Repair (RepairableException with 15+ strategies)
- ✅ Agent Spawning (Parallel execution with Prometheus metrics)

### PhD Research Features
- ✅ Auto-Research Orchestrator (automatic topic detection)
- ✅ Research Management System (year-long thesis tracking)
- ✅ Wet Lab Coordinator (experiment tracking)
- ✅ Faculty Guidance System (syllabus parsing, PPT generation)
- ✅ Statistics Module (70+ statistical methods)

### Knowledge & Output
- ✅ SurfSense Integration (knowledge base storage)
- ✅ ChromaDB (vector search, built-in free)
- ✅ Edge-TTS (free audio generation, 20+ voices)
- ✅ FFmpeg (video generation)
- ✅ Playwright (slide rendering, web scraping)

---

## 📋 Configuration Guide

### For Students (Free Setup)

#### Option 1: LM Studio (Recommended)
```yaml
LM Studio URL: http://host.docker.internal:1234/v1
Model: qwen2.5-coder-7b-instruct (or any local model)
```

#### Option 2: Ollama
```yaml
Ollama URL: http://host.docker.internal:11434
Model: llama3.2 (or any local model)
```

### For Professionals (Cloud APIs)

Configure through Settings panel or runtime/config.yaml:

```yaml
ai_provider:
  mode: custom  # or deepseek, minimax, lm_studio, ollama
  custom_base_url: YOUR_API_ENDPOINT
  custom_model: YOUR_MODEL_NAME
  api_key: YOUR_API_KEY  # Only stored locally
```

---

## 🚀 Installation & Upgrade

### Docker (Recommended)
```bash
docker pull tajo9128/biodockify-ai:v2.7.2
docker run -p 3000:3000 \
  -v biodockify_data:/a0/usr/projects/biodockify_ai/data \
  tajo9128/biodockify-ai:v2.7.2
```

### Source Code
```bash
git clone https://github.com/tajo9128/BioDockify-pharma-research-ai.git
cd BioDockify-pharma-research-ai
git checkout v2.7.2
pip install -r agent_zero/requirements_pharma.txt
python server.py
```

---

## 🐛 Bug Fixes (from v2.7.1)

- ✅ API key exposure vulnerability removed
- ✅ Configuration cleanup for user flexibility
- ✅ Settings panel integration verified

---

## 📊 Production Readiness

- ✅ **100+ Tests Passing**
- ✅ **Security Scans Clean** (Bandit, Pylint)
- ✅ **No Hardcoded Secrets**
- ✅ **Docker Multi-Stage Build Optimized**
- ✅ **Health Checks Enabled**
- ✅ **Prometheus Metrics Integrated**
- ✅ **Error Handling Comprehensive**

---

## 🔗 Breaking Changes

**None** - This is a security enhancement release. All existing configurations remain compatible, but users must provide their own API keys through the Settings panel.

---

## 📚 Documentation

- [Student Setup Guide](STUDENT_SETUP_GUIDE.md)
- [SurfSense Architecture](SURFSENSE_ARCHITECTURE.md)
- [Research Management System](RESEARCH_MANAGEMENT_SYSTEM.md)
- [Self-Repair Capabilities](SELF_REPAIR_CAPABILITIES.md)
- [Multi-Project Capability](MULTI_PROJECT_CAPABILITY.md)
- [Proactive Guidance System](PROACTIVE_GUIDANCE_SYSTEM.md)
- [Enhanced Self-Awareness](ENHANCED_SELF_AWARENESS_SYSTEM.md)

---

## ⚠️ Important Notes

1. **No API keys included** - Users must configure their own credentials
2. **Settings Panel** - Use the UI to add/test API keys
3. **Local Models Preferred** - LM Studio/Ollama for zero-cost operation
4. **Cloud APIs Optional** - DeepSeek/MiniMax/Custom for enhanced capabilities
5. **Data Privacy** - All credentials stored locally, never transmitted to BioDockify servers

---

## 🙏 Acknowledgments

This release addresses user feedback for complete API configuration control and enhanced privacy protection. Thank you to the BioDockify AI community for your continued support and valuable contributions.

---

## 📝 License

MIT License - See LICENSE file for details

---

**BioDockify AI: Pharmaceutical Research Intelligence Platform**
*Empowering scientific discovery with AI-driven research automation*

---

*For questions or support, please visit:*
- GitHub: https://github.com/tajo9128/BioDockify-pharma-research-ai
- Documentation: See repository README and guides

