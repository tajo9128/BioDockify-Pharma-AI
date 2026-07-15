export default async function registerFormulationSurface(canvas) {
  canvas.registerSurface({
    id: "formulation",
    title: "Formulation",
    icon: "science",
    order: 27,
    modalPath: "/components/formulation/formulation.html",
  });
}
