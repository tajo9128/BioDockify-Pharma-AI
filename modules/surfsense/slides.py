import os
import asyncio
from typing import List, Dict
from pathlib import Path
from playwright.async_api import async_playwright

SLIDE_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{
            margin: 0;
            padding: 0;
            width: 1920px;
            height: 1080px;
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            color: white;
            font-family: 'Segoe UI', sans-serif;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            overflow: hidden;
        }}
        .container {{
            width: 80%;
            height: 80%;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 20px;
            padding: 60px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 20px 50px rgba(0,0,0,0.5);
        }}
        h1 {{
            font-size: 72px;
            margin-bottom: 40px;
            background: linear-gradient(to right, #4ade80, #3b82f6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-align: left;
        }}
        ul {{
            font-size: 42px;
            line-height: 1.6;
            margin-left: 40px;
        }}
        li {{
            margin-bottom: 20px;
            color: #cbd5e1;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{title}</h1>
        <ul>
            {content}
        </ul>
    </div>
</body>
</html>
"""

async def generate_slides(markdown_text: str, theme: str = "default", output_dir: str = "slides") -> List[str]:
    """
    Parses markdown and generates slide images using Playwright.
    Input markdown expected format:
    # Title
    - Bullet 1
    - Bullet 2
    ---
    # Next Slide
    ...
    
    Returns list of paths to generated slide images.
    """
    os.makedirs(output_dir, exist_ok=True)
    slides_data = []
    
    # 1. Parse Markdown into slides
    current_slide = {"title": "Summary", "bullets": []}
    
    for line in markdown_text.split('\n'):
        line = line.strip()
        if not line: continue
        
        if line.startswith('---'):
            slides_data.append(current_slide)
            current_slide = {"title": "", "bullets": []}
        elif line.startswith('# '):
            if current_slide["title"] and not current_slide["bullets"]:
                current_slide["title"] = line[2:]
            elif current_slide["bullets"]:
                slides_data.append(current_slide)
                current_slide = {"title": line[2:], "bullets": []}
            else:
                current_slide["title"] = line[2:]
        elif line.startswith('- ') or line.startswith('* '):
            current_slide["bullets"].append(line[2:])
            
    if current_slide["title"] or current_slide["bullets"]:
        slides_data.append(current_slide)
        
    generated_paths = []
    
    # 2. Render each slide
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1920, "height": 1080})
        
        for idx, slide in enumerate(slides_data):
            bullets_html = "\n".join([f"<li>{b}</li>" for b in slide["bullets"]])
            html_content = SLIDE_TEMPLATE.format(title=slide["title"], content=bullets_html)
            
            # Write temp html
            temp_html_path = Path(output_dir) / f"temp_{idx}.html"
            with open(temp_html_path, "w", encoding="utf-8") as f:
                f.write(html_content)
                
            await page.goto(f"file://{temp_html_path.absolute()}")
            output_image_path = Path(output_dir) / f"slide_{idx:03d}.png"
            await page.screenshot(path=str(output_image_path))
            
            generated_paths.append(str(output_image_path.absolute()))
            
            # Cleanup html (Fix for Bug #8)
            try:
                os.remove(temp_html_path)
            except Exception as e:
                import logging
                logging.getLogger("surfsense.slides").debug(f"Failed to remove temp file {temp_html_path}: {e}")
                
        await browser.close()
        
    return generated_paths

