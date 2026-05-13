export default async function registerAgentTasksSurface(canvas) {
  canvas.registerSurface({
    id: "agent-tasks",
    title: "Agent Tasks",
    icon: "psychology",
    order: 7,
    modalPath: "/components/agent-tasks/agent-tasks-panel.html",
    open() {},
    close() {},
  });
}
