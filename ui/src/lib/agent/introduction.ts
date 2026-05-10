/**
 * BioDockify AI Introduction Module
 * 
 * Contains the comprehensive self-introduction text for BioDockify AI.
 * This introduction is displayed when a user first interacts with the chat.
 */

export const BIODOCKIFY_INTRODUCTION = `**Hello.**

I am **BioDockify AI**, an intelligent research assistant designed for pharmaceutical and life-science research, supporting PG students, PhD scholars, faculty, and early-stage researchers.

I am built to **analyze research**, not merely generate text, and to **automate repetitive academic tasks** while preserving scientific rigor.

---

## Core Capabilities

### 1. Deep Literature Analysis
I perform structured scientific analysis, including:
- Comparative analysis across multiple papers
- Identification of methodological strengths and weaknesses
- Detection of contradictions, inconsistencies, and evidence gaps
- Trend analysis across years, targets, or experimental models

### 2. Automatic Literature Review Workflow
Once you upload papers, I can automatically:
- Extract objectives, methods, results, and conclusions
- Organize studies by theme, target, methodology, or outcome
- Generate structured literature review drafts
- Maintain consistency across chapters and revisions

### 3. Evidence-Driven Research Analysis
All outputs are:
- Directly grounded in uploaded documents or cited sources
- Clearly labeled when evidence is strong, weak, or missing
- Free from fabricated data or unsupported claims

### 4. Automatic Research Continuity (Project Memory)
I automatically:
- Remember research objectives, hypotheses, and decisions
- Track changes across drafts and sessions
- Maintain logical continuity across chapters

### 5. Automated Academic Writing Support
I can automatically:
- Convert analysis into thesis-ready paragraphs
- Improve scientific language without changing meaning
- Align content with reviewer and journal expectations

### 6. Persona-Aware Behavior
Based on your role, I automatically adjust depth of explanation, level of critique, and terminology.

---

## What I Will NOT Do
❌ Invent results  
❌ Fabricate citations  
❌ Override scientific reasoning  
❌ Perform uncontrolled web scraping

---

## How to Start
Simply:
- **Upload research papers**
- **Upload a thesis chapter**
- **State your research topic**

I will automatically initiate literature parsing, evidence mapping, and analytical structuring.

---

*BioDockify AI analyzes research and automates academic workflows — it does not merely generate text.*`;

/**
 * Short introduction for returning users or quick mode
 */
export const BIODOCKIFY_SHORT_INTRO = `Hello, I am **BioDockify AI** — your intelligent research assistant for pharmaceutical and life-science research.

I am built to **analyze research** and **automate academic workflows**, not merely generate text.

You can:
- Upload research papers for analysis
- Ask me to search literature
- Request structured literature reviews
- Get help with thesis writing

How can I assist your research today?`;

/**
 * Get appropriate introduction based on context
 */
export function getIntroduction(isFirstTime: boolean = true): string {
    return isFirstTime ? BIODOCKIFY_INTRODUCTION : BIODOCKIFY_SHORT_INTRO;
}

/**
 * One-line positioning statement
 */
export const POSITIONING_STATEMENT = "BioDockify AI analyzes research and automates academic workflows — it does not merely generate text.";
