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
TAB_REMOTE   = "Remote URLs"
TAB_ADVANCED = "Integrating IGV with Streamlit"

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
        "`igv-streamlit` is an unofficial Streamlit component for embedding the [IGV](https://igv.org/) genome browser into your Streamlit apps.\n\n"
        "You can use it to browse genomic files -- both through local file paths and remote URLs.\n\n"
        "This app serves as a complete documentation for how to use `igv-streamlit`. Choose a mode in the sidebar to get started!\n\n"
        "Brought to you by [MalariaGEN](https://www.malariagen.net/).",
        text_alignment="center",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# BUILT-IN HG19 DEMO
# ═══════════════════════════════════════════════════════════════════════════════
elif active_tab == TAB_BUILTIN:
    st.sidebar.subheader("Configurations")
    browser_height = st.sidebar.slider("Browser height (px)", 300, 700, 400, 50, key = "builtin_height")

    st.markdown(
        "Here we access IGV's hg19 demo via URL. All the usual interactive features of IGV are available.\n\n"
        "Note the fullscreen button in the top-right, and that the demo file only has a limited region available.",
        text_alignment = "center",
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
    genome = "hg19", # Using IGV's built-in hg19 reference genome
    locus  = "chr22:24,376,166-24,376,456",
    tracks = [
        {
            "name"    : "NA12878 - chr22 (demo)",
            "url"     : "https://s3.amazonaws.com/igv.org.demo/gstt1_sample.bam", # Note the URL, not path!
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
    st.sidebar.subheader("Configurations")
    browser_height = st.sidebar.slider("Browser height (px)", 400, 1200, 900, 50, key="local_height")

    st.markdown(
        "Here we load local genomic files using `path` and `indexPath` instead of `url` and `indexURL`.\n\n"
        "Note, these demo files only cover a small region of the genome since they need to fit on the repo, but you can use full-sized files.\n\n"
        "When using local file paths, we must resolve relative paths to absolute paths using `st_igv.resolve_path()`.\n\n"
        "`igv-streamlit` then serves them automatically via a built-in local file server. ",
        text_alignment="center",
    )

    st_igv.browser(
        reference={
            "fastaPath": st_igv.resolve_path("local-data/PlasmoDB-54_Pfalciparum3D7_Genome.fasta"),
            "indexPath": st_igv.resolve_path("local-data/PlasmoDB-54_Pfalciparum3D7_Genome.fasta.fai")
        },
        locus="Pf3D7_07_v3:401,500-407,000",
        tracks=[
            {
                "name":    "GFF annotations",
                "path":    st_igv.resolve_path("local-data/PlasmoDB-55_Pfalciparum3D7.gff"),
                "format": "gff3",
                "type":   "annotation",
            },
            {
            "name":       "PF0883-C (Ghana, 2013)",
            "path":       st_igv.resolve_path("local-data/PF0833-C.filtered.cram"),
            "indexPath":  st_igv.resolve_path("local-data/PF0833-C.filtered.cram.crai"),
            "format":     "cram",
            "type":       "alignment",
        },
        {
            "name":      "SPT24175 (Cameroon, 2017)",
            "path":      st_igv.resolve_path("local-data/SPT24175.filtered.bam"),
            "indexPath": st_igv.resolve_path("local-data/SPT24175.filtered.bam.bai"),
            "format":    "bam",
            "type":      "alignment",
        }
        ],
        height = browser_height,
        key    = "local_browser",
    )

    with st.popover("Click to peek at the Python code", width="stretch", type="primary"):
        st.code(
            """
import igv_streamlit as st_igv

st_igv.browser(
    reference={
        "fastaPath": st_igv.resolve_path("local-data/PlasmoDB-54_Pfalciparum3D7_Genome.fasta"),
        "indexPath": st_igv.resolve_path("local-data/PlasmoDB-54_Pfalciparum3D7_Genome.fasta.fai")
                # `st_igv.resolve_path()` converts relative paths to absolute, anchored to this script —
                # so they work regardless of which directory Streamlit was launched from.

                # Alternatively, provide absolute paths, e.g., "/Users/me/Downloads/SPT24175.filtered.bam"
    },
    locus="Pf3D7_07_v3:402,000-406,700",
    tracks=[
        {
            "path":    st_igv.resolve_path("local-data/PlasmoDB-55_Pfalciparum3D7.gff"),
            "format": "gff3",
            "type":   "annotation",
        },
        {
            "name":       "PF0833-C (Ghana, 2013)",
            "path":       st_igv.resolve_path("local-data/PF0833-C.filtered.cram"),
            "indexPath":  st_igv.resolve_path("local-data/PF0833-C.filtered.cram.crai"),
            "format":     "cram",
            "type":       "alignment",
        },
        {
            "name":      "SPT24175 (Cameroon, 2017)",
            "path":      st_igv.resolve_path("local-data/SPT24175.filtered.bam"),
            "indexPath": st_igv.resolve_path("local-data/SPT24175.filtered.bam.bai"),
            "format":    "bam",
            "type":      "alignment",
        }
    ],
    height = browser_height,
    key    = "local_browser",
)
""",
            language="python",
        )


# ═══════════════════════════════════════════════════════════════════════════════
# REMOTE URLS
# ═══════════════════════════════════════════════════════════════════════════════
elif active_tab == TAB_REMOTE:
    st.sidebar.subheader("Configurations")
    browser_height = st.sidebar.slider("Browser height (px)", 400, 1200, 900, 50, key="remote_height")

    st.markdown(
        "Here, we stream CRAM/FASTA/GFF files directly from remote URLs over the internet, requiring no local files at all.\n\n",
        text_alignment = "center"
    )

    st_igv.browser(
        reference={
            "fastaURL": "https://raw.githubusercontent.com/malariagen/igv-streamlit/master/local-data/PlasmoDB-54_Pfalciparum3D7_Genome.fasta",
        },
        locus = "Pf3D7_07_v3:400,000-410,000",
        tracks=[
            {
                "name":             "GFF annotation",
                "url":              "https://raw.githubusercontent.com/malariagen/igv-streamlit/master/local-data/PlasmoDB-55_Pfalciparum3D7.gff",
                "format":           "gff3",
                "type":             "annotation",
                "displayMode":      "EXPANDED",
            },
            {
                "name":     "PF0833-C (Ghana, 2013)",
                "url":      "https://ftp.sra.ebi.ac.uk/vol1/run/ERR156/ERR15615711/PF0833-C.cram",
                "indexURL": "https://ftp.sra.ebi.ac.uk/vol1/run/ERR156/ERR15615711/PF0833-C.cram.crai",
                "format":   "cram",
                "type":     "alignment",
            },
            {
                "name":     "SPT24175 (Cameroon, 2017)",
                "url":      "https://ftp.sra.ebi.ac.uk/vol1/run/ERR156/ERR15632643/SPT24175.cram",
                "indexURL": "https://ftp.sra.ebi.ac.uk/vol1/run/ERR156/ERR15632643/SPT24175.cram.crai",
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

    st_igv.igv_browser(
        genome=genome,
        reference=reference,
        locus=locus,
        tracks=tracks,
        height=browser_height,
        key="advanced_browser",
        **config_dict,
    )
