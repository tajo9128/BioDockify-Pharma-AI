### text_editor
file read write patch with numbered lines
not code execution rejects binary
terminal (grep find sed) advance search/replace

#### text_editor:read
read file with numbered lines
args path line_from line_to (inclusive optional)
no range → first {{default_line_count}} lines
long lines cropped output may trim by token limit
read surrounding context before patching
usage:
~~~json
{
    ...
    "tool_name": "text_editor:read",
    "tool_args": {
        "path": "/path/file.py",
        "line_from": 1,
        "line_to": 50
    }
}
~~~

#### text_editor:write
create/overwrite file auto-creates dirs
args path content
usage:
~~~json
{
    ...
    "tool_name": "text_editor:write",
    "tool_args": {
        "path": "/path/file.py",
        "content": "import os\nprint('hello')\n"
    }
}
~~~

#### text_editor:patch
edit existing file. prefer patch_text; use edits only right after read for tiny line edits
args path plus exactly one of: patch_text string OR edits [{from to content}]
patch_text uses current file content, no prior read required
patch_text update-only forms:
- insert after anchor: @@ exact existing line then +new lines
- replace: use @@ line before target then -old +new, or @@ old target line then -same old target line +new
- do not repeat the same old line as both a space-context line and a -removed line
- context lines start with space, removals with -, additions with +
- use enough unique context; add @@ anchor when repeated text exists
edits legacy line mode: from/to inclusive, original line numbers from read, no overlaps
edits examples: {from:2 to:2 content:"x\n"} replace; {from:2 to:2} delete; {from:2 content:"x\n"} insert before
for edits, re-read after insert/delete or line-count-changing replace
ensure valid syntax in content (all braces brackets tags closed)
usage:
~~~json
{
    ...
    "tool_name": "text_editor:patch",
    "tool_args": {
        "path": "/path/file.py",
        "patch_text": "*** Begin Patch\n*** Update File: file.py\n@@ def run():\n+    print('ready')\n*** End Patch"
    }
}
~~~
