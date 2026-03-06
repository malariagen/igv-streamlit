# igv_streamlit/cli.py
from __future__ import annotations
import argparse
import os
import subprocess
import sys
from pathlib import Path

_VIEWER = Path(__file__).parent / "_viewer_app.py"

_FORMAT_DEFAULTS = {
    ".bam":  "bam",
    ".cram": "cram",
    ".vcf":  "vcf",
    ".vcf.gz": "vcf",
    ".bed":  "bed",
}

def main():
    parser = argparse.ArgumentParser(
        prog="igv-streamlit",
        description="Quickly browse a genomic file in IGV via Streamlit.",
    )
    parser.add_argument("file", help="Path to BAM/CRAM/VCF/BED file")
    parser.add_argument("--index",      help="Path to index file (auto-detected if omitted)")
    parser.add_argument("--genome",     default="hg38",
                        help="Built-in genome ID, e.g. hg38, hg19, mm10 (default: hg38)")
    parser.add_argument("--ref",        help="Path or URL to reference FASTA (overrides --genome)")
    parser.add_argument("--ref-index",  help="Path or URL to reference FASTA index (.fai)")
    parser.add_argument("--annotation", help="Path or URL to annotation file (GFF/BED/GTF)")
    parser.add_argument("--locus",      default="all", help="Initial locus (default: all)")
    parser.add_argument("--port",       default="8501", help="Streamlit port (default: 8501)")
    args = parser.parse_args()

    file_path = str(Path(args.file).resolve())
    suffix = "".join(Path(args.file).suffixes).lower()
    fmt = _FORMAT_DEFAULTS.get(suffix, "bam")

    # Auto-detect index
    index_path = args.index
    if not index_path:
        for candidate in [file_path + ".bai", file_path + ".crai", file_path + ".tbi"]:
            if Path(candidate).exists():
                index_path = candidate
                break

    env = {
        **os.environ,
        "SIGV_FILE":       file_path,
        "SIGV_FORMAT":     fmt,
        "SIGV_GENOME":     args.genome,
        "SIGV_LOCUS":      args.locus,
        "SIGV_INDEX":      index_path or "",
        "SIGV_REF":        args.ref or "",
        "SIGV_REF_INDEX":  args.ref_index or "",
        "SIGV_ANNOTATION": args.annotation or "",
    }

    subprocess.run(
        [
            sys.executable, "-m", "streamlit", "run",
            str(_VIEWER),
            "--server.port", args.port,
            "--server.headless", "false",
        ],
        env=env,
    )