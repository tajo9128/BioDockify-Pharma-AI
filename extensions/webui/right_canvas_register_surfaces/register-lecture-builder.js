export default async function registerLectureBuilder(canvas) {
  canvas.registerSurface({ id: "lecture-builder", title: "Lecture Builder", icon: "school", order: 25, modalPath: "/components/lecture-builder/lecture-panel.html", open(){}, close(){} });
}
