export default async function registerLocalLlmSurface(canvas) {
  canvas.registerSurface({
    id: "local_llm",
    title: "BioDockify AI Engine",
    icon: "psychology",
    order: 70,
    modalPath: "/components/local_llm/local_llm.html",
  });
}
