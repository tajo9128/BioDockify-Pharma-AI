export default async function registerAdmetPredictSurface(canvas) {
  canvas.registerSurface({
    id: "admet-predict",
    title: "ADMET Prediction",
    icon: "biotech",
    order: 16,
    modalPath: "/components/admet-predict/admet-predict-panel.html",
  });
}
