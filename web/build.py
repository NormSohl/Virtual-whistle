"""Build web/play.html: inline web/whistle-model.js into the page template."""
from pathlib import Path

here = Path(__file__).resolve().parent
model = (here / "whistle-model.js").read_text()
page = (here / "play.template.html").read_text().replace("/*__MODEL__*/", model)
(here / "play.html").write_text(page)
print(f"wrote {here / 'play.html'} ({len(page)} bytes)")
