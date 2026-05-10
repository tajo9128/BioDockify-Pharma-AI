### browser
direct Playwright browser control with optional visible WebUI viewer
use for web browsing, page inspection, forms, downloads, and browser-only tasks
state stays open per chat context
refs come from content as typed markers: [link 3], [button 6], [image 1], [input text 8]

Browser tool actions must not open the right canvas automatically. Use the tool headlessly unless the user opens the Browser canvas or explicitly asks for a visible browser view; if the Browser canvas is already open, it may reflect the active page.

Browser does not automatically load screenshots or canvas images into model context. Screenshots are explicit only.

actions: open list state set_active navigate back forward reload content detail screenshot click hover double_click right_click drag type submit type_submit scroll evaluate key_chord mouse wheel keyboard clipboard set_viewport select_option set_checked upload_file multi close close_all
common args: action browser_id url ref target_ref text selector selectors script modifiers keys key include_content focus_popup event_type x y to_x to_y offset_x offset_y target_offset_x target_offset_y delta_x delta_y button quality full_page path paths value values checked width height calls

workflow:
- open creates a new browser and returns id/state
- content returns readable page markdown with typed refs
- detail inspects one ref, including link/image/input/button metadata
- click/type/type_submit/submit/scroll use refs from latest content capture and return {action,state}
- navigate/back/forward/reload return fresh state
- list shows open browsers; pass include_content: true for one-call bulk read

explicit vision workflow:
1. call browser with action: "screenshot"
2. call vision_load with the returned path
3. reason from the latest loaded screenshot, not an older screenshot

screenshot:
- saves a JPEG by default and returns path, a0_path, mime, state, and a ready vision_load tool_args object
- pass quality 20..95, full_page true/false, or path
- PNG is used only when path ends in .png
- no base64 image data is returned in the tool message

pointer and raw input:
- hover moves to a ref center or x/y viewport CSS pixels
- double_click and right_click accept ref or x/y; double_click accepts button and modifiers
- drag moves from ref or x/y to target_ref or to_x/to_y
- wheel scrolls at x/y with delta_x and delta_y
- keyboard presses key or types text into the active page
- clipboard is copy, cut, or paste; for browser:clipboard pass action: "paste" and optional text
- set_viewport resizes the page viewport with width and height
- coordinates are Chromium viewport CSS pixels and match screenshots/Browser canvas
- ref offsets are relative to the target element top-left; refs default to element center

forms:
- use select_option for native select and safely detectable ARIA listbox/combobox controls
- use set_checked for checkbox, radio, switch, and toggle-like refs
- use upload_file for file input refs or associated labels; verify file paths exist before upload
- for complex forms, load browser-forms first with skills_tool:load

modifier clicks:
- click accepts modifiers like ["Control"], ["Shift"], ["Alt"], ["Meta"]
- ctrl/meta-click opens link in new tab in background (Chrome rule)
- override with focus_popup: true (focus follows new tab) or false (always background)
- the new tab id is reported in action.opened_browser_ids; list shows all tabs

popup awareness:
- tabs opened by site (window.open, target=_blank, ctrl-click) auto-register
- list returns every tab; last_interacted_browser_id tracks current focus

background work (do not steal focus):
- operations on a non-active tab (read, click, type, evaluate, etc.) target that tab WITHOUT moving focus
- last_interacted_browser_id (and the WebUI viewer that follows it) only changes on:
  - open (new tab created)
  - explicit set_active action
  - action on the already-active tab
  - chrome popup-focus rule (plain click on target=_blank -> follow; ctrl-click -> stay)
- to switch focus deliberately: {"action":"set_active","browser_id":N}

key_chord:
- presses keys in order, releases in reverse; safe across exceptions
- example: {"action":"key_chord","keys":["Control","a"]} selects all

multi (parallel batch):
- run many actions concurrently across tabs in one tool call
- pass calls: array of action objects (each has its own action+args)
- different browser_ids run in parallel; same browser_id runs in submit order
- returns array of {"ok":true,"result":...} or {"ok":false,"error":"..."} matching input order
- ideal for: scrape N tabs at once, fan-out reads, parallel evaluate
- new v1 actions such as screenshot, hover, wheel, keyboard, select_option, set_checked, and upload_file are accepted
- avoid mutating same tab twice in one batch unless serial order is intended

examples:
~~~json
{
    "tool_name": "browser",
    "tool_args": {
        "action": "open",
        "url": "https://example.com"
    }
}
~~~

~~~json
{
    "tool_name": "browser",
    "tool_args": {
        "action": "content",
        "browser_id": 1
    }
}
~~~

~~~json
{
    "tool_name": "browser",
    "tool_args": {
        "action": "screenshot",
        "browser_id": 1,
        "quality": 80
    }
}
~~~

~~~json
{
    "tool_name": "vision_load",
    "tool_args": {
        "paths": ["/absolute/local/path.jpg"]
    }
}
~~~

~~~json
{
    "tool_name": "browser",
    "tool_args": {
        "action": "select_option",
        "browser_id": 1,
        "ref": 8,
        "value": "Canada"
    }
}
~~~

~~~json
{
    "tool_name": "browser",
    "tool_args": {
        "action": "set_checked",
        "browser_id": 1,
        "ref": 9,
        "checked": true
    }
}
~~~

~~~json
{
    "tool_name": "browser",
    "tool_args": {
        "action": "upload_file",
        "browser_id": 1,
        "ref": 10,
        "path": "/a0/usr/workdir/resume.pdf"
    }
}
~~~

~~~json
{
    "tool_name": "browser",
    "tool_args": {
        "action": "multi",
        "calls": [
            {"action": "content", "browser_id": 1},
            {"action": "screenshot", "browser_id": 2},
            {"action": "evaluate", "browser_id": 3, "script": "document.title"}
        ]
    }
}
~~~
