export default async function registerBenchmarkSurface(canvas) {
  canvas.registerSurface({
    id: "benchmark",
    title: "Benchmark",
    icon: "monitoring",
    order: 65,
    modalPath: "/components/benchmark/benchmark.html",
  });
}
