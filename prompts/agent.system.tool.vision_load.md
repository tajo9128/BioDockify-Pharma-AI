### vision_load
load and analyze images
args: `action` (load, describe, analyze), `image_path`
optional: `question`
example:
~~~json
{
  "thoughts": ["I need to analyze this image."],
  "headline": "Loading image",
  "tool_name": "vision_load",
  "tool_args": {
    "action": "load",
    "image_path": "workdir/compound.png"
  }
}
~~~
