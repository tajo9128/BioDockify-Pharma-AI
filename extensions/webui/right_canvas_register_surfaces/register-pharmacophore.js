export default async function registerPharmacophoreSurface(canvas) {
  canvas.registerSurface({
    id: "pharmacophore",
    title: "Pharmacophore",
    icon: "ads_click",
    order: 25,
    modalPath: "/components/pharmacophore/pharmacophore.html",
  });
}
