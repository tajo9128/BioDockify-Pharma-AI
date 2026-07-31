export default async function registerAdmetPredictSurface(canvas) {
  canvas.registerSurface({
    id: "admet-predict",
    title: "ADMET Prediction",
    icon: "vaccines",
    order: 15.5,
    modalPath: "/components/admet-predict/admet-predict-panel.html",
  });
}
