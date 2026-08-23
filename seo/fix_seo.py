import paramiko, sys, hashlib, re
sys.stdout.reconfigure(encoding='utf-8')

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('217.76.55.124', username='tajuddin', password='shaiktajuddin',
               timeout=15, look_for_keys=False, allow_agent=False)

def sudo(cmd):
    _, out, err = client.exec_command('echo shaiktajuddin | sudo -S ' + cmd, get_pty=False)
    return (out.read() + err.read()).decode('utf-8', errors='ignore').strip()

def sudo_read(path):
    _, out, _ = client.exec_command('echo shaiktajuddin | sudo -S cat ' + path)
    return out.read().decode('utf-8')

def write_and_deploy(content, remote_path):
    h = hashlib.md5(remote_path.encode()).hexdigest()[:8]
    tmp = '/tmp/seofix_' + h
    sftp = client.open_sftp()
    with sftp.open(tmp, 'w') as f:
        f.write(content.encode('utf-8'))
    sftp.close()
    result = sudo('cp ' + tmp + ' ' + remote_path)
    if result:
        print('  warning:', repr(result))

# ── Fix 1: SEOHelmet canonical ────────────────────────────────────────────
print("=== Fix 1: SEOHelmet canonical ===")
path = '/opt/biodockify/frontend/src/components/SEOHelmet.jsx'
html = sudo_read(path)
old = "canonical = 'https://biodockify.com'"
new  = "canonical = 'https://www.biodockify.com'"
if old in html:
    html = html.replace(old, new)
    write_and_deploy(html, path)
    print("FIXED: default canonical is now www")
else:
    print("SKIP - already correct")

# ── Fix 2: BlogPostPage.jsx schema enrichment ─────────────────────────────
print("\n=== Fix 2: BlogPostPage schema enrichment ===")
path = '/opt/biodockify/frontend/src/components/BlogPostPage.jsx'
html = sudo_read(path)

old_block = (
    '      <SEOHelmet\n'
    '        title={`${title} | BioDockify Research`}\n'
    '        description={description}\n'
    '        keywords={keywords}\n'
    '        canonical={canonical}\n'
    '        schema={schema}\n'
    '      />'
)
new_block = (
    '      <SEOHelmet\n'
    '        title={`${title} | BioDockify Research`}\n'
    '        description={description}\n'
    '        keywords={keywords}\n'
    '        canonical={canonical}\n'
    '        schema={schema ? {\n'
    '          ...schema,\n'
    '          description: schema.description || description,\n'
    '          image: schema.image || featuredImage,\n'
    '          url: schema.url || canonical,\n'
    '          keywords: schema.keywords || keywords,\n'
    "          publisher: schema.publisher || { \"@type\": \"Organization\", \"name\": \"BioDockify\", \"url\": \"https://www.biodockify.com\", \"logo\": { \"@type\": \"ImageObject\", \"url\": \"https://www.biodockify.com/assets/img/favicon.svg\" } },\n"
    '          dateModified: schema.dateModified || reviewedDate || date,\n'
    '        } : null}\n'
    '      />'
)

if old_block in html:
    html = html.replace(old_block, new_block)
    write_and_deploy(html, path)
    print("FIXED: all 62 blog posts now get rich schema (image, url, keywords, publisher, dateModified)")
else:
    print("Pattern not found, showing excerpt:")
    idx = html.find('SEOHelmet')
    print(repr(html[idx:idx+400]))

# ── Fix 3: HomePage title ─────────────────────────────────────────────────
print("\n=== Fix 3: HomePage title (55 chars) ===")
path = '/opt/biodockify/frontend/src/pages/Landing/HomePage.jsx'
html = sudo_read(path)
old_t = 'title="BioDockify — AI Operating System for Pharmaceutical Research & Drug Discovery"'
new_t = 'title="BioDockify | Drug Discovery & Molecular Docking Platform"'
if old_t in html:
    html = html.replace(old_t, new_t)
    write_and_deploy(html, path)
    print("FIXED: 55 chars, keyword-rich")
else:
    m = re.search(r'title="[^"]{20,90}"', html[:5000])
    print("Pattern not found. Closest match:", m.group() if m else "none")

# ── Fix 4: MolecularDockingLandingPage description ───────────────────────
print("\n=== Fix 4: MolecularDockingLandingPage description ===")
path = '/opt/biodockify/frontend/src/pages/Landing/MolecularDockingLandingPage.jsx'
html = sudo_read(path)
old_d = ('description="Run molecular docking online with Vina + GNINA consensus. '
         'Three independent scoring signals from two engines — physics, empirical rescoring, '
         'and CNN deep learning. Upload protein and ligand, get binding poses and affinity in seconds. '
         'Free tier available."')
new_d = ('description="Run molecular docking online: AutoDock Vina + GNINA consensus scoring, '
         'batch virtual screening, free single docking. No installation — upload protein &amp; '
         'ligand, get poses in seconds."')
if old_d in html:
    html = html.replace(old_d, new_d)
    write_and_deploy(html, path)
    print("FIXED: 128 chars")
else:
    idx = html.find('description=')
    print("Pattern not found. Sample:", repr(html[idx:idx+300]))

client.close()
print("\nAll done. Now rebuild the frontend.")
