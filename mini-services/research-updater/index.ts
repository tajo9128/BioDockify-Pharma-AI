import { createServer } from 'http';
import { Server as SocketIOServer } from 'socket.io';

const PORT = 3003;
const httpServer = createServer();
const io = new SocketIOServer(httpServer, {
  cors: {
    origin: '*',
    methods: ['GET', 'POST']
  }
});

// Store active research tasks
const activeTasks = new Map<string, any>();

// Store connected clients
const connectedClients = new Map<string, any>();

console.log('🔌 Research Updater Service starting...');
console.log(`📡 WebSocket server will run on port ${PORT}`);

io.on('connection', (socket) => {
  const clientId = socket.id;
  console.log(`✅ Client connected: ${clientId}`);

  // Store client
  connectedClients.set(clientId, {
    socket,
    connectedAt: new Date().toISOString(),
    subscribedTasks: new Set<string>()
  });

  // Client subscribes to task updates
  socket.on('subscribe-task', (taskId) => {
    console.log(`📌 Client ${clientId} subscribed to task: ${taskId}`);
    const client = connectedClients.get(clientId);
    if (client) {
      client.subscribedTasks.add(taskId);

      // Send current task status if available
      const task = activeTasks.get(taskId);
      if (task) {
        socket.emit('task-update', task);
      }
    }
  });

  // Client unsubscribes from task updates
  socket.on('unsubscribe-task', (taskId) => {
    console.log(`📌 Client ${clientId} unsubscribed from task: ${taskId}`);
    const client = connectedClients.get(clientId);
    if (client) {
      client.subscribedTasks.delete(taskId);
    }
  });

  // Client requests current status
  socket.on('get-task-status', (taskId) => {
    const task = activeTasks.get(taskId);
    if (task) {
      socket.emit('task-status', task);
    } else {
      socket.emit('task-status', {
        taskId,
        status: 'not_found',
        message: 'Task not found'
      });
    }
  });

  // Handle disconnection
  socket.on('disconnect', () => {
    console.log(`❌ Client disconnected: ${clientId}`);
    connectedClients.delete(clientId);
  });

  // Send welcome message
  socket.emit('connected', {
    message: 'Connected to Research Updater Service',
    clientId,
    timestamp: new Date().toISOString()
  });
});

// Function to broadcast task updates to all subscribed clients
export function broadcastTaskUpdate(taskId: string, data: any) {
  const update = {
    taskId,
    ...data,
    timestamp: new Date().toISOString()
  };

  // Store task data
  activeTasks.set(taskId, update);

  // Broadcast to subscribed clients
  for (const [clientId, client] of connectedClients.entries()) {
    if (client.subscribedTasks.has(taskId)) {
      client.socket.emit('task-update', update);
    }
  }

  console.log(`📢 Broadcasted update for task ${taskId} to ${getSubscriberCount(taskId)} clients`);
}

// Function to update task progress
export function updateTaskProgress(taskId: string, progress: number, status: string, message: string) {
  const update = {
    progress,
    status,
    currentStep: message,
    timestamp: new Date().toISOString()
  };

  activeTasks.set(taskId, {
    ...activeTasks.get(taskId),
    ...update
  });

  // Broadcast to subscribed clients
  for (const [clientId, client] of connectedClients.entries()) {
    if (client.subscribedTasks.has(taskId)) {
      client.socket.emit('progress-update', update);
    }
  }

  console.log(`📊 Updated progress for task ${taskId}: ${progress}% - ${message}`);
}

// Helper function to count subscribers
function getSubscriberCount(taskId: string): number {
  let count = 0;
  for (const client of connectedClients.values()) {
    if (client.subscribedTasks.has(taskId)) {
      count++;
    }
  }
  return count;
}

// Export io instance for external use
export { io, activeTasks, connectedClients };

// Start server
httpServer.listen(PORT, () => {
  console.log(`\n✅ Research Updater Service is running`);
  console.log(`📡 WebSocket server listening on port ${PORT}`);
  console.log(`🔗 Clients can connect to: ws://localhost:${PORT}`);
  console.log(`⏰ Started at: ${new Date().toISOString()}\n`);
});

// Graceful shutdown
process.on('SIGINT', () => {
  console.log('\n🛑 Shutting down Research Updater Service...');
  io.close();
  httpServer.close();
  console.log('✅ Service stopped gracefully');
  process.exit(0);
});

// Keep process alive
setInterval(() => {
  const stats = {
    connectedClients: connectedClients.size,
    activeTasks: activeTasks.size,
    uptime: process.uptime(),
    memory: process.memoryUsage()
  };

  console.log(`📊 Service Stats: ${stats.connectedClients} clients, ${stats.activeTasks} tasks`);
}, 300000); // Every 5 minutes
