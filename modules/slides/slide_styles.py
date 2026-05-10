"""
Slide Styles - Pre-defined presentation themes and templates
"""

from typing import Dict, Any


# Pre-defined slide styles
SLIDE_STYLES = {
    "academic": {
        "name": "Academic",
        "description": "Clean, professional style for conferences and seminars",
        "colors": {
            "background": "#FFFFFF",
            "title": "#1a365d",
            "text": "#2d3748",
            "accent": "#3182ce"
        },
        "fonts": {
            "title": "Georgia, serif",
            "body": "Arial, sans-serif"
        },
        "layout": "classic"
    },
    "modern": {
        "name": "Modern",
        "description": "Sleek design with gradients and contemporary typography",
        "colors": {
            "background": "#0f172a",
            "title": "#f8fafc",
            "text": "#e2e8f0",
            "accent": "#38bdf8"
        },
        "fonts": {
            "title": "Inter, sans-serif",
            "body": "Inter, sans-serif"
        },
        "layout": "modern"
    },
    "minimal": {
        "name": "Minimal",
        "description": "Simple white background with clean typography",
        "colors": {
            "background": "#FFFFFF",
            "title": "#111827",
            "text": "#374151",
            "accent": "#6366f1"
        },
        "fonts": {
            "title": "Helvetica, sans-serif",
            "body": "Helvetica, sans-serif"
        },
        "layout": "minimal"
    },
    "pharma": {
        "name": "Pharmaceutical",
        "description": "Professional style for pharmaceutical and biotech presentations",
        "colors": {
            "background": "#f0f9ff",
            "title": "#0c4a6e",
            "text": "#1e3a5f",
            "accent": "#0891b2"
        },
        "fonts": {
            "title": "Roboto, sans-serif",
            "body": "Open Sans, sans-serif"
        },
        "layout": "corporate"
    }
}


def get_style_template(style_name: str) -> Dict[str, Any]:
    """
    Get the template configuration for a given style.
    
    Args:
        style_name: Name of the style (academic, modern, minimal, pharma)
    
    Returns:
        Style configuration dict
    """
    return SLIDE_STYLES.get(style_name, SLIDE_STYLES["academic"])


def get_available_styles() -> list:
    """Get list of available style names."""
    return list(SLIDE_STYLES.keys())


def get_style_css(style_name: str) -> str:
    """
    Generate CSS for a slide style.
    
    Args:
        style_name: Name of the style
    
    Returns:
        CSS string for the style
    """
    style = get_style_template(style_name)
    colors = style["colors"]
    fonts = style["fonts"]
    
    return f"""
    .slide {{
        background-color: {colors['background']};
        color: {colors['text']};
        font-family: {fonts['body']};
        padding: 40px;
        min-height: 100vh;
        box-sizing: border-box;
    }}
    
    .slide-title {{
        color: {colors['title']};
        font-family: {fonts['title']};
        font-size: 2.5em;
        font-weight: 700;
        margin-bottom: 20px;
    }}
    
    .slide-content {{
        font-size: 1.4em;
        line-height: 1.6;
    }}
    
    .slide-content ul {{
        list-style-type: disc;
        margin-left: 30px;
    }}
    
    .slide-content li {{
        margin-bottom: 10px;
    }}
    
    .slide-accent {{
        color: {colors['accent']};
    }}
    
    .slide-footer {{
        position: absolute;
        bottom: 20px;
        font-size: 0.9em;
        color: {colors['text']};
        opacity: 0.7;
    }}
    """


def generate_slide_html(slide: Dict[str, Any], style_name: str = "academic") -> str:
    """
    Generate HTML for a single slide.
    
    Args:
        slide: Slide data with title, content, type
        style_name: Style to apply
    
    Returns:
        HTML string for the slide
    """
    style = get_style_template(style_name)
    slide_type = slide.get("type", "content")
    
    # Convert content to HTML list if it contains newlines
    content = slide.get("content", "")
    if "\n" in content:
        items = [f"<li>{line.strip()}</li>" for line in content.split("\n") if line.strip()]
        content_html = f"<ul>{''.join(items)}</ul>"
    else:
        content_html = f"<p>{content}</p>"
    
    # Generate slide HTML
    if slide_type == "title":
        return f"""
        <div class="slide slide-title-page">
            <h1 class="slide-title">{slide.get('title', '')}</h1>
            <p class="slide-subtitle">{slide.get('content', '')}</p>
        </div>
        """
    elif slide_type == "references":
        return f"""
        <div class="slide slide-references">
            <h2 class="slide-title">{slide.get('title', 'References')}</h2>
            <div class="slide-content references-list">
                {content_html}
            </div>
        </div>
        """
    else:
        return f"""
        <div class="slide">
            <h2 class="slide-title">{slide.get('title', '')}</h2>
            <div class="slide-content">
                {content_html}
            </div>
            <div class="slide-footer">
                Slide {slide.get('index', '')}
            </div>
        </div>
        """


def generate_presentation_html(slides: list, style_name: str = "academic", title: str = "Presentation") -> str:
    """
    Generate complete HTML presentation.
    
    Args:
        slides: List of slide data dicts
        style_name: Style to apply
        title: Presentation title for HTML head
    
    Returns:
        Complete HTML document string
    """
    css = get_style_css(style_name)
    slides_html = "\n".join([generate_slide_html(s, style_name) for s in slides])
    
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        {css}
        
        @media print {{
            .slide {{
                page-break-after: always;
            }}
        }}
    </style>
</head>
<body>
    {slides_html}
</body>
</html>
"""
