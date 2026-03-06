# igv_streamlit/_viewer_app.py
import os
import sys
from pathlib import Path

# Allow running as a script alongside the package
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import igv_streamlit as st_igv

st.set_page_config(page_title="IGV Viewer", layout="wide")

file_path   = os.environ["SIGV_FILE"]
fmt         = os.environ.get("SIGV_FORMAT", "bam")
genome      = os.environ.get("SIGV_GENOME", "hg38")
index_path  = os.environ.get("SIGV_INDEX", "")
ref         = os.environ.get("SIGV_REF", "")
ref_index   = os.environ.get("SIGV_REF_INDEX", "")
annotation  = os.environ.get("SIGV_ANNOTATION", "")
init_locus  = os.environ.get("SIGV_LOCUS", "all")

st.title(f"IGV — {Path(file_path).name}")

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.subheader("View options")
    locus  = st.text_input("Locus", value=init_locus)
    height = st.slider("Browser height (px)", 300, 1200, 600, 50)

# ── Build reference ───────────────────────────────────────────────────────────
if ref:
    reference_cfg = {"fastaPath" if Path(ref).exists() else "fastaURL": ref}
    if ref_index:
        k = "indexPath" if Path(ref_index).exists() else "indexURL"
        reference_cfg[k] = ref_index
    reference_kwarg = {"reference": reference_cfg}
    genome_kwarg    = {}
else:
    reference_kwarg = {}
    genome_kwarg    = {"genome": genome}

# ── Build tracks ──────────────────────────────────────────────────────────────
tracks = []

if annotation:
    is_local = Path(annotation).exists()
    tracks.append({
        "name":   Path(annotation).name,
        "path" if is_local else "url": annotation,
        "type":   "annotation",
    })

track = {
    "name":   Path(file_path).name,
    "path":   file_path,
    "format": fmt,
    "type":   "alignment",
}
if index_path:
    track["indexPath"] = index_path

tracks.append(track)

# ── Render ────────────────────────────────────────────────────────────────────
st_igv.browser(
    **genome_kwarg,
    **reference_kwarg,
    locus=locus or None,
    tracks=tracks,
    height=height,
    key="cli_browser",
)