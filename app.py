import os
import json
import streamlit as st

import sys
sys.path.insert(0, os.path.dirname(__file__))
import igv_streamlit as st_igv

st.set_page_config(
    page_title = "igv-streamlit",
    page_icon  = "assets/igv-streamlit-logo.png",
    layout     = "wide"
)

st.logo("assets/igv-streamlit-logo.png", size="large")
st.title("igv-streamlit", text_alignment="center")
st.divider()

# ── Sidebar navigation ────────────────────────────────────────────────────────
st.sidebar.subheader("Navigation")
TAB_WELCOME  = "Welcome page"
TAB_BUILTIN  = "igv.js's built-in hg19 demo"
TAB_LOCAL    = "Local files"
TAB_REMOTE   = "Remote PF8-release"
TAB_ADVANCED = "Advanced config"

active_tab = st.sidebar.radio(
    "Select mode",
    [TAB_WELCOME, TAB_BUILTIN, TAB_LOCAL, TAB_REMOTE, TAB_ADVANCED],
    label_visibility="collapsed",
)
st.sidebar.divider()


# ═══════════════════════════════════════════════════════════════════════════════
# WELCOME
# ═══════════════════════════════════════════════════════════════════════════════
if active_tab == TAB_WELCOME:
    st.markdown(
        "igv-streamlit is an unofficial Streamlit component for embedding the [IGV](https://igv.org/) genome browser into your Streamlit apps.\n\n"
        "It provides support for files through both local file paths and remote URLs.\n\n"
        "Choose a mode in the sidebar to see how you can use igv-streamlit to embed IGV in your genomics apps!\n\n"
        "Brought to you by [MalariaGEN](https://www.malariagen.net/).",
        text_alignment="center",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# BUILT-IN HG19 DEMO
# ═══════════════════════════════════════════════════════════════════════════════
elif active_tab == TAB_BUILTIN:
    st.sidebar.subheader("Configurations")
    browser_height = st.sidebar.slider("Browser height (px)", 400, 1200, 400, 50, key="builtin_height")

    st.markdown(
        "Here we access IGV's hg19 demo via URL. All the usual interactive features of IGV are available. "
        "Note the fullscreen button in the top-right.",
        text_alignment="center",
    )

    st_igv.browser(
        genome="hg19",
        locus="chr22:24,376,166-24,376,456",
        tracks=[
            {
                "name":     "NA12878 - chr22 (demo)",
                "url":      "https://s3.amazonaws.com/igv.org.demo/gstt1_sample.bam",
                "indexURL": "https://s3.amazonaws.com/igv.org.demo/gstt1_sample.bam.bai",
                "format":   "bam",
                "type":     "alignment",
            }
        ],
        height=browser_height,
        key="builtin_demo",
    )

    with st.popover("Click to peek at the Python code", width="stretch", type="primary"):
        st.code(
            """
import igv_streamlit as st_igv

st_igv.browser(
    genome = "hg19",
    locus  = "chr22:24,376,166-24,376,456",
    tracks = [
        {
            "name"    : "NA12878 - chr22 (demo)",
            "url"     : "https://s3.amazonaws.com/igv.org.demo/gstt1_sample.bam",
            "indexURL": "https://s3.amazonaws.com/igv.org.demo/gstt1_sample.bam.bai",
            "format"  : "bam",
            "type"    : "alignment",
        }
    ],
)
""",
            language="python",
        )


# ═══════════════════════════════════════════════════════════════════════════════
# LOCAL FILES
# ═══════════════════════════════════════════════════════════════════════════════
elif active_tab == TAB_LOCAL:
    # Show you can do multiple files. Get a different BAM
    st.sidebar.subheader("Local files config")
    browser_height = st.sidebar.slider("Browser height (px)", 400, 1200, 500, 50, key="local_height")

    DATA_DIR = os.path.join(os.path.dirname(__file__), "local-data")

    if not os.path.isdir(DATA_DIR):
        st.error(
            f"No `local-data/` directory found at `{DATA_DIR}`. "
            "Please create it and add your genomic files."
        )
        st.stop()

    fasta_files = sorted(
        f for f in os.listdir(DATA_DIR)
        if f.endswith((".fasta", ".fa", ".fna")) and not f.endswith(".fai")
    )
    gff_files = sorted(
        f for f in os.listdir(DATA_DIR)
        if f.endswith((".gff", ".gff3", ".gtf"))
    )
    bam_files = sorted(
        f for f in os.listdir(DATA_DIR)
        if f.endswith((".bam", ".cram")) and not f.endswith((".bai", ".crai"))
    )

    st.sidebar.subheader("Reference")
    selected_fasta = st.sidebar.selectbox("FASTA reference", fasta_files, key="local_fasta") if fasta_files else None
    selected_gff   = st.sidebar.selectbox("Annotation (GFF)", gff_files, key="local_gff")

    st.sidebar.subheader("Alignment tracks")
    selected_bams = st.sidebar.multiselect("BAM / CRAM files", bam_files, default=bam_files[:1], key="local_bams")

    locus = st.sidebar.text_input("Locus", "Pf3D7_07_v3:400,251-408,852", key="local_locus")

    st.subheader("Local files")

    if not fasta_files:
        st.info("No FASTA files found in `local-data/`. Add a reference to enable the browser.")
        st.stop()

    fasta_path       = os.path.join(DATA_DIR, selected_fasta)
    fai_path         = fasta_path + ".fai"
    reference_config = {
        "fastaPath": fasta_path,
        "name":      selected_fasta,
        **({"indexPath": fai_path} if os.path.isfile(fai_path) else {}),
    }

    track_configs = []

    if selected_gff != "(none)":
        track_configs.append({
            "name":             selected_gff,
            "path":             os.path.join(DATA_DIR, selected_gff),
            "format":           "gff3",
            "type":             "annotation",
            "displayMode":      "EXPANDED",
            "visibilityWindow": 500_000,
        })

    for bam in selected_bams:
        bam_path = os.path.join(DATA_DIR, bam)
        fmt      = "cram" if bam.endswith(".cram") else "bam"
        idx_ext  = ".crai" if fmt == "cram" else ".bai"
        idx_path = bam_path + idx_ext
        track    = {
            "name":   bam,
            "path":   bam_path,
            "format": fmt,
            "type":   "alignment",
        }
        if os.path.isfile(idx_path):
            track["indexPath"] = idx_path
        if fmt == "cram":
            track["sourceType"] = "file"
        track_configs.append(track)

    st_igv.browser(
        reference=reference_config,
        locus=locus or None,
        tracks=track_configs if track_configs else None,
        height=browser_height,
        key="local_browser",
    )

    with st.expander("Python code (generated)"):
        st.code(
            f"""
import igv_streamlit as st_igv

st_igv.browser(
    reference={{
        "fastaPath": "local-data/{selected_fasta}",
        "indexPath": "local-data/{selected_fasta}.fai",
        "name":      "{selected_fasta}",
    }},
    locus="{locus}",
    tracks=[{{
        "name":      "PF0833-C",
        "path":      "local-data/PF0833-C.filtered.cram",
        "indexPath": "local-data/PF0833-C.filtered.cram.crai",
        "format":    "cram",
        "type":      "alignment",
    }}],
)
""",
            language="python",
        )


# ═══════════════════════════════════════════════════════════════════════════════
# REMOTE PF8-RELEASE
# ═══════════════════════════════════════════════════════════════════════════════
elif active_tab == TAB_REMOTE:
    st.sidebar.subheader("Remote PF8 config")
    browser_height = st.sidebar.slider("Browser height (px)", 400, 1200, 500, 50, key="remote_height")
    locus          = st.sidebar.text_input("Locus", "Pf3D7_01_v3:1-100000", key="remote_locus")
    sample_id      = st.sidebar.text_input("Sample ID", "PF0833-C", key="remote_sample")

    st.subheader("Remote PF8-release files (Sanger COG bucket)")
    st.write(
        "Streams CRAM/FASTA/GFF directly from "
        "`pf8-release.cog.sanger.ac.uk` — no local data needed."
    )

    BASE = "https://pf8-release.cog.sanger.ac.uk"

    st_igv.browser(
        reference={
            "fastaURL": f"{BASE}/reference/PlasmoDB-54-Pfalciparum3D7-Genome.fasta",
            "name":     "PlasmoDB-54 Pf3D7",
        },
        locus=locus or None,
        tracks=[
            {
                "name":             "Annotation",
                "url":              f"{BASE}/annotations/PlasmoDB-55_Pfalciparum3D7.gff.gz",
                "format":           "gff3",
                "type":             "annotation",
                "displayMode":      "EXPANDED",
                "visibilityWindow": 500_000,
            },
            {
                "name":     sample_id,
                "url":      "https://ftp.sra.ebi.ac.uk/vol1/run/ERR156/ERR15615711/PF0833-C.cram",
                "indexURL": "https://ftp.sra.ebi.ac.uk/vol1/run/ERR156/ERR15615711/PF0833-C.cram.crai",
                "format":   "cram",
                "type":     "alignment",
            },
        ],
        height=browser_height,
        key="remote_browser",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ADVANCED CONFIG
# ═══════════════════════════════════════════════════════════════════════════════
elif active_tab == TAB_ADVANCED:
    st.sidebar.subheader("Advanced config")
    browser_height = st.sidebar.slider("Browser height (px)", 400, 1200, 500, 50, key="advanced_height")

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

    raw = st.sidebar.text_area("IGV config (JSON)", default_config, height=260, key="advanced_config")

    st.subheader("Advanced – paste a raw IGV config")
    st.write(
        "Paste any valid [igv.js browser config](https://github.com/igvteam/igv.js/wiki/Browser-Configuration) "
        "as JSON. Use `url`/`indexURL` for remote files."
    )

    try:
        config_dict = json.loads(raw)
    except json.JSONDecodeError as exc:
        st.error(f"Invalid JSON: {exc}")
        st.stop()

    genome    = config_dict.pop("genome",    None)
    reference = config_dict.pop("reference", None)
    locus     = config_dict.pop("locus",     None)
    tracks    = config_dict.pop("tracks",    None)

    st_igv.browser(
        genome=genome,
        reference=reference,
        locus=locus,
        tracks=tracks,
        height=browser_height,
        key="advanced_browser",
        **config_dict,
    )