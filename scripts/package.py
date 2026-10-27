"""Create a source-only deployment archive. Credentials are never included."""
import tarfile
from pathlib import Path

root=Path(__file__).resolve().parent.parent
output=root/"output"/"note-calendar-source.tar.gz"
output.parent.mkdir(exist_ok=True)
with tarfile.open(output,"w:gz") as archive:
    for name in ["note_calendar","tests","deploy","scripts","docs","firmware/src","firmware/include","firmware/platformio.ini","firmware/partitions.csv","pyproject.toml","README.md","PRODUCT.md","DESIGN.md",".impeccable/design.json","THIRD_PARTY_NOTICES.md"]:
        path=root/name
        if not path.exists():continue
        paths=sorted(path.rglob("*")) if path.is_dir() else [path]
        for item in paths:
            if item.is_file() and "__pycache__" not in item.parts:
                archive.add(item,arcname=item.relative_to(root))
print(output)
