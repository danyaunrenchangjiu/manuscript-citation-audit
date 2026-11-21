"""Render a standalone journal distribution for existing direct callers."""

import argparse
import json
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate

from render_report import SONG_FONT, build_pdf, distribution_section, register_fonts, tally_reference_sources


def render_distribution(data, output):
    document = SimpleDocTemplate(str(output), pagesize=A4, leftMargin=32, rightMargin=32,
                                 topMargin=13, bottomMargin=36, title="参考文献分布")
    content = distribution_section(data["references"], document.width - 12)
    build_pdf(document, content, data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--regular-font", type=Path, default=SONG_FONT)
    parser.add_argument("--bold-font", type=Path, default=SONG_FONT)
    args = parser.parse_args()
    register_fonts(args.regular_font, args.bold_font)
    render_distribution(json.loads(args.input.read_text(encoding="utf-8-sig")), args.output)


if __name__ == "__main__":
    main()
