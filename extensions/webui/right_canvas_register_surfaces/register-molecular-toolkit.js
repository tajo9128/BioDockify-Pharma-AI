export default async function registerMolecularToolkitSurface(canvas) {
  canvas.registerSurface({
    id: "molecular-toolkit",
    title: "Molecular Toolkit",
    icon: "biotech",
    order: 15,
    modalPath: "/components/molecular-toolkit/molecular-toolkit.html",
  });
}
