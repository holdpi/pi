#!/usr/bin/env python3
"""Stage only the public website for GitHub Pages, including clean URL routes."""
from pathlib import Path
import re
import shutil
import sys

root = Path(__file__).resolve().parents[1]
destination = Path(sys.argv[1]).resolve()
shutil.copytree(root / "website", destination, dirs_exist_ok=True)
(destination / ".nojekyll").touch()
(destination / "CNAME").write_text("holdpi.com\n")
for route in ("docs", "brandbook", "protocol"):
    html = (root / "website" / f"{route}.html").read_text()
    # Directory routes have a trailing slash on Pages. Preserve root asset URLs.
    html = re.sub(
        r'((?:href|src)=["\'])(?![/#]|https?:|data:|mailto:)([^"\']+)',
        r"\1/\2",
        html,
    )
    (destination / route).mkdir(exist_ok=True)
    (destination / route / "index.html").write_text(html)
print(f"Public website staged: {destination}")
