# igv-streamlit

An unofficial Streamlit component for [IGV (Integrative Genomics Viewer)](https://github.com/igvteam/igv.js).

Supports both **local files** (served via a built-in CORS HTTP server) and **remote URLs** — no additional servers or configuration required.

---

## Installation

```bash
pip install igv-streamlit
```

Or from source:

```bash
git clone https://github.com/yourname/igv-streamlit
pip install -e igv-streamlit/
```

## Quick start

```python
import igv_streamlit as sigv

# Built-in genome + remote BAM
sigv.igv_browser(
    genome="hg38",
    locus="BRCA1",
    tracks=[{
        "name": "Sample",
        "url":      "https://example.com/sample.bam",
        "indexURL": "https://example.com/sample.bam.bai",
        "type": "alignment",
    }],
)
```

## Local files

Use `path` / `indexPath` / `fastaPath` instead of `url` / `indexURL` / `fastaURL` for local files.  
The component automatically starts a CORS-enabled HTTP server and rewrites the paths to localhost URLs that igv.js can fetch.

```python
import igv_streamlit as sigv

sigv.igv_browser(
    reference={
        "fastaPath": "/data/PlasmoDB-54_Pfalciparum3D7_Genome.fasta",
        "indexPath": "/data/PlasmoDB-54_Pfalciparum3D7_Genome.fasta.fai",
        "name": "Pf3D7",
    },
    locus="Pf3D7_01_v3:1-100000",
    tracks=[
        {
            "name": "Annotation",
            "path":   "/data/PlasmoDB-55_Pfalciparum3D7.gff",
            "format": "gff3",
            "type":   "annotation",
        },
        {
            "name":      "PF0833-C CRAM",
            "path":      "/data/PF0833-C.filtered.cram",
            "indexPath": "/data/PF0833-C.filtered.cram.crai",
            "format":    "cram",
            "type":      "alignment",
        },
        {
            "name":      "PF0833-C BAM",
            "path":      "/data/PF0833-C.filtered.bam",
            "indexPath": "/data/PF0833-C.filtered.bam.bai",
            "format":    "bam",
            "type":      "alignment",
        },
    ],
)
```

### Path ↔ URL property mapping

| Local file property | igv.js URL property |
|---------------------|---------------------|
| `path`              | `url`               |
| `indexPath`         | `indexURL`          |
| `fastaPath`         | `fastaURL`          |
| `cytobandPath`      | `cytobandURL`       |
| `aliasPath`         | `aliasURL`          |

## Remote files (PF8-release example)

```python
import igv_streamlit as sigv

BASE = "https://pf8-release.cog.sanger.ac.uk"

sigv.igv_browser(
    reference={
        "fastaURL": f"{BASE}/reference/PlasmoDB-54-Pfalciparum3D7-Genome.fasta",
        "name": "PlasmoDB-54 Pf3D7",
    },
    locus="Pf3D7_01_v3:1-100000",
    tracks=[
        {
            "name": "Annotation",
            "url":    f"{BASE}/annotations/PlasmoDB-55_Pfalciparum3D7.gff.gz",
            "format": "gff3",
            "type":   "annotation",
        },
        {
            "name":     "PF0833-C",
            "url":      f"{BASE}/cram/PF0833-C.cram",
            "indexURL": f"{BASE}/cram/PF0833-C.cram.crai",
            "format":   "cram",
            "type":     "alignment",
        },
    ],
)
```

## API reference

### `sigv.igv_browser(...)`

| Parameter        | Type              | Description |
|-----------------|-------------------|-------------|
| `genome`        | `str \| dict`     | Built-in genome ID (`"hg38"`, `"mm10"`, …) or reference dict |
| `reference`     | `dict`            | Custom reference config with `fastaURL`/`fastaPath` |
| `locus`         | `str`             | Initial locus (`"chr1:1000-2000"` or gene name) |
| `tracks`        | `list[dict]`      | List of igv.js track config objects |
| `height`        | `int`             | Browser height in pixels (default: `500`) |
| `key`           | `str`             | Streamlit component key for multiple browsers |
| `on_locus_change` | `callable`      | Callback when the user navigates |

Returns a Streamlit component result; access `result.locus` for the current locus string.

## Running the demo app

```bash
git clone https://github.com/yourname/igv-streamlit
cd igv-streamlit
pip install -r requirements.txt

# optionally place genomic files in data/
mkdir -p data
# cp /path/to/*.bam data/ ...

streamlit run app.py
```

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  Streamlit app (Python)                             │
│                                                     │
│  igv_streamlit.igv_browser(reference=..., tracks=…) │
│    │                                                │
│    ├─ local path? → register_file(path)             │
│    │                  → http://127.0.0.1:PORT/file/TOKEN
│    │                                                │
│    └─ st.components.v2.component(data={config})     │
│         │                                           │
│         ▼                                           │
│  ┌─────────────────────────────────────┐           │
│  │  igv.js (loaded from CDN)           │           │
│  │  runs in main Streamlit page        │           │
│  │  fetches files via HTTP             │           │
│  │   remote → directly                │           │
│  │   local  → 127.0.0.1:PORT/file/…   │           │
│  └─────────────────────────────────────┘           │
│         │                                           │
│  locus changes → result.locus (Python)              │
└─────────────────────────────────────────────────────┘
```

## Security note

The built-in file server only serves files that have been explicitly registered via `path`/`indexPath`/`fastaPath` properties. It **does not** expose arbitrary filesystem paths.

## License

MIT
