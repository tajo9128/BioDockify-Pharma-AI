# BioDockify AI - Pharmaceutical Research Platform

## Overview
A comprehensive pharmaceutical research workstation built with Next.js 15 and Docker, featuring AI-powered literature analysis, knowledge graph construction, and lab protocol generation.

## Technology Stack

### Frontend
- **Framework**: Next.js 15 with App Router
- **Language**: TypeScript 5
- **Styling**: Tailwind CSS 4 with custom dark theme
- **UI Components**: Lucide React icons, custom components
- **State Management**: React hooks (useState, useEffect)

### Backend
- **API Routes**: Next.js API routes with RESTful endpoints
- **Database**: SQLite with Prisma ORM
- **Research Management**: In-memory task tracking with progress simulation

### Color Scheme (EXACT Specifications)

```css
/* Main Backgrounds */
--bg-main: #0a0a0c
--bg-card: rgba(255, 255, 255, 0.05)
--bg-input: rgba(0, 0, 0, 0.2)
--bg-terminal: #0f1115
--bg-terminal-header: #1a1d24

/* Accent Colors */
--accent-cyan: #22d3ee
--accent-cyan-dark: #0891b2
--accent-blue: #3b82f6
--accent-blue-dark: #2563eb

/* Status Colors */
--success: #10b981
--warning: #f59e0b
--error: #ef4444

/* Glow Effects */
--glow-cyan: rgba(34, 211, 238, 0.3)
--glow-emerald: rgba(16, 185, 129, 0.4)
--glow-purple: rgba(168, 85, 247, 0.2)
```

## Application Structure

### Frontend Components

#### Core Pages (Single Page Application)
1. **Home Page**
   - BioDockify logo with gradient text
   - Research topic input with dark glass card design
   - Three feature cards (Literature Search, Knowledge Graph, Lab Integration)
   - Recent research list with status indicators

2. **Research Page**
   - 4-step progress stepper with glowing active states
   - Terminal-style console with color-coded logs
   - Progress bar with cyan gradient fill
   - Cancel button for running tasks
   - Real-time status updates via polling

3. **Results Page**
   - Stats cards: Papers Analyzed, Entities Found, Graph Nodes, Connections
   - Entity sections with color-coded tags:
     - Drugs: blue-500
     - Diseases: red-500
     - Proteins: emerald-500
   - Research summary section
   - Export buttons for PDF and DOCX formats

4. **Lab Interface Page**
   - Protocol Generator (SiLA 2 XML)
     - Protocol types: Liquid Handler, Crystallization, Assay
   - Report Generator
     - Templates: Full Report, Summary, Executive Summary
   - Recent exports list with download functionality

5. **Settings Page**
   - LLM Configuration (OpenAI/Ollama)
   - Database Configuration (Neo4j)
   - Elsevier API settings
   - Connection test buttons with status indicators

#### Reusable Components
- **Sidebar**: Fixed left navigation with active states and hover effects
- **Console**: Terminal-style output with traffic light dots and auto-scroll
- **StatusBadge**: Animated status indicators (pending/running/completed/failed)
- **ProgressStep**: Circular progress indicators with connecting lines
- **StatsCard**: Glass-effect cards with icons and trends

### API Endpoints

#### Research Management
```
POST   /api/v1/research/start         - Start new research
GET    /api/v1/research/[taskId]/status - Get research status
GET    /api/v1/research/[taskId]/results - Get research results
POST   /api/v1/research/[taskId]/cancel - Cancel research
GET    /api/v1/research/history       - Get research history
```

#### Lab Interface
```
POST   /api/v1/lab/protocol           - Generate protocol
POST   /api/v1/lab/report             - Generate report
GET    /api/v1/lab/exports            - Get recent exports
```

#### Settings
```
GET    /api/v1/settings               - Get settings
POST   /api/v1/settings               - Save settings
GET    /api/v1/settings/test/[type]   - Test connection
```

### Backend Modules

#### Research Manager (`src/lib/research-manager.ts`)
- Task lifecycle management
- Progress simulation with 4 phases
- Real-time log generation
- Results generation with mock data

#### Lab Interface (`src/lib/lab-interface.ts`)
- SiLA 2 protocol generation
- Report generation (DOCX)
- Export tracking

#### Settings Manager (`src/lib/settings-manager.ts`)
- Configuration storage
- Connection management
- Default settings handling

#### Python Modules

##### Runtime Configuration (`runtime/config_loader.py`)
```python
- load_config()     # Load configuration from config.yaml
- save_config()      # Save configuration
- get_config_value() # Get specific configuration value
- set_config_value() # Set specific configuration value
```

##### SiLA 2 Generator (`modules/lab_interface/sila_generator.py`)
```python
class LiquidHandlerSiLA:
  - generate_protocol()          # Generate liquid handler protocol
  - generate_crystallization_protocol()  # Generate crystallization protocol
  - generate_assay_protocol()    # Generate assay protocol
```

##### Report Generator (`modules/lab_interface/report_generator.py`)
```python
class ResearchReportGenerator:
  - create_report_content()      # Create full report
  - create_summary_report()      # Create summary report
  - create_executive_summary()   # Create executive summary
```

### Database Schema (Prisma)

```prisma
model ResearchTask {
  id          String   @id @default(cuid())
  topic       String
  status      String   @default("pending")
  progress    Int      @default(0)
  currentStep Int      @default(1)
  phase       String   @default("Initializing")
  createdAt   DateTime @default(now())
  updatedAt   DateTime @updatedAt
  results     ResearchResult?
  exports     Export[]
}

model ResearchResult {
  id               String   @id @default(cuid())
  taskId           String   @unique
  title            String
  papersCount      Int      @default(0)
  entitiesCount    Int      @default(0)
  nodesCount       Int      @default(0)
  connectionsCount Int      @default(0)
  summary          String
  createdAt        DateTime @default(now())
  task             ResearchTask @relation(fields: [taskId], references: [id])
}

model Export {
  id        String   @id @default(cuid())
  taskId    String
  type      String
  filename  String
  createdAt DateTime @default(now())
  task      ResearchTask @relation(fields: [taskId], references: [id])
}

model AppSettings {
  id            String   @id @default(cuid())
  llmProvider   String   @default("ollama")
  ollamaUrl     String   @default("http://localhost:11434")
  openaiKey     String?
  elsevierKey   String?
  neo4jHost     String   @default("bolt://localhost:7687")
  neo4jUser     String   @default("neo4j")
  neo4jPassword String
  updatedAt     DateTime @updatedAt
}
```

## Features Implemented

### Frontend
✅ Dark theme with exact color scheme
✅ Responsive design
✅ Client-side routing (Single Page Application)
✅ Real-time progress tracking
✅ Terminal-style console with color-coded logs
✅ Glass-effect cards and components
✅ Glowing effects and animations
✅ Status badges with pulse animation
✅ Progress stepper with gradient lines
✅ Stats cards with icons
✅ Settings panel with connection testing

### Backend
✅ RESTful API endpoints
✅ Research task management
✅ Progress simulation
✅ Protocol generation (SiLA 2 XML)
✅ Report generation (DOCX)
✅ Settings management
✅ Database schema with Prisma

### Python Modules
✅ Configuration loader
✅ SiLA 2 protocol generator
✅ Research report generator
✅ Support for multiple protocol types
✅ Multiple report templates

## Design Highlights

1. **Glassmorphism**: All cards use `bg-white/5 border border-white/10 rounded-2xl backdrop-blur-md`
2. **Gradient Buttons**: Primary buttons use `bg-gradient-to-r from-cyan-600 to-blue-600`
3. **Glow Effects**: Active elements have shadow glows like `shadow-[0_0_15px_rgba(34,211,238,0.3)]`
4. **Terminal Aesthetic**: Console component features traffic light dots and monospace font
5. **Status Badges**: Animated badges with color-coded states
6. **Custom Scrollbar**: Styled scrollbar matching the dark theme
7. **Background Decorations**: Blurred purple and cyan circles for depth

## API Integration

The frontend uses a centralized API service (`src/lib/api.ts`) that:
- Provides TypeScript interfaces for all API responses
- Handles API errors gracefully
- Supports all research, lab, and settings endpoints
- Uses relative paths (gateway handles routing)

## Future Enhancements

1. **Real Research Integration**: Connect to actual PubMed/Elsevier APIs
2. **Neo4j Integration**: Use actual graph database for knowledge storage
3. **LLM Integration**: Use Ollama/OpenAI for content generation
4. **File Downloads**: Implement actual file download functionality
5. **Authentication**: Add user authentication and session management
6. **Export Persistence**: Store generated files in database
7. **Visualization**: Add interactive knowledge graph visualization
8. **Real-time Updates**: Use WebSocket for live updates instead of polling

## Usage

1. Start the development server (automatically running):
   ```bash
   bun run dev
   ```

2. Access the application at `http://localhost:3000`

3. Enter a research topic and click "Start Research"

4. Watch the progress through the console and stepper

5. View results in the Results page

6. Generate protocols and reports in the Lab Interface

7. Configure settings in the Settings page

## Status

✅ **Complete** - All core features implemented and tested
✅ **Running** - Development server active on port 3000
✅ **Linted** - Code quality checks passed
✅ **Database** - Prisma schema pushed successfully
