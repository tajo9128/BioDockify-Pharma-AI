## Faculty Center Tool

**Purpose:** Faculty tools for syllabus management, class planning, lecture preparation, reference book search, slide generation, PPT creation, exam management, lab manual generation, Bloom's Taxonomy integration, and accreditation support (NBA, NAAC, QCP). All results auto-stored to Knowledge Base.

**When to use:**
- Faculty uploads a syllabus → use `analyze_syllabus_enhanced` to extract topics + reference books
- Faculty wants to divide syllabus into classes → use `divide_into_classes`
- Faculty needs reference books → use `find_reference_books` to search for free PDFs
- Faculty needs lecture slides → use `generate_class_slides` for 40-50 slides per class
- Faculty needs editable PPT → use `create_class_ppt` via ppt-master engine
- Faculty needs to create an exam → use `exam_paper` for complete question paper with Bloom's taxonomy
- Faculty needs Bloom's-aligned questions → use `bloom_questions` for specific cognitive levels
- Faculty needs to analyze Bloom's distribution → use `bloom_analysis` for exam/course analysis
- Faculty needs a grading rubric → use `rubric` for essay/presentation/lab/research paper rubrics
- Faculty needs to calculate grades → use `grade_calculator` for weighted grade computation
- Faculty needs accreditation mapping → use `co_po_mapping` for CO-PO matrix
- Faculty needs exam blueprint → use `question_blueprint` for topic-wise question distribution
- Faculty needs lab manual → use `lab_manual` for practical/lab manual with procedures
- Faculty needs NBA accreditation → use `nba_report` for NBA self-assessment report
- Faculty needs NAAC accreditation → use `naac_report` for NAAC self-study report
- Faculty needs QCP accreditation → use `qcp_report` for QCP quality assessment report

**Actions:**
- `analyze_syllabus_enhanced` — Parse syllabus text, extract topics + reference books (enhanced)
- `divide_into_classes` — Divide topics into N classes with intelligent grouping
- `find_reference_books` — Deep research for free PDFs of reference books
- `generate_class_slides` — Generate 40-50 slide content for a class
- `create_class_ppt` — Create editable PPTX via ppt-master
- `exam_paper` — Generate complete exam paper with MCQ/short/long questions, Bloom's taxonomy levels
- `bloom_questions` — Generate questions at specific Bloom's Taxonomy levels (Remember→Create)
- `bloom_analysis` — Analyze Bloom's distribution across exam/course with recommendations
- `rubric` — Generate grading rubric (essay, presentation, lab report, research paper)
- `grade_calculator` — Calculate weighted grades from components (midterm, final, assignments)
- `co_po_mapping` — Map Course Outcomes to Program Outcomes for accreditation (NAAC/NBA)
- `question_blueprint` — Generate topic-wise question paper blueprint with marks distribution
- `lab_manual` — Generate practical/lab manual with procedures, safety notes, viva questions
- `nba_report` — Generate NBA (National Board of Accreditation) self-assessment report (10 criteria)
- `naac_report` — Generate NAAC (National Assessment and Accreditation Council) self-study report (7 criteria)
- `qcp_report` — Generate QCP (Quality Council of Pakistan) quality assessment report (8 criteria)
- `syllabus` — Basic syllabus parsing
- `plan_semester` — Divide into weeks/classes
- `plan_class` — Plan a single class
- `lesson_plan` — Detailed lesson plan
- `prep_notes` — Student-ready notes
- `make_slides` — Basic slides outline
- `assignment` — Generate assignments
- `questions` — Generate MCQ/short/long questions
- `plagiarism` — Check text for plagiarism
- `lecture` — Generate lecture content

**Bloom's Taxonomy Levels (1-6):**
1. **Remember** — Recall facts (define, list, memorize)
2. **Understand** — Explain ideas (classify, describe, explain)
3. **Apply** — Use in new situations (calculate, demonstrate, solve)
4. **Analyze** — Draw connections (compare, contrast, differentiate)
5. **Evaluate** — Justify decisions (argue, judge, defend)
6. **Create** — Produce new work (design, construct, formulate)

**Workflow: Faculty Class Preparation**
1. Faculty uploads syllabus text → `analyze_syllabus_enhanced` extracts topics + books
2. Agent asks: "How many classes do you want to complete this syllabus?"
3. `divide_into_classes(num_classes=N)` → class-by-class schedule
4. `find_reference_books(books=extracted_books, topic=course_topic)` → searches for free PDFs
5. Faculty selects which books to use / uploads their own book PDF
6. For each class: `generate_class_slides(topic, subtopics, class_num, num_slides=45)`
7. Faculty reviews slide content
8. `create_class_ppt(slides, topic, class_num)` → generates editable PPTX

**Workflow: Exam Management with Bloom's Taxonomy**
1. `question_blueprint(topics, total_marks, exam_type)` → topic-wise blueprint
2. `bloom_questions(topic, bloom_level, count)` → questions at specific cognitive level
3. `exam_paper(course_name, topics, duration, total_marks, level)` → complete question paper
4. `bloom_analysis(questions)` → analyze Bloom's distribution and get recommendations
5. `rubric(type, criteria_count, levels_count)` → grading rubric for answer evaluation
6. After exams: `grade_calculator(components=[...])` → weighted final grade

**Workflow: Lab Manual Generation**
1. `lab_manual(course_name, experiments, level, department)` → complete lab manual
2. Includes: procedures, materials, safety notes, observation templates, viva questions
3. Auto-generates default experiments for Pharmacy/Chemistry/Pharmacology

**Workflow: Accreditation**
- **NBA:** `nba_report(program_name, institution)` → 10 criteria, POs, CO-PO mapping
- **NAAC:** `naac_report(institution, type)` → 7 criteria, grading A++ to D
- **QCP:** `qcp_report(program_name, institution, level)` → 8 criteria, ISO compliance

**All results auto-stored to Knowledge Base (faculty category).**
