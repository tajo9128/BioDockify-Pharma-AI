### slides_pptx
generate PowerPoint presentations from SVG slides
args:
- `action` (one of: convert, design)
- `svg_dir` (directory containing SVG files)
- `output_name` (optional: output filename)
returns PPTX file path
example:
~~~json
{
  "thoughts": ["I need to create a presentation from these slides."],
  "headline": "Generating PPTX presentation",
  "tool_name": "slides_pptx",
  "tool_args": {
    "action": "convert",
    "svg_dir": "workdir/presentation/",
    "output_name": "research_talk"
  }
}
~~~
