// Research manager module - handles research task state and progress simulation

interface ResearchTask {
  id: string;
  topic: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  currentStep: number;
  logs: string[];
  phase: string;
  createdAt: string;
  results?: any;
}

// In-memory storage for demo purposes (in production, use a database)
const researchTasks = new Map<string, ResearchTask>();
const taskIntervals = new Map<string, NodeJS.Timeout>();

// Start a new research task
export function startResearchTask(taskId: string, topic: string): void {
  const task: ResearchTask = {
    id: taskId,
    topic,
    status: 'running',
    progress: 0,
    currentStep: 1,
    logs: [
      `Started research on: ${topic}`,
      'Initializing literature search module...',
    ],
    phase: 'Literature Search',
    createdAt: new Date().toISOString(),
  };

  researchTasks.set(taskId, task);
  simulateProgress(taskId, topic);
}

// Get research task status
export function getResearchStatus(taskId: string): any {
  const task = researchTasks.get(taskId);

  if (!task) {
    return null;
  }

  return {
    taskId: task.id,
    status: task.status,
    progress: task.progress,
    currentStep: task.currentStep,
    logs: task.logs,
    phase: task.phase,
  };
}

// Get research results
export function getResearchResults(taskId: string): any {
  const task = researchTasks.get(taskId);

  if (!task || task.status !== 'completed') {
    return null;
  }

  return task.results;
}

// Cancel research task
export function cancelResearch(taskId: string): void {
  const interval = taskIntervals.get(taskId);
  if (interval) {
    clearInterval(interval);
    taskIntervals.delete(taskId);
  }

  const task = researchTasks.get(taskId);
  if (task) {
    task.status = 'cancelled';
    task.logs.push('Research cancelled by user');
    researchTasks.set(taskId, task);
  }
}

// Get research history
export function getResearchHistory(): any[] {
  const history = Array.from(researchTasks.values())
    .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
    .map(task => ({
      id: task.id,
      topic: task.topic,
      status: task.status,
      createdAt: task.createdAt,
    }));

  return history;
}

// Simulate research progress
function simulateProgress(taskId: string, topic: string): void {
  const phases = [
    {
      step: 1,
      phase: 'Literature Search',
      logs: [
        'Searching PubMed...',
        'Querying Elsevier database...',
        'Found 47 relevant papers',
        'Analyzing abstracts...',
        'Extracting key information...',
      ],
    },
    {
      step: 2,
      phase: 'Entity Extraction',
      logs: [
        'Extracting named entities...',
        'Identifying drugs...',
        'Identifying diseases...',
        'Identifying proteins...',
        'Validating entity relationships...',
      ],
    },
    {
      step: 3,
      phase: 'Knowledge Graph',
      logs: [
        'Building knowledge graph...',
        'Creating node relationships...',
        'Validating connections...',
        'Graph construction complete',
        'Optimizing graph structure...',
      ],
    },
    {
      step: 4,
      phase: 'Analysis',
      logs: [
        'Analyzing patterns...',
        'Generating insights...',
        'Preparing results...',
        'Analysis complete',
      ],
    },
  ];

  let currentPhase = 0;
  let logIndex = 0;

  const interval = setInterval(() => {
    const task = researchTasks.get(taskId);

    if (!task || task.status === 'cancelled') {
      clearInterval(interval);
      taskIntervals.delete(taskId);
      return;
    }

    if (currentPhase < phases.length) {
      const phase = phases[currentPhase];

      if (logIndex < phase.logs.length) {
        task.logs.push(phase.logs[logIndex]);
        task.phase = phase.phase;
        task.currentStep = phase.step;
        task.progress = Math.min(
          100,
          currentPhase * 25 + (logIndex / phase.logs.length) * 25
        );
        logIndex++;
        researchTasks.set(taskId, task);
      } else {
        currentPhase++;
        logIndex = 0;
      }
    } else {
      // Research complete
      task.status = 'completed';
      task.progress = 100;
      task.currentStep = 4;
      task.logs.push('Research completed successfully!');

      // Generate mock results
      task.results = {
        taskId,
        title: topic,
        stats: {
          papers: 47,
          entities: 128,
          nodes: 89,
          connections: 234,
        },
        entities: {
          drugs: ['Donepezil', 'Rivastigmine', 'Galantamine', 'Memantine', 'Tacrine'],
          diseases: ['Alzheimer\'s Disease', 'Dementia', 'Cognitive Decline', 'Memory Loss'],
          proteins: ['Amyloid-beta', 'Tau protein', 'ApoE4', 'Acetylcholinesterase', 'Butyrylcholinesterase'],
        },
        summary: `This research analyzed 47 scientific papers on ${topic}. The analysis identified 5 key drugs (Donepezil, Rivastigmine, Galantamine, Memantine, Tacrine), 4 disease conditions, and 5 protein targets. The knowledge graph reveals 234 significant relationships between these entities, providing insights into the current therapeutic landscape. Key findings include strong evidence supporting acetylcholinesterase inhibitors as first-line treatment, emerging research on amyloid-targeted therapies, and potential combination therapy approaches that warrant further investigation.`,
      };

      researchTasks.set(taskId, task);
      clearInterval(interval);
      taskIntervals.delete(taskId);
    }
  }, 1500);

  taskIntervals.set(taskId, interval);
}
