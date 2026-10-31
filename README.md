# Cloud Scythe Labs Assets

This repo is for storing and referencing all visual assets for the Cloud Scythe Labs
organization, its products and website.

| Path | Contents |
| --- | --- |
| `01_Test_Zone/` | Experiments: beta fonts, social drafts, temp emblems, design-language mockups (`01_5_Mockups/`) |
| `02_Brand_Guidelines/` | Brand Guidelines PDF; `Design_Language/` spec (`CSL_Design_Language.md`) and web tokens (`csl-tokens.css`) |
| `03_Branding_Assets/` | Color palettes, typefaces (`03_02_Typefaces/00_Sources` = editable font sources), emblems, logotypes, lockups, tickers |
| `04_Product_Assets/` | Product brands (ReaCloud) |

## Working locally

Toolchain: `nix develop`, or a Python venv with
`03_Branding_Assets/03_02_Typefaces/00_Sources/requirements.txt`.

| Command | Result |
| --- | --- |
| `make fonts` | Rebuild all fonts from the UFO sources |
| `make proof` | Render PNG glyph proofs of the built fonts |
| `make serve` | Serve the repo at http://localhost:8000 — open `/01_Test_Zone/01_5_Mockups/` to review mockups |

Mockups and pages that load the fonts or SVG masks must be served over HTTP; `file://` blocks them.
Font workflow details: [`03_Branding_Assets/03_02_Typefaces/00_Sources/README.md`](03_Branding_Assets/03_02_Typefaces/00_Sources/README.md).
