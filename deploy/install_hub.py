"""Install the small ESL Hub integration after preserving the original files."""
import ast
import argparse
from datetime import datetime, timezone
from pathlib import Path
import shutil


def install(hub, source):
    app_path=hub/"app.py"
    template_path=hub/"templates"/"index.html"
    app=app_path.read_text(encoding="utf-8")
    template=template_path.read_text(encoding="utf-8")
    if "from esl_note_proxy import register_note_controller" not in app:
        anchor="app = Flask(__name__)"
        if app.count(anchor)!=1:
            raise RuntimeError("Could not identify the ESL Hub app. No files changed.")
        app=app.replace(anchor,anchor+"\nfrom esl_note_proxy import register_note_controller\nregister_note_controller(app)",1)
    template=template.replace('<a class="btn btn-outline-light" href="/note/">Note calendar</a>',"")
    if 'id="note4-tab"' not in template:
        # Keep the controller beside the existing family calendar. Its document
        # owns its settings forms, separate from the hub's configuration form.
        lines=template.splitlines(keepends=True)
        matching=[i for i,line in enumerate(lines) if 'id="family-tab"' in line]
        if len(matching)!=1:
            raise RuntimeError("Could not identify the Family Calendar tab. No files changed.")
        lines.insert(matching[0]+1,'            <li class="nav-item" role="presentation"><button class="nav-link" id="note4-tab" data-bs-toggle="tab" data-bs-target="#note4" type="button" role="tab" aria-controls="note4" aria-selected="false">Family Calendar - Note4</button></li>\n')
        template="".join(lines)
    if "{% include '_note4_panel.html' %}" not in template:
        anchor='<div class="tab-content">'
        if template.count(anchor)!=1:
            raise RuntimeError("Could not identify the hub tab panels. No files changed.")
        template=template.replace(anchor,anchor+"\n            {% include '_note4_panel.html' %}",1)
    template=template.replace("configurationActions.hidden = todoIsActive;","configurationActions.hidden = todoIsActive || target === '#note4';")
    if "js/note4-tab.js" not in template:
        template=template.replace("</body>",'<script src="{{ url_for(\'static\', filename=\'js/note4-tab.js\') }}" defer></script>\n</body>',1)
    proxy=(source/"esl_note_proxy.py").read_text(encoding="utf-8")
    ast.parse(app)
    ast.parse(proxy)
    stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup=hub.parent/("esl_hub_backup_note_"+stamp)
    backup.mkdir(mode=0o700)
    shutil.copy2(app_path,backup/"app.py")
    shutil.copy2(template_path,backup/"index.html")
    if (hub/"esl_note_proxy.py").exists():
        shutil.copy2(hub/"esl_note_proxy.py",backup/"esl_note_proxy.py")
    for target,name in ((hub/"templates"/"_note4_panel.html","_note4_panel.html"),(hub/"static"/"js"/"note4-tab.js","note4-tab.js")):
        if target.exists():
            shutil.copy2(target,backup/name)
        shutil.copy2(source/name,target)
    (hub/"esl_note_proxy.py").write_text(proxy,encoding="utf-8")
    app_path.write_text(app,encoding="utf-8")
    template_path.write_text(template,encoding="utf-8")
    print("ESL Hub integration installed. Backup:",backup)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description="Add the Note calendar tab to an existing ESL Hub checkout.")
    parser.add_argument("--hub",type=Path,required=True,help="Path to the ESL Hub checkout")
    args=parser.parse_args()
    install(args.hub.resolve(),Path(__file__).resolve().parent)
