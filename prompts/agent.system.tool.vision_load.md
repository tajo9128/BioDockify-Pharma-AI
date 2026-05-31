### vision_load
load and analyze images
args:
- `action` (one of: load, describe, analyze)
- `image_path` (path to image file)
- `question` (optional: question about the image)
returns image description, analysis results
example:
~~~json
{
  "thoughts": ["I need to analyze this image."],
  "headline": "Loading image for analysis",
  "tool_name": "vision_load",
  "tool_args": {
    "action": "load",
    "image_path": "workdir/compound_structure.png"
  }
}
~~~
