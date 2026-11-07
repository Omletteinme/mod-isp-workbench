from pathlib import Path
import shutil

root = Path(__file__).resolve().parents[1]
dist = root / "dist"
if dist.exists():
    shutil.rmtree(dist)
dist.mkdir()

shutil.copy2(root / "templates" / "index.html", dist / "index.html")
shutil.copytree(root / "static", dist / "static")

index = dist / "index.html"
html = index.read_text()
html = html.replace(
    '<nav class="topnav" aria-label="Workbench sections"><a class="current" href="#workbench">Workbench</a><a href="#methods-title">Processing paths</a><a href="#measurements-title">Measurements</a></nav>',
    '<nav class="topnav" aria-label="Project links"><a class="current" href="#workbench">Project</a><a href="https://github.com/harshithhgowdaa/mod-isp-workbench">Source &amp; docs ↗</a></nav>',
)

# Turn the inference workbench into a transparent project landing page on Vercel.
html = html.replace(
    'Checking local processors',
    'Local runtime required',
)
html = html.replace(
    '<section class="workflow" aria-label="Image processing workflow">',
    '<section class="workflow" aria-label="Local runtime information">\n'
    '      <div class="workflow-head"><div><span class="section-index">01 / RUN LOCALLY</span><h2>Start the image workbench</h2></div>'
    '<span class="privacy-note">Images stay on your machine</span></div>\n'
    '      <p>This Vercel site hosts the project interface and documentation. Image inference runs in the local Flask app because the model runtime and image payloads exceed Vercel Function limits.</p>\n'
    '      <p><a class="run-button" href="https://github.com/harshithhgowdaa/mod-isp-workbench#readme"><span>View setup instructions</span><span aria-hidden="true">↗</span></a></p>\n'
    '    </section>\n'
    '    <section class="workflow" aria-label="Image processing workflow" hidden>',
)
html = html.replace(
    '<section class="proof-section" aria-labelledby="proof-title">',
    '<section class="proof-section" aria-labelledby="proof-title" hidden>',
)
html = html.replace(
    '<section id="raw-integrity"',
    '<section id="raw-integrity"',
)
html = html.replace(
    '<section class="methods-section"',
    '<section class="methods-section" hidden',
)
html = html.replace(
    '<section class="measurement-section"',
    '<section class="measurement-section" hidden',
)
html = html.replace(
    'MOD-ISP · LOCAL RESEARCH WORKBENCH',
    '<a href="https://github.com/harshithhgowdaa/mod-isp-workbench">MOD-ISP · SOURCE REPOSITORY</a>',
)
(dist / "index.html").write_text(html)
