# Font workflow. Run inside `nix develop`, or in a venv with
# 03_Branding_Assets/03_02_Typefaces/00_Sources/requirements.txt installed.

PYTHON ?= python3
FONT_SOURCES := 03_Branding_Assets/03_02_Typefaces/00_Sources

.PHONY: fonts proof serve

# Compile UFO sources -> 01_Branding/*.{otf,woff2}, 02_Internal/*.{ttf,woff2}
fonts:
	$(PYTHON) $(FONT_SOURCES)/build.py

# Render PNG proofs of the built fonts -> 00_Sources/proofs/
proof:
	$(PYTHON) $(FONT_SOURCES)/proof.py

# Serve the repo root (HTML pages that load the fonts) on http://localhost:8000.
# Sends Cache-Control: no-store so edited CSS/JS show up on a normal reload.
serve:
	$(PYTHON) -c 'import http.server as s; h = s.SimpleHTTPRequestHandler; e = h.end_headers; h.end_headers = lambda self: (self.send_header("Cache-Control", "no-store"), e(self))[1]; s.test(HandlerClass=h, port=8000, bind="127.0.0.1")'
