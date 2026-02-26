"""
app.py - demonstration of the igv-streamlit component.

Run with:
    streamlit run app.py
"""

import os
import streamlit as st

import sys
sys.path.insert(0, os.path.dirname(__file__))
import igv_streamlit as st_igv

st.set_page_config(
    page_title = "igv-streamlit",
    page_icon  = "assets/igv-streamlit-logo.png",
    layout     = "wide"
)

st.title("igv-streamlit", text_alignment="center")
st.caption(
    "An unofficial Streamlit component for embedding the igv.js genome browser. "
    "Brought to you by [MalariaGEN](https://www.malariagen.net/). "
    "Powered by [igv.js](https://github.com/igvteam/igv.js)",
    text_alignment="center"
)
st.divider()

st.sidebar.header("Modes of operation")

MODE_BUILTIN  = "Built-in genome (hg19 demo)"
MODE_LOCAL    = "Local files (data/ directory)"
MODE_REMOTE   = "Remote PF8-release files"
MODE_ADVANCED = "Advanced / manual config"

mode = st.sidebar.radio(
    "Data source",
    [MODE_BUILTIN, MODE_LOCAL, MODE_REMOTE, MODE_ADVANCED],
)

browser_height = st.sidebar.slider("Browser height (px)", 300, 900, 500, 50)


# ═══════════════════════════════════════════════════════════════════════════════
# MODE 1 – built-in hg19 demo
# ═══════════════════════════════════════════════════════════════════════════════
if mode == MODE_BUILTIN:
    st.subheader("Built-in genome demo (hg19)")
    st.write(
        "Uses IGV's hosted hg19 reference with a public BAM file from Broad Institute. "
        "No local data required."
    )

    locus = st.text_input("Locus", "chr22:24,376,166-24,376,456")

    st_igv.igv_browser(
        genome="hg19",
        locus=locus,
        tracks=[
            {
                "name": "NA12878 – chr22 (demo)",
                "url": "https://s3.amazonaws.com/igv.org.demo/gstt1_sample.bam",
                "indexURL": "https://s3.amazonaws.com/igv.org.demo/gstt1_sample.bam.bai",
                "format": "bam",
                "type": "alignment",
            }
        ],
        height=browser_height,
        key="builtin_demo",
    )

    with st.expander("Python code"):
        st.code(
            """
import igv_streamlit as sigv

sigv.igv_browser(
    genome="hg19",
    locus="chr22:24,376,166-24,376,456",
    tracks=[{
        "name": "NA12878",
        "url": "https://s3.amazonaws.com/igv.org.demo/gstt1_sample.bam",
        "indexURL": "https://s3.amazonaws.com/igv.org.demo/gstt1_sample.bam.bai",
        "format": "bam",
        "type": "alignment",
    }],
)
""",
            language="python",
        )


# ═══════════════════════════════════════════════════════════════════════════════
# MODE 2 – local data/ directory
# ═══════════════════════════════════════════════════════════════════════════════
elif mode == MODE_LOCAL:
    st.subheader("Local files")

    DATA_DIR = os.path.join(os.path.dirname(__file__), "local-data")

    if not os.path.isdir(DATA_DIR):
        st.error(
            f"No `data/` directory found at `{DATA_DIR}`. "
            "Please create it and add your genomic files."
        )
        st.stop()

    st.sidebar.subheader("Reference")

    fasta_files = [
        f for f in os.listdir(DATA_DIR)
        if f.endswith((".fasta", ".fa", ".fna")) and not f.endswith(".fai")
    ]
    gff_files = [
        f for f in os.listdir(DATA_DIR)
        if f.endswith((".gff", ".gff3", ".gtf"))
    ]

    selected_fasta = st.sidebar.selectbox("FASTA reference", ["(none)"] + fasta_files)
    selected_gff   = st.sidebar.selectbox("Annotation (GFF)", ["(none)"] + gff_files)

    st.sidebar.subheader("Alignment tracks")

    bam_files = [
        f for f in os.listdir(DATA_DIR)
        if f.endswith((".bam", ".cram")) and not f.endswith((".bai", ".crai"))
    ]
    selected_bams = st.sidebar.multiselect("BAM / CRAM files", bam_files, default=bam_files[:1])

    locus = st.text_input("Locus", "Pf3D7_01_v3:1-100000")

    reference_config = None
    if selected_fasta != "(none)":
        fasta_path = os.path.join(DATA_DIR, selected_fasta)
        fai_path   = fasta_path + ".fai"
        reference_config = {
            "fastaPath": fasta_path,
            **({"indexPath": fai_path} if os.path.isfile(fai_path) else {}),
            "name": selected_fasta,
        }

    track_configs = []

    if selected_gff != "(none)" and reference_config is not None:
        track_configs.append({
            "name": selected_gff,
            "path": os.path.join(DATA_DIR, selected_gff),
            "format": "gff3",
            "type": "annotation",
            "displayMode": "EXPANDED",
            "visibilityWindow": 500_000,
        })

    for bam in selected_bams:
        bam_path = os.path.join(DATA_DIR, bam)
        fmt      = "cram" if bam.endswith(".cram") else "bam"
        idx_ext  = ".crai" if fmt == "cram" else ".bai"
        idx_path = bam_path + idx_ext
        track = {
            "name": bam,
            "path": bam_path,
            "format": fmt,
            "type": "alignment",
        }
        if os.path.isfile(idx_path):
            track["indexPath"] = idx_path
        if fmt == "cram" and reference_config:
            track["sourceType"] = "file"
        track_configs.append(track)

    if not reference_config:
        st.info("Select a FASTA reference in the sidebar to enable the browser.")
    else:
        st_igv.igv_browser(
            reference=reference_config,
            locus=locus or None,
            tracks=track_configs if track_configs else None,
            height=browser_height,
            key="local_browser",
        )

    with st.expander("Python code (generated)"):
        st.code(
            f"""
import igv_streamlit as sigv

sigv.igv_browser(
    reference={{
        "fastaPath": "data/{selected_fasta}",
        "indexPath": "data/{selected_fasta}.fai",
        "name": "{selected_fasta}",
    }},
    locus="{locus}",
    tracks=[{{
        "name": "PF0833-C",
        "path":      "data/PF0833-C.filtered.cram",
        "indexPath": "data/PF0833-C.filtered.cram.crai",
        "format": "cram",
        "type": "alignment",
    }}],
)
""",
            language="python",
        )


# ═══════════════════════════════════════════════════════════════════════════════
# MODE 3 – remote PF8-release files
# ═══════════════════════════════════════════════════════════════════════════════
elif mode == MODE_REMOTE:
    st.subheader("Remote PF8-release files (Sanger COG bucket)")
    st.write(
        "Streams CRAM/FASTA/GFF directly from "
        "`pf8-release.cog.sanger.ac.uk` — no local data needed."
    )

    BASE = "https://pf8-release.cog.sanger.ac.uk"

    locus     = st.text_input("Locus", "Pf3D7_01_v3:1-100000")
    sample_id = st.text_input("Sample ID", "PF0833-C")

    st_igv.igv_browser(
        reference={
            "fastaURL": f"{BASE}/reference/PlasmoDB-54-Pfalciparum3D7-Genome.fasta",
            "name": "PlasmoDB-54 Pf3D7",
        },
        locus=locus or None,
        tracks=[
            {
                "name": "Annotation",
                "url": f"{BASE}/annotations/PlasmoDB-55_Pfalciparum3D7.gff.gz",
                "format": "gff3",
                "type": "annotation",
                "displayMode": "EXPANDED",
                "visibilityWindow": 500_000,
            },
            {
                "name": sample_id,
                "url":      "https://ftp.sra.ebi.ac.uk/vol1/run/ERR156/ERR15606936/PF0833-C.cram",
                "indexURL": "https://ftp.sra.ebi.ac.uk/vol1/run/ERR156/ERR15606936/PF0833-C.cram.crai",
                "format": "cram",
                "type": "alignment",
            },
        ],
        height=browser_height,
        key="remote_browser",
    )

    with st.expander("Python code"):
        st.code(
            f"""
import igv_streamlit as sigv

BASE = "https://pf8-release.cog.sanger.ac.uk"

sigv.igv_browser(
    reference={{
        "fastaURL": f"{{BASE}}/reference/PlasmoDB-54-Pfalciparum3D7-Genome.fasta",
        "name": "PlasmoDB-54 Pf3D7",
    }},
    locus="Pf3D7_01_v3:1-100000",
    tracks=[
        {{
            "name": "Annotation",
            "url": f"{{BASE}}/annotations/PlasmoDB-55_Pfalciparum3D7.gff.gz",
            "format": "gff3",
            "type": "annotation",
        }},
        {{
            "name": "PF0833-C",
            "url":      f"{{BASE}}/cram/PF0833-C.cram",
            "indexURL": f"{{BASE}}/cram/PF0833-C.cram.crai",
            "format": "cram",
            "type": "alignment",
        }},
    ],
)
""",
            language="python",
        )


# ═══════════════════════════════════════════════════════════════════════════════
# MODE 4 – advanced / paste raw JSON config
# ═══════════════════════════════════════════════════════════════════════════════
elif mode == MODE_ADVANCED:
    st.subheader("Advanced – paste a raw IGV config")
    st.write(
        "Paste any valid [igv.js browser config](https://github.com/igvteam/igv.js/wiki/Browser-Configuration) "
        "as JSON. Use `url`/`indexURL` for remote files."
    )

    default_config = """{
  "genome": "hg38",
  "locus": "BRCA1",
  "tracks": [
    {
      "name": "BRCA1 region",
      "url": "https://s3.amazonaws.com/igv.org.test/data/gencode.v18.collapsed.bed",
      "format": "bed",
      "type": "annotation"
    }
  ]
}"""

    raw = st.text_area("IGV config (JSON)", default_config, height=260)

    import json

    try:
        config_dict = json.loads(raw)
    except json.JSONDecodeError as exc:
        st.error(f"Invalid JSON: {exc}")
        st.stop()

    genome    = config_dict.pop("genome", None)
    reference = config_dict.pop("reference", None)
    locus     = config_dict.pop("locus", None)
    tracks    = config_dict.pop("tracks", None)

    st_igv.igv_browser(
        genome=genome,
        reference=reference,
        locus=locus,
        tracks=tracks,
        height=browser_height,
        key="advanced_browser",
        **config_dict,
    )


# ── footer ────────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    "igv-streamlit wraps [igv.js](https://github.com/igvteam/igv.js) "
    "using Streamlit's v2 component API. Local files are served via a "
    "built-in CORS HTTP server running on localhost."
)