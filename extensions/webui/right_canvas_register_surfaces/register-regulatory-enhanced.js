export default async function registerRegulatoryEnhancedSurface(canvas) {
  canvas.registerSurface({
    id: "regulatory-enhanced",
    title: "Regulatory Affairs",
    icon: "gavel",
    order: 31,
    modalPath: "/components/regulatory-enhanced/regulatory-enhanced.html",
  });
}
