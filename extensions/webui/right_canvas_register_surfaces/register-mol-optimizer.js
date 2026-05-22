export default async function registerMolOptimizerSurface(canvas) {
  canvas.registerSurface({
    id: "mol-optimizer",
    title: "Mol Optimizer",
    icon: "auto_fix_high",
    order: 27,
    modalPath: "/components/mol-optimizer/mol-optimizer.html",
  });
}
