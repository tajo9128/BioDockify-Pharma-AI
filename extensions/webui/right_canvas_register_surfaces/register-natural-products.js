export default async function registerNaturalProductsSurface(canvas) {
  canvas.registerSurface({
    id: "natural-products",
    title: "Natural Products",
    icon: "eco",
    order: 30,
    modalPath: "/components/natural-products/natural-products.html",
  });
}
