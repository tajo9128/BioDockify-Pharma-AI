export default async function registerPipelineSurface(canvas) {
  canvas.registerSurface({
    id: "research-pipeline",
    title: "Research Pipeline",
    icon: "account_tree",
    order: 5,
    modalPath: "/components/research-command-center/pipeline-dashboard.html",
  });
}
