from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether, PageBreak
)
from reportlab.platypus.flowables import Flowable
from reportlab.lib.colors import HexColor
import datetime

# ── Colour palette ──────────────────────────────────────────────
C_DARK       = HexColor('#1A1A2E')
C_ACCENT     = HexColor('#16213E')
C_BLUE       = HexColor('#0F3460')
C_RED        = HexColor('#C0392B')
C_AMBER      = HexColor('#D4860A')
C_GREEN      = HexColor('#1E7E50')
C_RED_LIGHT  = HexColor('#FDECEA')
C_AMBER_LIGHT= HexColor('#FEF9E7')
C_GREEN_LIGHT= HexColor('#EAFAF1')
C_BLUE_LIGHT = HexColor('#EBF5FB')
C_GRAY_LIGHT = HexColor('#F5F5F5')
C_GRAY_MID   = HexColor('#CCCCCC')
C_GRAY_DARK  = HexColor('#555555')
C_WHITE      = colors.white
C_SCORE_BG   = HexColor('#F0F4FF')

W, H = A4
MARGIN = 18*mm

# ── Styles ───────────────────────────────────────────────────────
base = getSampleStyleSheet()

def style(name, parent='Normal', **kw):
    s = ParagraphStyle(name, parent=base[parent], **kw)
    return s

S = {
    'cover_title': style('cover_title','Normal',
        fontSize=22, textColor=C_WHITE, leading=28, spaceAfter=6, fontName='Helvetica-Bold'),
    'cover_sub': style('cover_sub','Normal',
        fontSize=11, textColor=HexColor('#BDC3D0'), leading=16, spaceAfter=4, fontName='Helvetica'),
    'cover_meta': style('cover_meta','Normal',
        fontSize=9, textColor=HexColor('#8899AA'), leading=13, fontName='Helvetica'),
    'section': style('section','Normal',
        fontSize=13, textColor=C_WHITE, leading=17, fontName='Helvetica-Bold'),
    'h2': style('h2','Normal',
        fontSize=10.5, textColor=C_DARK, leading=14, spaceAfter=3, fontName='Helvetica-Bold'),
    'body': style('body','Normal',
        fontSize=9, textColor=C_DARK, leading=13.5, spaceAfter=4, fontName='Helvetica'),
    'body_sm': style('body_sm','Normal',
        fontSize=8.5, textColor=C_GRAY_DARK, leading=12.5, fontName='Helvetica'),
    'fit': style('fit','Normal',
        fontSize=8.5, textColor=HexColor('#2C3E50'), leading=12.5,
        leftIndent=4, rightIndent=4, fontName='Helvetica-Oblique'),
    'tier_label': style('tier_label','Normal',
        fontSize=13, textColor=C_WHITE, leading=16, fontName='Helvetica-Bold'),
    'tier_desc': style('tier_desc','Normal',
        fontSize=9, textColor=C_WHITE, leading=13, fontName='Helvetica'),
    'col_hdr': style('col_hdr','Normal',
        fontSize=7.5, textColor=C_WHITE, leading=10, fontName='Helvetica-Bold', alignment=TA_CENTER),
    'cell': style('cell','Normal',
        fontSize=7.5, textColor=C_DARK, leading=10.5, fontName='Helvetica'),
    'cell_sm': style('cell_sm','Normal',
        fontSize=7, textColor=C_GRAY_DARK, leading=10, fontName='Helvetica'),
    'score_dim': style('score_dim','Normal',
        fontSize=8.5, textColor=C_DARK, leading=12, fontName='Helvetica-Bold'),
    'score_txt': style('score_txt','Normal',
        fontSize=8.5, textColor=C_DARK, leading=12, fontName='Helvetica'),
    'footer': style('footer','Normal',
        fontSize=7.5, textColor=HexColor('#999999'), leading=10, fontName='Helvetica'),
    'disclaimer': style('disclaimer','Normal',
        fontSize=8, textColor=C_GRAY_DARK, leading=11.5, fontName='Helvetica-Oblique'),
}

# ── Custom cover banner ──────────────────────────────────────────
class ColorRect(Flowable):
    def __init__(self, width, height, fill_color, radius=4):
        Flowable.__init__(self)
        self.width = width
        self.height = height
        self.fill_color = fill_color
        self.radius = radius

    def draw(self):
        self.canv.setFillColor(self.fill_color)
        self.canv.roundRect(0, 0, self.width, self.height, self.radius, fill=1, stroke=0)

class ScoreBar(Flowable):
    """Horizontal score bar 1-5"""
    def __init__(self, score, max_score=5, width=60, height=8, color=C_BLUE):
        Flowable.__init__(self)
        self.score = score
        self.max_score = max_score
        self.width = width
        self.height = height
        self.color = color

    def draw(self):
        c = self.canv
        seg_w = self.width / self.max_score
        gap = 1.5
        for i in range(self.max_score):
            x = i * seg_w
            filled = i < self.score
            c.setFillColor(self.color if filled else HexColor('#E0E6F0'))
            c.setStrokeColor(C_WHITE)
            c.setLineWidth(0.5)
            c.rect(x + gap/2, 0, seg_w - gap, self.height, fill=1, stroke=1)

# ── Helper: section banner ───────────────────────────────────────
def section_banner(text, color, subtext='', width=None):
    w = width or (W - 2*MARGIN)
    elems = []
    # draw background rectangle via a table with background
    content = [[Paragraph(text, S['tier_label'])]]
    if subtext:
        content.append([Paragraph(subtext, S['tier_desc'])])
    tbl = Table(content, colWidths=[w])
    tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), color),
        ('TOPPADDING',   (0,0), (-1,-1), 7),
        ('BOTTOMPADDING',(0,0), (-1,-1), 7),
        ('LEFTPADDING',  (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
        ('ROUNDEDCORNERS', [4]),
    ]))
    elems.append(tbl)
    return elems

# ── Helper: journal table ─────────────────────────────────────────
def journal_table(rows, tier_color, col_widths=None):
    """rows = list of dicts with keys: num, name, publisher, index, access, IF, cs, q"""
    HDR = ['#', 'Journal', 'Publisher', 'Index', 'Access', 'IF (2024)', 'CiteScore', 'Quartile']
    cw = col_widths or [8, 105, 58, 45, 38, 30, 35, 90]
    available = W - 2*MARGIN
    scale = available / sum(cw)
    cw = [x * scale for x in cw]

    data = [[Paragraph(h, S['col_hdr']) for h in HDR]]
    for r in rows:
        data.append([
            Paragraph(str(r['num']), S['cell']),
            Paragraph(f"<b>{r['name']}</b>", S['cell']),
            Paragraph(r['publisher'], S['cell_sm']),
            Paragraph(r['index'], S['cell_sm']),
            Paragraph(r['access'], S['cell_sm']),
            Paragraph(r['IF'], S['cell']),
            Paragraph(r['cs'], S['cell']),
            Paragraph(r['q'], S['cell_sm']),
        ])

    tbl = Table(data, colWidths=cw, repeatRows=1)
    row_styles = [
        ('BACKGROUND',   (0,0),  (-1,0),  tier_color),
        ('TEXTCOLOR',    (0,0),  (-1,0),  C_WHITE),
        ('GRID',         (0,0),  (-1,-1), 0.3, C_GRAY_MID),
        ('ROWBACKGROUNDS',(0,1), (-1,-1), [C_WHITE, C_GRAY_LIGHT]),
        ('TOPPADDING',   (0,0),  (-1,-1), 3),
        ('BOTTOMPADDING',(0,0),  (-1,-1), 3),
        ('LEFTPADDING',  (0,0),  (-1,-1), 3),
        ('RIGHTPADDING', (0,0),  (-1,-1), 3),
        ('VALIGN',       (0,0),  (-1,-1), 'TOP'),
        ('FONTSIZE',     (0,0),  (-1,-1), 7.5),
    ]
    tbl.setStyle(TableStyle(row_styles))
    return tbl


def fit_note(journal_name, note, tier_color):
    content = [[
        Paragraph(f"<b>{journal_name}</b>  —  {note}", S['fit'])
    ]]
    tbl = Table(content, colWidths=[W - 2*MARGIN])
    tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), C_GRAY_LIGHT),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LINEBELOW', (0,0), (-1,-1), 0.3, C_GRAY_MID),
        ('LEFTLINE', (0,0), (0,-1), 3, tier_color),
    ]))
    return tbl


# ── Page template with header/footer ────────────────────────────
def make_doc(path):
    doc = SimpleDocTemplate(
        path,
        pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=MARGIN + 8*mm,
        title="Journal Recommendation Report",
        author="Journal Recommender Skill",
    )
    return doc

def on_page(canvas, doc):
    canvas.saveState()
    w, h = A4
    # footer line
    canvas.setStrokeColor(C_GRAY_MID)
    canvas.setLineWidth(0.4)
    canvas.line(MARGIN, 14*mm, w - MARGIN, 14*mm)
    # footer text
    canvas.setFont('Helvetica', 7.5)
    canvas.setFillColor(HexColor('#999999'))
    canvas.drawString(MARGIN, 10*mm, "Journal Recommendation Report  |  Generated by Journal Recommender Skill")
    canvas.drawRightString(w - MARGIN, 10*mm, f"Page {doc.page}")
    canvas.restoreState()

# ════════════════════════════════════════════════════════════════
# BUILD CONTENT
# ════════════════════════════════════════════════════════════════
def build_pdf(output_path):
    doc = make_doc(output_path)
    story = []
    sp = lambda n=6: Spacer(1, n)
    HR = lambda color=C_GRAY_MID, w=1: HRFlowable(width='100%', thickness=w, color=color, spaceAfter=4, spaceBefore=4)

    # ── COVER BAND ──────────────────────────────────────────────
    cover_data = [[
        Paragraph("Journal Recommendation Report", S['cover_title']),
        Paragraph("Green Synthesis of Robust Superhydrophobic Antibacterial<br/>and UV Blocking Cotton Fabrics by Dual Stage Silanization", S['cover_sub']),
        Paragraph(f"Neha Agrawal et al.  |  NTU Singapore  |  Generated {datetime.date.today().strftime('%d %B %Y')}", S['cover_meta']),
    ]]
    cover_tbl = Table(cover_data, colWidths=[W - 2*MARGIN])
    cover_tbl.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,-1), C_BLUE),
        ('TOPPADDING',    (0,0), (-1,-1), 14),
        ('BOTTOMPADDING', (0,0), (-1,-1), 14),
        ('LEFTPADDING',   (0,0), (-1,-1), 14),
        ('RIGHTPADDING',  (0,0), (-1,-1), 14),
        ('ROUNDEDCORNERS', [6]),
    ]))
    story += [cover_tbl, sp(12)]

    # ── PAPER SNAPSHOT ─────────────────────────────────────────
    story += section_banner("📄  Paper Summary", C_ACCENT)
    story.append(sp(6))
    snap_rows = [
        ["Field", "Materials Science · Textile Surface Engineering · Nanomaterials"],
        ["Methodology", "Experimental — multi-technique characterisation (FESEM, FTIR, XRD, contact angle), AATCC-standardised antibacterial and UV testing, 4-dimension durability benchmarking"],
        ["Key Contribution", "Dual silanization approach (APTES cross-linker + HDTMS hydrophobe) that anchors ZnO nanoparticles to cotton with significantly improved wash and abrasion durability vs. prior single-step methods"],
        ["Keywords", "Superhydrophobic · ZnO nanoparticles · Silanization · Antibacterial textiles · UV blocking · Cotton · Green synthesis · Functional coatings"],
        ["Indexing Preference", "Scopus  |  Access: Open Access or Subscription"],
        ["Journals Found", "37 journals recommended: 10 Ambitious · 15 Target · 12 Safe, all from Scopus March 2025 master list"],
    ]
    snap_tbl = Table(snap_rows, colWidths=[75, W - 2*MARGIN - 75])
    snap_tbl.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (0,-1), C_BLUE_LIGHT),
        ('FONTNAME',      (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTSIZE',      (0,0), (-1,-1), 8.5),
        ('TEXTCOLOR',     (0,0), (0,-1), C_BLUE),
        ('GRID',          (0,0), (-1,-1), 0.3, C_GRAY_MID),
        ('ROWBACKGROUNDS',(1,0), (1,-1), [C_WHITE, C_GRAY_LIGHT]),
        ('TOPPADDING',    (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING',   (0,0), (-1,-1), 7),
        ('VALIGN',        (0,0), (-1,-1), 'TOP'),
    ]))
    story += [snap_tbl, sp(14)]

    col_w = W - 2*MARGIN

    # ════════════════════════════════════════════════════════════
    # AMBITIOUS TIER
    # ════════════════════════════════════════════════════════════
    story += section_banner("🔴  AMBITIOUS JOURNALS", C_RED)
    story.append(sp(8))

    amb_rows = [
        {'num':1,  'name':'Advanced Fiber Materials',              'publisher':'Springer',  'index':'WoS + Scopus','access':'Subscription','IF':'21.3', 'cs':'16.5', 'q':'Q1 – Mat. Sci. Textiles',              'ar':'not published','dt':'not published'},
        {'num':2,  'name':'Advanced Functional Materials',         'publisher':'Wiley-VCH', 'index':'WoS + Scopus','access':'Subscription','IF':'19.96','cs':'19.0', 'q':'Q1 – Mat. Sci. Multidisciplinary',     'ar':'not published','dt':'~40 days'},
        {'num':3,  'name':'ACS Nano',                              'publisher':'ACS',       'index':'WoS + Scopus','access':'Subscription','IF':'16.0', 'cs':'26.0', 'q':'Q1 – Mat. Sci. Multidisciplinary (top 6%)','ar':'not published','dt':'not published'},
        {'num':4,  'name':'Carbohydrate Polymers',                 'publisher':'Elsevier',  'index':'WoS + Scopus','access':'Subscription','IF':'13.58','cs':'16.3', 'q':'Q1 – Polymer Science (rank 4/89)',     'ar':'~20–25%',      'dt':'6–10 weeks'},
        {'num':5,  'name':'Journal of Colloid and Interface Science','publisher':'Elsevier','index':'WoS + Scopus','access':'Subscription','IF':'10.39','cs':'18.5', 'q':'Q1 – Chemistry Physical',              'ar':'not published','dt':'~2 months'},
        {'num':6,  'name':'Nano Letters',                          'publisher':'ACS',       'index':'WoS + Scopus','access':'Subscription','IF':'9.09', 'cs':'14.8', 'q':'Q1 – Nanoscience & Nanotechnology',    'ar':'not published','dt':'not published'},
        {'num':7,  'name':'Small Science',                         'publisher':'Wiley-VCH', 'index':'WoS + Scopus','access':'Open Access', 'IF':'8.3',  'cs':'7.2',  'q':'Q1 – Nanoscience & Nanotechnology',    'ar':'not published','dt':'not published'},
        {'num':8,  'name':'ACS Applied Materials and Interfaces',  'publisher':'ACS',       'index':'WoS + Scopus','access':'Subscription','IF':'8.26', 'cs':'14.4', 'q':'Q1 – Mat. Sci. Multidisciplinary',     'ar':'not published','dt':'not published'},
        {'num':9,  'name':'Progress in Organic Coatings',          'publisher':'Elsevier',  'index':'WoS + Scopus','access':'Subscription','IF':'8.19', 'cs':'12.6', 'q':'Q1 – Mat. Sci. Coatings & Films',      'ar':'not published','dt':'not published'},
        {'num':10, 'name':'ACS Applied Nano Materials',            'publisher':'ACS',       'index':'WoS + Scopus','access':'Subscription','IF':'5.5',  'cs':'8.3',  'q':'Q1 – Nanoscience & Nanotechnology',    'ar':'not published','dt':'not published'},
    ]
    story.append(journal_table(amb_rows, C_RED))
    story.append(sp(4))

    amb_notes = [
        ("Advanced Fiber Materials",
         "The #1 ranked journal in Materials Science, Textiles (IF 21.3); superhydrophobic multifunctional cotton fabrics are core to its scope — the dual silanization mechanism and durability benchmarking are the strongest levers for acceptance here."),
        ("Advanced Functional Materials",
         "Regularly publishes multi-functional nanoparticle-fabric systems; the green synthesis angle and combined superhydrophobic + antibacterial + UV-blocking properties are appealing, but the novelty framing relative to prior ZnO-on-cotton literature must be airtight."),
        ("ACS Nano",
         "ACS flagship nano journal (IF 16.0, top 6% of Mat. Sci. Multidisciplinary); the ZnO nanoparticle architecture and multi-functional performance are in scope, but the bar for novelty is high — best submitted with the nano-enabled mechanism, not the textile application, as the lead story."),
        ("Nano Letters",
         "High-impact ACS letters format (IF 9.09); the nanoparticle synthesis, characterisation, and surface chemistry would need to be framed as a nano-science advance rather than a textile engineering paper — a tighter, more focused submission than the full manuscript."),
        ("Carbohydrate Polymers",
         "Cotton is a cellulosic biopolymer and the APTES–cellulose hydroxyl chemistry is mechanistically central; IF 12.5 is top-5% in Polymer Science and the cotton substrate makes this a genuine fit beyond a generic 'materials' submission."),
        ("Journal of Colloid and Interface Science",
         "Strong fit for the wetting physics (WCA 154°, WSA 2°), surface energy analysis, and APTES–ZnO–cellulose interfacial chemistry; the bond-formation mechanism figures are exactly what this journal rewards."),
        ("ACS Applied Materials and Interfaces",
         "Broad applied scope, realistic Q1 target for multi-functional coatings with quantified performance data; high submission volume means individual-paper visibility varies — clear application framing is essential."),
        ("Progress in Organic Coatings",
         "Directly covers organic surface treatments and hydrophobic coatings; the silane chemistry (APTES + HDTMS), contact angle data, and four-dimension durability battery are squarely in scope — IF 8.19 places it firmly at the top of the coatings sub-field."),
        ("Small Science",
         "Wiley-VCH OA journal for micro/nanotechnology (IF 8.3, Q1); the ZnO nanoparticle-enabled multi-functionality and the surface chemistry at the nano-scale are a natural fit — open access format without compromising on prestige."),
        ("ACS Applied Nano Materials",
         "ACS journal dedicated to fundamental and applied nanomaterials science (IF 5.5, Q1); nanoparticle–polymer surface composites with functional performance data are exactly its remit — lower selectivity than ACS Nano but same ACS indexing and visibility."),
    ]
    for name, note in amb_notes:
        story.append(fit_note(name, note, C_RED))
    story.append(sp(14))

    # ════════════════════════════════════════════════════════════
    # TARGET TIER
    # ════════════════════════════════════════════════════════════
    story += section_banner("🟡  TARGET JOURNALS", C_AMBER)
    story.append(sp(8))

    tgt_rows = [
        {'num':1,  'name':'Applied Surface Science Advances',          'publisher':'Elsevier', 'index':'WoS + Scopus','access':'Open Access', 'IF':'7.5', 'cs':'5.8',  'q':'Q1 – Surfaces & Coatings',               'ar':'not published','dt':'not published'},
        {'num':2,  'name':'Applied Surface Science',                   'publisher':'Elsevier', 'index':'WoS + Scopus','access':'Subscription','IF':'6.9', 'cs':'12.1', 'q':'Q1 – Mat. Sci. Coatings & Films',         'ar':'~50–60%',      'dt':'6–8 weeks'},
        {'num':3,  'name':'Surfaces and Interfaces',                   'publisher':'Elsevier', 'index':'WoS + Scopus','access':'Subscription','IF':'6.6', 'cs':'5.0',  'q':'Q1 – Mat. Sci. Coatings & Films',         'ar':'not published','dt':'not published'},
        {'num':4,  'name':'Surface and Coatings Technology',           'publisher':'Elsevier', 'index':'WoS + Scopus','access':'Subscription','IF':'6.5', 'cs':'10.2', 'q':'Q1 – Mat. Sci. Coatings & Films',         'ar':'not published','dt':'~10 weeks'},
        {'num':5,  'name':'Nanoscale',                                 'publisher':'RSC',      'index':'WoS + Scopus','access':'Subscription','IF':'6.7', 'cs':'11.6', 'q':'Q1 – Nanoscience & Nanotechnology',       'ar':'not published','dt':'not published'},
        {'num':6,  'name':'Carbohydrate Polymer Technologies and Applications','publisher':'Elsevier','index':'WoS + Scopus','access':'Open Access','IF':'6.91','cs':'5.4','q':'Q1 – Materials Chemistry',            'ar':'not published','dt':'not published'},
        {'num':7,  'name':'Reactive and Functional Polymers',          'publisher':'Elsevier', 'index':'WoS + Scopus','access':'Subscription','IF':'5.43','cs':'7.8',  'q':'Q1 – Polymers and Plastics',              'ar':'not published','dt':'not published'},
        {'num':8,  'name':'International Journal of Biological Macromolecules','publisher':'Elsevier','index':'WoS + Scopus','access':'Subscription','IF':'7.7','cs':'11.6','q':'Q1 – Biochemistry',                 'ar':'not published','dt':'not published'},
        {'num':9,  'name':'Polymers',                                  'publisher':'MDPI',     'index':'WoS + Scopus','access':'Open Access', 'IF':'4.9', 'cs':'6.5',  'q':'Q1 – Polymer Science (rank 19/94)',        'ar':'not published','dt':'~14 days'},
        {'num':10, 'name':'Cellulose',                                 'publisher':'Springer', 'index':'WoS + Scopus','access':'Subscription','IF':'4.8', 'cs':'8.1',  'q':'Q1 – Mat. Sci. Textiles / Paper & Wood',  'ar':'not published','dt':'not published'},
        {'num':11, 'name':'Nanoscale Advances',                        'publisher':'RSC',      'index':'WoS + Scopus','access':'Open Access', 'IF':'4.6', 'cs':'4.64', 'q':'Q1 – Nanoscience',                        'ar':'not published','dt':'~31 days'},
        {'num':12, 'name':'Dyes and Pigments',                         'publisher':'Elsevier', 'index':'WoS + Scopus','access':'Subscription','IF':'4.3', 'cs':'8.1',  'q':'Q1 – Mat. Sci. Textiles / Chem. Applied', 'ar':'not published','dt':'not published'},
        {'num':13, 'name':'Langmuir',                                  'publisher':'ACS',      'index':'WoS + Scopus','access':'Subscription','IF':'3.95','cs':'6.7',  'q':'Q1 – Chemistry Physical',                 'ar':'not published','dt':'not published'},
        {'num':14, 'name':'New Journal of Chemistry',                  'publisher':'RSC',      'index':'WoS + Scopus','access':'Subscription','IF':'2.5', 'cs':'5.0',  'q':'Q2 – Chemistry Multidisciplinary',         'ar':'not published','dt':'not published'},
        {'num':15, 'name':'Coloration Technology',                     'publisher':'Wiley',    'index':'WoS + Scopus','access':'Subscription','IF':'2.81','cs':'3.6',  'q':'Q2 – Mat. Sci. Textiles (WoS: Q1)',       'ar':'not published','dt':'not published'},
    ]
    story.append(journal_table(tgt_rows, C_AMBER))
    story.append(sp(4))

    tgt_notes = [
        ("Applied Surface Science Advances",
         "OA sister journal of Applied Surface Science with identical scope; Q1 in Surfaces and Coatings Films — an open-access option for the wettability, SEM/EDS, and surface chemistry content without compromising on indexing."),
        ("Applied Surface Science",
         "One of the highest-volume materials journals globally; superhydrophobic textile coatings via nanoparticle deposition are a staple here; the ~50–60% acceptance and 6–8 week decision make it a practical, expedient submission."),
        ("Surfaces and Interfaces",
         "Elsevier journal dedicated to surfaces, coatings, and interface engineering (IF 6.6, Q2 Surfaces & Coatings); the silanization chemistry, ZnO surface deposition, and wettability data map directly to its editorial scope — fast growing journal with accessible acceptance rates."),
        ("Surface and Coatings Technology",
         "Dedicated to surface modification for functional performance; scope explicitly includes wet chemical and silane-based processes — the APTES/HDTMS chemistry and multi-dimension durability battery are a direct content match."),
        ("Reactive and Functional Polymers",
         "Covers functionalised polymers including antimicrobial agents, surface-reactive polymers, and hydrogels (IF 5.43, Q1 Polymers & Plastics); the APTES-mediated reactive coupling to cotton cellulose and the ZnO functional layer are strongly within scope."),
        ("International Journal of Biological Macromolecules",
         "Cotton cellulose modification is central to its scope; the APTES–hydroxyl bonding mechanism and macromolecular characterisation (FTIR, XRD of cellulose crystallinity) make this a strong thematic fit alongside the functional performance data."),
        ("Nanoscale",
         "RSC flagship nano journal; the ZnO nanoparticle characterisation, nanocomposite architecture, and multi-property performance are in scope — best framed around the nano-enabled functionality rather than the textile application per se."),
        ("Nanomaterials",
         "MDPI OA journal (IF 4.3, Q1 Nanoscience); dedicated to nanomaterial synthesis, characterisation, and applications — the green ZnO synthesis and nanocomposite coating performance are a direct fit; fast turnaround (~6 weeks) and fully open access."),
        ("Cellulose",
         "International journal devoted to cellulose science including textile fibre applications; explicitly covers surface modifications of cotton and manufactured fibres — the APTES chemistry on cellulose hydroxyl groups is precisely its subject matter."),
        ("Nanoscale Advances",
         "OA alternative to Nanoscale with fast first decision (~31 days all submissions); a practical open-access choice for the ZnO silanization chemistry particularly suited to authors with OA requirements."),
        ("Dyes and Pigments",
         "WoS-indexed under Materials Science, Textiles; UV blocking performance, colorant-substrate interaction, and HDTMS surface treatment of cotton are core to its scope — the AATCC 183 UV data and white appearance retention are notable selling points here."),
        ("Langmuir",
         "ACS's leading interfacial science journal; the contact angle physics, surface energy modification, and APTES/HDTMS bonding mechanism are exactly its subject — best submitted as an interface/surface chemistry paper, not a textiles paper."),
        ("New Journal of Chemistry",
         "RSC broad applied chemistry journal with a strong materials presence; green synthesis framing and multi-step functional surface chemistry are well-represented — accessible but credible for an RSC imprint."),
        ("Coloration Technology",
         "Wiley journal dedicated to textile surface treatment under WoS Materials Science, Textiles; AATCC-standardised UV blocking, antibacterial testing, and surface hydrophobicity of cotton are precisely its editorial remit."),
        ("Carbohydrate Polymer Technologies and Applications",
         "OA Elsevier journal (Q1 Materials Chemistry) launched as a companion to Carbohydrate Polymers; cellulose-based surface modifications and functional applications are core content — open access with the Elsevier editorial quality benchmark."),
    ]
    for name, note in tgt_notes:
        story.append(fit_note(name, note, C_AMBER))
    story.append(sp(14))

    # ════════════════════════════════════════════════════════════
    # SAFE TIER
    # ════════════════════════════════════════════════════════════
    story += section_banner("🟢  SAFE JOURNALS", C_GREEN)
    story.append(sp(8))

    saf_rows = [
        {'num':1,  'name':'RSC Advances',                       'publisher':'RSC',             'index':'WoS + Scopus','access':'Open Access', 'IF':'4.6', 'cs':'7.2',  'q':'Q2 – Chemistry Multidisciplinary', 'ar':'~45–55%',      'dt':'~30 days'},
        {'num':2,  'name':'Nanomaterials',                       'publisher':'MDPI',            'index':'WoS + Scopus','access':'Open Access', 'IF':'4.3', 'cs':'5.9',  'q':'Q1 – Nanoscience (MDPI)',          'ar':'not published','dt':'~6 weeks'},
        {'num':3,  'name':'Journal of Applied Polymer Science',  'publisher':'Wiley',           'index':'WoS + Scopus','access':'Subscription','IF':'3.2', 'cs':'5.0',  'q':'Q2 – Polymer Science',             'ar':'not published','dt':'not published'},
        {'num':4,  'name':'Journal of Natural Fibers',           'publisher':'Taylor & Francis','index':'WoS + Scopus','access':'Open Access', 'IF':'3.1', 'cs':'3.9',  'q':'Q2 – Mat. Sci. Textiles',          'ar':'not published','dt':'~21 weeks'},
        {'num':5,  'name':'Journal of Engineered Fibers and Fabrics','publisher':'SAGE',        'index':'WoS + Scopus','access':'Open Access', 'IF':'2.77','cs':'3.2',  'q':'Q2 – Mat. Sci. Textiles',          'ar':'not published','dt':'not published'},
        {'num':6,  'name':'Coatings',                            'publisher':'MDPI',            'index':'WoS + Scopus','access':'Open Access', 'IF':'2.8', 'cs':'4.1',  'q':'Q2 – Mat. Sci. Coatings & Films',  'ar':'not published','dt':'not published'},
        {'num':7,  'name':'Fibers and Polymers',                 'publisher':'Korean Fiber Soc.','index':'WoS + Scopus','access':'Subscription','IF':'2.65','cs':'3.3', 'q':'Q2 – Mat. Sci. Textiles',          'ar':'not published','dt':'not published'},
        {'num':8,  'name':'Textile Research Journal',            'publisher':'SAGE',            'index':'WoS + Scopus','access':'Subscription','IF':'1.9', 'cs':'3.1',  'q':'Q2 – Mat. Sci. Textiles',          'ar':'not published','dt':'not published'},
        {'num':9,  'name':'AATCC Journal of Research',           'publisher':'SAGE',            'index':'WoS + Scopus','access':'Subscription','IF':'—',   'cs':'2.1',  'q':'Q2 – Mat. Sci. Textiles',          'ar':'not published','dt':'not published'},
        {'num':10, 'name':'Journal of Industrial Textiles',      'publisher':'SAGE',            'index':'WoS + Scopus','access':'Open Access', 'IF':'—',   'cs':'2.8',  'q':'Q2 – Mat. Sci. Textiles',          'ar':'not published','dt':'not published'},
        {'num':11, 'name':'Autex Research Journal',              'publisher':'De Gruyter',      'index':'WoS + Scopus','access':'Open Access', 'IF':'—',   'cs':'2.2',  'q':'Q3 – Mat. Sci. Textiles',          'ar':'not published','dt':'not published'},
        {'num':12, 'name':'Fibers',                              'publisher':'MDPI',            'index':'WoS + Scopus','access':'Open Access', 'IF':'—',   'cs':'2.0',  'q':'Q2 – Mat. Sci. Multidisciplinary', 'ar':'not published','dt':'not published'},
    ]
    story.append(journal_table(saf_rows, C_GREEN))
    story.append(sp(4))

    saf_notes = [
        ("RSC Advances",
         "Broad-scope OA chemistry journal; ~45–55% acceptance and OA format make it a low-friction submission for the silanization chemistry and ZnO antibacterial results; reliable indexing and RSC brand recognition."),
        ("Journal of Applied Polymer Science",
         "Covers polymer applications including textile coatings and surface modification; the HDTMS/APTES silane chemistry on cotton cellulose aligns cleanly with its applied polymer scope."),
        ("Journal of Natural Fibers",
         "Taylor & Francis OA journal (IF 3.1, Q2 Mat. Sci. Textiles) dedicated to natural-fibre materials science; cotton fabric surface engineering is exactly its core territory and the green synthesis angle is particularly well-received here."),
        ("Fibers and Polymers",
         "Korean Fiber Society journal covering dyeing, finishing, and textile processing; a direct subject match — functional fabric performance, durability testing, and surface chemistry all fall within its remit."),
        ("Journal of Engineered Fibers and Fabrics",
         "SAGE OA journal (IF 2.77, Q2 Mat. Sci. Textiles); engineered textile performance, surface functionalisation, and technical fabric applications are its core topics — a highly targeted home for the full applied textile narrative of this paper."),
        ("Coatings",
         "MDPI OA journal dedicated to coatings science including hydrophobic films and nanoparticle-based functional surfaces; Q2 in Materials Science Coatings & Films with fast MDPI turnaround and reliable Scopus/WoS indexing."),
        ("Textile Research Journal",
         "SAGE's flagship textiles journal, one of the longest-established in the field; fundamental and applied textile science including surface finishes and functional fabrics — high name recognition in the textiles community despite modest IF."),
        ("Polymers",
         "MDPI OA polymer science journal (Q1/Q2 Polymer Science); broad scope covering polymer synthesis, characterisation, and applications including functional coatings — the HDTMS/APTES polymer chemistry and cotton surface modification are strongly in scope."),
        ("AATCC Journal of Research",
         "Published by the same body whose test standards were used in this paper (AATCC 100-2004 and AATCC 183-2004); institutional fit is strong and reviewers will immediately recognise the test protocols — ideal for visibility within the textile testing community."),
        ("Journal of Industrial Textiles",
         "SAGE OA journal focused on industrial and technical textiles; functional performance data (antibacterial, UV, hydrophobicity) in an applied fabric context are squarely its content — straightforward editorial fit with high acceptance probability."),
        ("Autex Research Journal",
         "Open access, WoS + Scopus indexed textiles journal; broad textile scope with low barriers — a reliable fallback option if higher-tier submissions are unsuccessful."),
        ("Fibers",
         "MDPI OA multidisciplinary fibres journal (WoS Mat. Sci. Multidisciplinary); covers chemical properties, processing, and functional applications of natural and synthetic fibres — the cotton substrate chemistry and functional coating are in scope and publication costs are low."),
    ]
    for name, note in saf_notes:
        story.append(fit_note(name, note, C_GREEN))

    story.append(sp(14))

    # ── PAPER QUALITY ASSESSMENT (end of report) ─────────────────
    story.append(PageBreak())
    story += section_banner("📊  Paper Quality Assessment", C_ACCENT)
    story.append(sp(6))
    story.append(Paragraph(
        "The paper was evaluated on five dimensions (scored 1–5) to determine the appropriate tier anchor for recommendations. "
        "Scores reflect the work's relative standing within the functional textiles / surface engineering literature.",
        S['body']
    ))
    story.append(sp(8))

    score_data = [
        [
            Paragraph("Dimension", S['col_hdr']),
            Paragraph("Score", S['col_hdr']),
            Paragraph("Visual", S['col_hdr']),
            Paragraph("Assessment", S['col_hdr']),
        ],
        [
            Paragraph("Novelty", S['score_dim']),
            Paragraph("3 / 5", S['cell']),
            ScoreBar(3, color=C_BLUE),
            Paragraph("Dual silanization for durability is a well-argued methodological advance; ZnO-based multifunctional textile coatings are a populated area — novelty centres on the anchoring mechanism and durability outcome, not the three functions individually.", S['score_txt']),
        ],
        [
            Paragraph("Methodological Rigor", S['score_dim']),
            Paragraph("4 / 5", S['cell']),
            ScoreBar(4, color=C_GREEN),
            Paragraph("Strong: FESEM, FTIR, XRD, contact angle, standardised AATCC antibacterial and UV tests (AATCC 100-2004 and 183-2004), n=3 replicates, four independent durability stressors.", S['score_txt']),
        ],
        [
            Paragraph("Contribution Breadth", S['score_dim']),
            Paragraph("3 / 5", S['cell']),
            ScoreBar(3, color=C_BLUE),
            Paragraph("Advances functional textiles and surface coatings subfield; moderate cross-disciplinary reach into nanomaterials and green chemistry — not a field-wide paradigm shift.", S['score_txt']),
        ],
        [
            Paragraph("Evidence Quality", S['score_dim']),
            Paragraph("4 / 5", S['cell']),
            ScoreBar(4, color=C_GREEN),
            Paragraph("Quantified results with error bars; 800 abrasion cycles, 120 min ultrasonic wash, pH 1–13 immersion, 12 hr UV irradiation — comprehensive and reproducible for the field.", S['score_txt']),
        ],
        [
            Paragraph("Clarity of Advance", S['score_dim']),
            Paragraph("4 / 5", S['cell']),
            ScoreBar(4, color=C_GREEN),
            Paragraph("Explicitly identifies the gap (nanoparticle loss after washing in prior work, refs 23, 25, 26) and benchmarks against it — the advance is clearly documented and differentiated.", S['score_txt']),
        ],
    ]
    score_tbl = Table(score_data, colWidths=[90, 35, 65, col_w - 90 - 35 - 65], repeatRows=1)
    score_tbl.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,0), C_BLUE),
        ('ROWBACKGROUNDS',(0,1), (-1,-1), [C_SCORE_BG, C_WHITE]),
        ('GRID',          (0,0), (-1,-1), 0.3, C_GRAY_MID),
        ('TOPPADDING',    (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING',   (0,0), (-1,-1), 6),
        ('RIGHTPADDING',  (0,0), (-1,-1), 6),
        ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story += [score_tbl, sp(8)]

    total_data = [[
        Paragraph("Total Score: <b>18 / 25</b>", ParagraphStyle('ts2', parent=base['Normal'],
            fontSize=11, textColor=C_WHITE, fontName='Helvetica-Bold')),
        Paragraph(
            "Solid, well-executed experimental work with a clear durability contribution. "
            "The paper is competitive at strong specialty journals (Target tier) and selective Ambitious options "
            "where the multi-functionality + durability angle is genuinely distinctive. "
            "It does not yet reach the transformative novelty threshold required by flagship broad-scope materials journals.",
            ParagraphStyle('tsdesc2', parent=base['Normal'],
            fontSize=8.5, textColor=HexColor('#DCE8FF'), leading=12.5, fontName='Helvetica')
        ),
    ]]
    total_tbl = Table(total_data, colWidths=[110, col_w - 110])
    total_tbl.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,-1), C_BLUE),
        ('TOPPADDING',    (0,0), (-1,-1), 9),
        ('BOTTOMPADDING', (0,0), (-1,-1), 9),
        ('LEFTPADDING',   (0,0), (-1,-1), 10),
        ('RIGHTPADDING',  (0,0), (-1,-1), 10),
        ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
        ('ROUNDEDCORNERS', [4]),
    ]))
    story += [total_tbl, sp(14)]

    # ── TIER DEFINITIONS (end of report) ────────────────────────
    story += section_banner("🏷️  What the Tiers Mean", C_ACCENT)
    story.append(sp(6))
    tier_def_rows = [
        [
            Paragraph("🔴  AMBITIOUS", ParagraphStyle('td1b', parent=base['Normal'],
                fontSize=9, textColor=C_RED, fontName='Helvetica-Bold')),
            Paragraph(
                "Top 10–15% of field by SJR/CiteScore. High-profile specialty or flagship journals. "
                "Expect rigorous peer review; rejection rate is high. The paper's durability story and "
                "multi-property combination are the strongest levers at this tier.",
                S['body_sm']),
            Paragraph("Acceptance typically &lt;25%", S['body_sm']),
        ],
        [
            Paragraph("🟡  TARGET", ParagraphStyle('td2b', parent=base['Normal'],
                fontSize=9, textColor=C_AMBER, fontName='Helvetica-Bold')),
            Paragraph(
                "Top 15–50% of field. Strong specialty journals with direct scope alignment. "
                "Best realistic fit for the work as submitted — scope, quality level, and methodology "
                "are well-matched to editorial expectations.",
                S['body_sm']),
            Paragraph("Acceptance typically 20–50%", S['body_sm']),
        ],
        [
            Paragraph("🟢  SAFE", ParagraphStyle('td3b', parent=base['Normal'],
                fontSize=9, textColor=C_GREEN, fontName='Helvetica-Bold')),
            Paragraph(
                "Reputable, indexed journals in the lower half of field ranking. "
                "Broad scope or less selective — high probability of acceptance. "
                "All are Scopus-indexed and peer-reviewed.",
                S['body_sm']),
            Paragraph("Acceptance typically &gt;35%", S['body_sm']),
        ],
    ]
    tier_def_tbl = Table(tier_def_rows, colWidths=[65, col_w - 65 - 90, 90])
    tier_def_tbl.setStyle(TableStyle([
        ('GRID',          (0,0), (-1,-1), 0.3, C_GRAY_MID),
        ('ROWBACKGROUNDS',(0,0), (-1,-1), [C_RED_LIGHT, C_AMBER_LIGHT, C_GREEN_LIGHT]),
        ('TOPPADDING',    (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING',   (0,0), (-1,-1), 8),
        ('RIGHTPADDING',  (0,0), (-1,-1), 8),
        ('VALIGN',        (0,0), (-1,-1), 'TOP'),
    ]))
    story += [tier_def_tbl, sp(6)]
    story.append(Paragraph(
        "All journals listed are indexed in Scopus as per the official March 2025 master list. "
        "Metrics (IF, CiteScore, SJR, quartile) are sourced from Scimago, Clarivate JCR 2024, and "
        "journal websites; 'not published' means the metric was searched for but not publicly disclosed by the publisher.",
        S['disclaimer']
    ))
    story.append(sp(14))

    # ── FOOTER NOTE ─────────────────────────────────────────────
    story += section_banner("ℹ️  Notes on Metrics & Methodology", C_DARK)
    story.append(sp(6))
    notes_text = [
        "• <b>Impact Factor (IF)</b>: Sourced from Clarivate JCR 2024, released June 2025. Shown as '—' where not publicly listed.",
        "• <b>CiteScore</b>: Scopus four-year citation metric. Sourced from Scopus / Researcher.life.",
        "• <b>Quartile</b>: Scimago SJR quartile within the most relevant subject category for this paper. Where WoS and Scopus quartiles differ, the more relevant category is shown.",
        "• <b>Database</b>: All journals are from the official Scopus March 2025 and/or WoS March 2024 master lists. No journal outside these lists is recommended.",
        "• <b>Paper scoring</b>: Five-dimension internal assessment (1–5 each) against the functional textiles / surface engineering literature. Scores inform tier placement but are not editorial criteria.",
    ]
    for n in notes_text:
        story.append(Paragraph(n, S['body_sm']))
        story.append(sp(3))

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    print("PDF generated successfully.")

build_pdf('/mnt/user-data/outputs/Journal_Recommendation_Report.pdf')
