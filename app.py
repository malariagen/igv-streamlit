# app.py

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

    import os
    on_cloud = os.path.exists("/mount/src")

    st.markdown(
        "**This section only works when running Streamlit locally** — for cloud deployments, use remote URLs instead.\n\n"
        "Here we load local genomic files using `path` and `indexPath` instead of `url` and `indexURL`.\n\n"
        "When using local file paths, `igv-streamlit` serves them automatically via a built-in local file server.",
        text_alignment="center",
    )

    if on_cloud:
        st.warning(
            "This demo is running on Streamlit Cloud, which doesn't support local file serving.\n\n"
            "Clone the repo and run `streamlit run app.py` locally to try this feature.\n\n"
            "You can still see the code for this demo by clicking the button below."
        )
    else:
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
                "name":       "PF0883-C.cram (Ghana, 2013)",
                "path":       st_igv.resolve_path("local-data/PF0833-C.filtered.cram"),
                "indexPath":  st_igv.resolve_path("local-data/PF0833-C.filtered.cram.crai"),
                "format":     "cram",
                "type":       "alignment",
            },
            {
                "name":      "SPT24175.bam (Cameroon, 2017)",
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
        { # Note, we are browsing a CRAM file alongside a BAM file
            "name":       "PF0833-C.cram (Ghana, 2013)",
            "path":       st_igv.resolve_path("local-data/PF0833-C.filtered.cram"),
            "indexPath":  st_igv.resolve_path("local-data/PF0833-C.filtered.cram.crai"),
            "format":     "cram",
            "type":       "alignment",
        },
        {
            "name":      "SPT24175.bam (Cameroon, 2017)",
            "path":      st_igv.resolve_path("local-data/SPT24175.filtered.bam"),
            "indexPath": st_igv.resolve_path("local-data/SPT24175.filtered.bam.bai"),
            "format":    "bam",
            "type":      "alignment",
        }
    ]
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
        "Here, we stream CRAM/FASTA/GFF files directly from remote URLs over the internet.\n\n"
        "This requires no local files at all and allows us to browse whole genomes.",
        text_alignment = "center"
    )

    st_igv.browser(
        reference={
            "fastaURL": "https://raw.githubusercontent.com/malariagen/igv-streamlit/master/local-data/PlasmoDB-54_Pfalciparum3D7_Genome.fasta",
        },
        locus = "Pf3D7_07_v3:402,282-406,400",
        tracks=[
            {
                "name":        "GFF annotation",
                "url":         "https://raw.githubusercontent.com/malariagen/igv-streamlit/master/local-data/PlasmoDB-55_Pfalciparum3D7.gff",
                "format":      "gff3",
                "type":        "annotation",
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

    with st.popover("Click to peek at the Python code", width="stretch", type="primary"):
        st.code(
            """
import igv_streamlit as st_igv

# If you see "Error accessing resource: http://127.0.0.1:xxxxx/file/xxxxxxxxxxx Status: 0",
# this is usually due to intermittent outage of the remote server hosting the files. 
# Try refreshing the page, or check the URLs are accessible in your browser.

st_igv.browser(
    reference={
        "fastaURL": "https://raw.githubusercontent.com/malariagen/igv-streamlit/master/local-data/PlasmoDB-54_Pfalciparum3D7_Genome.fasta",
    },
    locus = "Pf3D7_07_v3:401,500-406,500",
    tracks=[
        {
            "name":        "GFF annotation",
            "url":         "https://raw.githubusercontent.com/malariagen/igv-streamlit/master/local-data/PlasmoDB-55_Pfalciparum3D7.gff",
            "format":      "gff3",
            "type":        "annotation",
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
)
""",
            language = "python",
        )

# ═══════════════════════════════════════════════════════════════════════════════
# ADVANCED CONFIG
# ═══════════════════════════════════════════════════════════════════════════════
elif active_tab == TAB_ADVANCED:
    st.sidebar.subheader("Configurations")

    BASE_FASTA = "https://raw.githubusercontent.com/malariagen/igv-streamlit/master/local-data/PlasmoDB-54_Pfalciparum3D7_Genome.fasta"
    BASE_GFF   = "https://raw.githubusercontent.com/malariagen/igv-streamlit/master/local-data/PlasmoDB-55_Pfalciparum3D7.gff"

    SAMPLES = {
        "PF0833-C (Ghana, 2013)": {
            "url":      "https://ftp.sra.ebi.ac.uk/vol1/run/ERR156/ERR15615711/PF0833-C.cram",
            "indexURL": "https://ftp.sra.ebi.ac.uk/vol1/run/ERR156/ERR15615711/PF0833-C.cram.crai",
            "format":   "cram",
        },
        "SPT24175 (Cameroon, 2017)": {
            "url":      "https://ftp.sra.ebi.ac.uk/vol1/run/ERR156/ERR15632643/SPT24175.cram",
            "indexURL": "https://ftp.sra.ebi.ac.uk/vol1/run/ERR156/ERR15632643/SPT24175.cram.crai",
            "format":   "cram",
        },
    }

    LOCI = {
        "CRT":  "Pf3D7_07_v3:403,581-403,659",
        "DHFR": "Pf3D7_04_v3:748,200-749,900",
        "MDR1": "Pf3D7_05_v3:957,890-962,000",
    }

    st.markdown(
        "This page demonstrates how you can integrate Streamlit's UI elements with IGV's configuration to build a custom browser interface.\n\n"
    )

    @st.dialog("IGV Genome Browser", width="large")
    def show_browser():
        # ── Sample & locus ────────────────────────────────────────────────────
        selected_sample = st.radio(
            "Sample",
            list(SAMPLES.keys()),
            horizontal=True,
            key="adv_sample",
        )

        locus_label = st.pills(
            "Locus",
            list(LOCI.keys()),
            default="CRT",
            key="adv_locus",
        )

        st.divider()

        # ── Options: toggles left, sliders right ──────────────────────────────
        col_toggles, col_sliders = st.columns([1, 2])

        with col_toggles:
            show_annotations = st.toggle(
                "GFF annotations", value=True, key="adv_gff"
            )
            display_mode = st.select_slider(
                "Annotation mode",
                options=["COLLAPSED", "EXPANDED", "SQUISHED"],
                value="EXPANDED",
                key="adv_display",
                disabled=not show_annotations,
            )
            view_as_pairs = st.toggle(
                "View as pairs",
                value=False,
                key="adv_pairs",
                help="Draw paired reads connected by a line spanning the insert.",
            )

        with col_sliders:
            browser_height = st.slider(
                "Browser height (px)", 400, 1200, 600, 50,
                key="advanced_height",
            )
            track_height = st.slider(
                "Track height (px)", 50, 500, 200, 25,
                key="adv_track_height",
                help="Total height of the alignment track panel.",
            )
            alignment_row_height = st.slider(
                "Read row height (px)", 4, 30, 14, 1,
                key="adv_row_height",
                help="Height per read row in EXPANDED/FULL mode (alignmentRowHeight).",
            )

        # ── Build config & render ─────────────────────────────────────────────
        tracks = []

        if show_annotations:
            tracks.append({
                "name":        "GFF annotations",
                "url":         BASE_GFF,
                "format":      "gff3",
                "type":        "annotation",
                "displayMode": display_mode,
            })

        tracks.append({
            "name":               selected_sample,
            "type":               "alignment",
            "viewAsPairs":        view_as_pairs,
            "height":             track_height,
            "alignmentRowHeight": alignment_row_height,
            "squishedRowHeight":  max(2, alignment_row_height // 4),
            **SAMPLES[selected_sample],
        })

        st_igv.browser(
            reference={
                "fastaURL":      BASE_FASTA
            },
            locus=LOCI[locus_label],
            tracks=tracks,
            height=browser_height,
            key="advanced_browser",
        )

    if st.button("Browse IGV", type="primary"):
        show_browser()