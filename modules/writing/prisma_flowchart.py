"""PRISMA 2020 Flowchart Generator — systematic review workflow visualization."""
import logging

log = logging.getLogger("prisma")


def generate_prisma(
    identification: int = 0,
    screening: int = 0,
    eligibility: int = 0,
    included: int = 0,
    exclusion_reasons: dict = None,
    search_query: str = "",
    topic: str = "Systematic Review"
) -> dict:
    """
    Generate PRISMA 2020 flowchart data + Mermaid diagram + HTML.

    Returns structured data for rendering the PRISMA flowchart.
    """
    exclusion_reasons = exclusion_reasons or {}
    duplicates = max(0, identification - screening) if identification else 0
    excluded_screening = max(0, screening - eligibility) if screening else 0
    excluded_eligibility = max(0, eligibility - included) if eligibility else 0

    # Build Mermaid flowchart
    mermaid = _build_mermaid(
        identification, screening, duplicates,
        eligibility, excluded_screening,
        included, excluded_eligibility,
        exclusion_reasons, topic
    )

    # Build HTML version
    html = _build_html(
        identification, screening, duplicates,
        eligibility, excluded_screening,
        included, excluded_eligibility,
        exclusion_reasons, topic, search_query
    )

    # Build structured data for rendering
    data = {
        "topic": topic,
        "search_query": search_query,
        "stages": [
            {
                "stage": "Identification",
                "label": "Records identified",
                "description": f"Records identified from databases and registers",
                "count": identification,
                "icon": "search"
            },
            {
                "stage": "Screening",
                "label": "Records screened",
                "description": f"Records after {duplicates} duplicates removed",
                "count": screening,
                "excluded": {"Duplicates removed": duplicates} if duplicates else {},
                "icon": "filter_list"
            },
            {
                "stage": "Eligibility",
                "label": "Full-text assessed",
                "description": f"Full-text articles assessed for eligibility",
                "count": eligibility,
                "excluded": {"Excluded at screening": excluded_screening} if excluded_screening else {},
                "icon": "description"
            },
            {
                "stage": "Included",
                "label": "Studies included",
                "description": f"Studies included in qualitative/quantitative synthesis",
                "count": included,
                "excluded": exclusion_reasons if exclusion_reasons else {"Excluded at eligibility": excluded_eligibility} if excluded_eligibility else {},
                "icon": "check_circle"
            }
        ],
        "summary": {
            "total_identified": identification,
            "total_screened": screening,
            "total_assessed": eligibility,
            "total_included": included,
            "inclusion_rate": f"{round(100 * included / max(identification, 1), 1)}%"
        }
    }

    return {
        "mermaid": mermaid,
        "html": html,
        "data": data,
    }


def _build_mermaid(ident, screen, dup, elig, scr_ex, incl, elig_ex, reasons, topic):
    m = "flowchart TD\n"
    m += f"    A[\"<b>Identification</b><br/>Records identified (n={ident})\"] --> B\n"
    m += f"    B[\"<b>Screening</b><br/>Records screened (n={screen})\"] --> C\n"
    if dup:
        m += f"    A --> A1[\"Duplicates removed (n={dup})\"]\n    style A1 fill:#ffcccc\n"
    if scr_ex:
        m += f"    B --> B1[\"Excluded at screening (n={scr_ex})\"]\n    style B1 fill:#ffcccc\n"
    m += f"    C[\"<b>Eligibility</b><br/>Full-text assessed (n={elig})\"] --> D\n"
    if elig_ex or reasons:
        total_elig_excl = sum(reasons.values()) if reasons else elig_ex
        reasons_str = "<br/>".join(f"{k}: n={v}" for k, v in (reasons or {}).items()) if reasons else f"Excluded (n={elig_ex})"
        m += f"    C --> C1[\"{reasons_str}\"]\n    style C1 fill:#ffcccc\n"
    m += f"    D[\"<b>Included</b><br/>Studies included (n={incl})\"]\n"
    m += f"    style A fill:#e3f2fd\n    style B fill:#e3f2fd\n    style C fill:#e3f2fd\n    style D fill:#c8e6c9\n"
    return m


def _build_html(ident, screen, dup, elig, scr_ex, incl, elig_ex, reasons, topic, query):
    html = f"""<div class="prisma-chart">
<style>
.prisma-chart {{ font-family: system-ui; max-width: 500px; margin: 0 auto; }}
.prisma-box {{ border: 2px solid #1976d2; border-radius: 8px; padding: 10px; margin: 4px 0; text-align: center; }}
.prisma-box.final {{ border-color: #388e3c; background: #e8f5e9; }}
.prisma-box .count {{ font-size: 1.4rem; font-weight: 700; }}
.prisma-box .label {{ font-size: 0.75rem; color: #666; }}
.prisma-exclude {{ border: 1px solid #e53935; border-radius: 4px; background: #ffebee; padding: 6px; margin: 2px 0; font-size: 0.7rem; color: #c62828; text-align: center; }}
.prisma-arrow {{ text-align: center; color: #999; font-size: 1.2rem; margin: 2px 0; }}
</style>
<h4 style="text-align:center;margin:0 0 8px">{topic}</h4>
<div class="prisma-box"><div class="count">n = {ident}</div><div class="label">Records identified from databases</div></div>
"""
    if dup:
        html += f'<div class="prisma-exclude">Duplicates removed (n = {dup})</div>\n'
    html += f'<div class="prisma-arrow">⬇</div>\n'
    html += f'<div class="prisma-box"><div class="count">n = {screen}</div><div class="label">Records screened</div></div>\n'
    if scr_ex:
        html += f'<div class="prisma-exclude">Records excluded at screening (n = {scr_ex})</div>\n'
    html += f'<div class="prisma-arrow">⬇</div>\n'
    html += f'<div class="prisma-box"><div class="count">n = {elig}</div><div class="label">Full-text articles assessed</div></div>\n'
    if reasons:
        for reason, count in reasons.items():
            html += f'<div class="prisma-exclude">{reason} (n = {count})</div>\n'
    elif elig_ex:
        html += f'<div class="prisma-exclude">Excluded (n = {elig_ex})</div>\n'
    html += f'<div class="prisma-arrow">⬇</div>\n'
    html += f'<div class="prisma-box final"><div class="count">n = {incl}</div><div class="label">Studies included in review</div></div>\n'
    if query:
        html += f'<div style="font-size:0.65rem;color:#999;margin-top:8px;text-align:center">Search: {query}</div>\n'
    html += '</div>'
    return html
