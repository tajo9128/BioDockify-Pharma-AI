export default async function registerMolSimilarity(canvas) {
  canvas.registerSurface({ id: "mol-similarity", title: "Similarity", icon: "share", order: 28, modalPath: "/components/mol-similarity/similarity-panel.html", open(){}, close(){} });
}
