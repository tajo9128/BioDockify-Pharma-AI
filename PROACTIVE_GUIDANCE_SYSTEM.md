# Proactive Guidance System

## Overview

Agent Zero (BioDockify AI) now includes a comprehensive proactive guidance system that automatically detects user roles (researcher or faculty) and provides intelligent suggestions and resources.

## Features

### 1. Automatic Role Detection
- Identifies if user is a **Researcher** (PhD student, scientist) or **Faculty** (professor, teacher)
- Confidence scoring based on keyword analysis and conversation history
- Context-aware adaptation over time

### 2. Researcher Guidance
For PhD students and scientists, the system provides:
- **Next Step Suggestions**: Based on current research stage
- **Planning Guidance**: Research questions, IRB/ethics applications
- **Literature Review**: Database recommendations, systematic reviews
- **Methodology Design**: Sample size calculation, experimental design
- **Data Collection**: Quality monitoring, optimization
- **Data Analysis**: Statistical methods, visualization
- **Publication Planning**: Target journals, manuscript preparation
- **Resource Recommendations**: Tools, databases, references

### 3. Faculty Guidance
For professors and teachers, the system provides:
- **Syllabus Management**: Upload and parse course syllabi
- **Class Preparation**: Automatic material generation for next class
- **Lecture Notes**: Comprehensive notes with learning objectives
- **PPT Slides**: Ready-to-use presentation slides
- **Resource Gathering**: Books, articles, videos for topics
- **Assessment Preparation**: Exam questions, grading rubrics
- **Study Guides**: Handouts and supplementary materials

## API Endpoints

### POST /api/proactive/process
Process a message and generate proactive guidance.

**Request:**
```json
{
  "user_id": "user_123",
  "message": "I'm working on my PhD thesis on Alzheimer's",
  "research_state": {
    "current_stage": "planning",
    "progress": 0.0,
    "tasks": []
  },
  "conversation_history": []
}
```

**Response:**
```json
{
  "role": "researcher",
  "confidence": 1.00,
  "guidance": [
    {
      "guidance_id": "uuid",
      "guidance_type": "next_step",
      "title": "Define Research Questions",
      "description": "Your research needs clear, focused questions",
      "action_items": [
        "Identify the main research question",
        "Formulate 3-5 specific sub-questions"
      ],
      "priority": "critical",
      "estimated_effort": "1-2 hours"
    }
  ],
  "actions": [
    {
      "action_id": "uuid_action_0",
      "description": "Identify the main research question",
      "priority": "critical",
      "type": "next_step"
    }
  ]
}
```

### POST /api/proactive/upload_syllabus
Upload and parse a course syllabus.

**Request:**
```json
{
  "user_id": "faculty_123",
  "syllabus_path": "/path/to/syllabus.pdf"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Syllabus uploaded successfully",
  "syllabus": {
    "course_info": {"title": "Pharmacology 101"},
    "weeks": [{"week": 1, "topic": "Introduction"}]
  },
  "guidance": []
}
```

### POST /api/proactive/generate_materials
Generate class materials for a specific week.

**Request:**
```json
{
  "user_id": "faculty_123",
  "week": 2,
  "topic": "Drug Metabolism"
}
```

**Response:**
```json
{
  "success": true,
  "week": 2,
  "topic": "Drug Metabolism",
  "notes": {"topic": "...", "content": {...}},
  "slides": {"presentation": {...}},
  "resources": {"books": [...], "articles": [...], "videos": [...]}
}
```

### GET /api/proactive/guidance/{user_id}
Get proactive guidance history for a user.

### GET /api/proactive/context/{user_id}
Get full user context including role and history.

## Usage Examples

### Example 1: Researcher getting guidance
**User Message:** "I need to plan my data analysis for my Alzheimer's research"

**System Response:**
- Detected Role: Researcher (Confidence: 100%)
- Guidance Provided:
  1. Perform Statistical Analysis (Critical)
  2. Plan for Publication (High)
  3. Review Upcoming Deadlines (Medium)
  4. Expand Your Toolkit (Low)

### Example 2: Faculty preparing for class
**User Message:** "I need to prepare for next week's class on drug discovery"

**System Response:**
- Detected Role: Faculty (Confidence: 100%)
- Guidance Provided:
  1. Next Class: Week 3 Materials (High)
  2. Enhance Lecture Materials (Medium)
  3. Prepare Student Assessments (Medium)
  4. Gather Additional Resources (Low)

## Supported File Formats

**Syllabi:** PDF, DOCX, TXT, MD
**Generated Materials:** JSON (for notes and slides)

## Research Stage Detection

The system automatically detects and adapts to these research stages:
1. **Planning** - Research questions, ethics approval
2. **Literature Review** - Database searches, systematic reviews
3. **Methodology Design** - Experimental design, sample size
4. **Data Collection** - Quality monitoring, optimization
5. **Data Analysis** - Statistical methods, visualization
6. **Results Interpretation** - Context analysis, implications
7. **Writing Draft** - Manuscript preparation

## Compliance

- **GDPR/CCPA**: User data can be exported/deleted on request
- **ISO 27001**: Security standards for educational data
- **GLP/GCP**: Research integrity maintained
- **International Standards**: Multi-language support (EN, ZH, ES, FR, DE, JA, KO, AR, PT, RU)
- **RTL Support**: Arabic and Hebrew interfaces supported

## Technical Architecture

### Components
- `modules/proactive_guidance.py` - Core guidance engines
- `modules/faculty_materials.py` - Syllabus parsing and material generation
- `modules/proactive_integration.py` - Role detection and API integration
- Integration with `api/main.py` - RESTful API endpoints

### Dependencies
- FastAPI - API framework
- PyPDF2 - PDF parsing
- python-docx - DOCX parsing
- Pathlib - File operations
- JSON - Data serialization

## Future Enhancements

- [ ] Real-time collaboration for multi-user classes
- [ ] Advanced analytics on student performance
- [ ] Integration with LMS systems (Canvas, Blackboard)
- [ ] Automated quiz generation from lecture content
- [ ] Research milestone tracking with notifications
- [ ] Peer review coordination for research groups

## Support

For issues or feature requests, please refer to the BioDockify AI documentation.

---

**Version:** 1.0.0  
**Last Updated:** 2026-02-14  
**Compliance:** International Pharmaceutical Research Standards
