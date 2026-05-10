import re
from pathlib import Path
from typing import Optional

class LaTeXExporter:
    """
    Exports reports to LaTeX using a template-based approach.
    """
    
    def __init__(self, template_path: str = "modules/publication/templates/academic_report.tex"):
        self.template_path = Path(template_path)
        if not self.template_path.exists():
            raise FileNotFoundError(f"Template not found at: {self.template_path}")
            
        with open(self.template_path, 'r', encoding="utf-8") as f:
            self.template = f.read()

    def generate_latex(self, 
                       title: str, 
                       author: str, 
                       affiliation: str, 
                       abstract: str, 
                       content_markdown: str,
                       output_path: Optional[str] = None) -> str:
        """
        Generates LaTeX source code by filling the template.
        Returns the generated LaTeX string.
        """
        
        # 1. Convert Markdown basics to LaTeX
        latex_content = self._markdown_to_latex(content_markdown)
        
        # 2. Fill Template
        rendered = self.template
        rendered = rendered.replace("{{ title }}", self._sanitize(title))
        rendered = rendered.replace("{{ author }}", self._sanitize(author))
        rendered = rendered.replace("{{ affiliation }}", self._sanitize(affiliation))
        rendered = rendered.replace("{{ abstract }}", self._sanitize(abstract))
        rendered = rendered.replace("{{ content }}", latex_content)
        
        # 3. Save if requested
        if output_path:
            out = Path(output_path)
            out.parent.mkdir(parents=True, exist_ok=True)
            with open(out, 'w', encoding="utf-8") as f:
                f.write(rendered)
                
        return rendered

    def _sanitize(self, text: str) -> str:
        """Escape LaTeX special characters."""
        chars = {
            "&": r"\&",
            "%": r"\%",
            "$": r"\$",
            "#": r"\#",
            "_": r"\_",
            "{": r"\{",
            "}": r"\}",
            "~": r"\textasciitilde{}",
            "^": r"\^{}",
        }
        pattern = re.compile('|'.join(re.escape(str(key)) for key in chars.keys()))
        return pattern.sub(lambda m: chars[m.group()], text)

    def _markdown_to_latex(self, text: str) -> str:
        """
        Simple Markdown to LaTeX converter.
        Handles: Headers, Bold, Italic, Lists.
        """
        lines = text.split('\n')
        latex_lines = []
        
        in_itemize = False
        in_enumerate = False
        
        for line in lines:
            line = line.strip()
            
            # Sanitization (basic, need to be careful not to break tags we add)
            # For now, let's sanitize strictly content, not structure markers
            # Ideally we'd tokenize. This is a naive MVP approach.
            
            # Headers
            if line.startswith('# '):
                line = f"\\section{{{self._sanitize(line[2:])}}}"
            elif line.startswith('## '):
                line = f"\\subsection{{{self._sanitize(line[3:])}}}"
            elif line.startswith('### '):
                line = f"\\subsubsection{{{self._sanitize(line[4:])}}}"
                
            # Lists (Unordered)
            elif line.startswith('- '):
                if not in_itemize:
                    latex_lines.append(r"\begin{itemize}")
                    in_itemize = True
                content = self._sanitize(line[2:])
                line = f"\\item {content}"
            else:
                if in_itemize and not line.startswith('- '):
                    latex_lines.append(r"\end{itemize}")
                    in_itemize = False
                    
            # Bold / Italic (Regex)
            # Bold **text** -> \textbf{text}
            line = re.sub(r'\*\*(.*?)\*\*', r'\\textbf{\1}', line)
            # Italic *text* -> \textit{text}
            line = re.sub(r'\*(.*?)\*', r'\\textit{\1}', line)

            # Paragraph breaks
            if line == "":
                line = r"\par"
                
            latex_lines.append(line)
            
        if in_itemize:
            latex_lines.append(r"\end{itemize}")
            
        return "\n".join(latex_lines)

if __name__ == "__main__":
    # Test
    exporter = LaTeXExporter()
    latex = exporter.generate_latex(
        title="Test Report",
        author="BioDockify AI",
        affiliation="Virtual Lab",
        abstract="This is a test abstract.",
        content_markdown="# Introduction\nThis is a **bold** statement.\n- Point 1\n- Point 2"
    )
    print(latex)
