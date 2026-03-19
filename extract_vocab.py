"""
extract_vocab.py
One-time script: reads the Latin vocabulary PDF and writes vocabulary.csv.
Uses pdfplumber for coordinate-based extraction so column layout is reliable
regardless of how pdftotext would interpret the page structure.
"""

import csv
import re
import pdfplumber

PDF_PATH = "500 wichtigste lateinische Wörter.pdf"
CSV_PATH = "vocabulary.csv"

# x-coordinate threshold separating Latin (left) from German (right)
GERMAN_X_THRESHOLD = 280

# y-tolerance: words within this many points vertically are on the same line
LINE_TOL = 3

# Skip the title header text
SKIP_PHRASES = {"Die", "500", "wichtigsten", "lateinischen", "Wörter", "W\ufffdter"}


def group_by_line(words, tol=LINE_TOL):
    """Group words into lines based on their vertical (top) position."""
    lines = []
    for word in sorted(words, key=lambda w: (round(w["top"] / tol), w["x0"])):
        top = word["top"]
        if lines and abs(top - lines[-1]["top"]) <= tol:
            lines[-1]["words"].append(word)
        else:
            lines.append({"top": top, "words": [word]})
    return lines


def is_page_header(words):
    """Return True if this line is the page title or page number."""
    texts = {w["text"] for w in words}
    # Page header contains the title words; page number is a bare digit
    if texts & SKIP_PHRASES:
        return True
    if len(words) == 1 and words[0]["text"].isdigit():
        return True
    return False


def extract_pairs(pdf_path):
    """
    Extract (latin, german) pairs from all pages.
    Strategy:
      - For each line on each page, split words at GERMAN_X_THRESHOLD.
      - Left words → Latin fragment; right words → German fragment.
      - Lines that have only a Latin fragment are sub-entries / continuation
        lines; their text is appended to the current Latin entry.
      - Lines that have only a German fragment attach to the current Latin entry.
      - Lines that have both start a new entry.
    """
    entries = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            words = page.extract_words()
            lines = group_by_line(words)

            current_latin = []
            current_german = []

            for line in lines:
                ws = line["words"]
                if is_page_header(ws):
                    continue

                latin_words = [w for w in ws if w["x0"] < GERMAN_X_THRESHOLD]
                german_words = [w for w in ws if w["x0"] >= GERMAN_X_THRESHOLD]

                latin_text = " ".join(w["text"] for w in latin_words).strip()
                german_text = " ".join(w["text"] for w in german_words).strip()

                has_latin = bool(latin_text)
                has_german = bool(german_text)

                if has_latin and has_german:
                    # Save any pending entry before starting a new one
                    if current_latin:
                        entries.append(
                            (" ".join(current_latin), " ".join(current_german))
                        )
                    current_latin = [latin_text]
                    current_german = [german_text]

                elif has_latin and not has_german:
                    # Continuation / sub-entry: append Latin, no German yet
                    current_latin.append(latin_text)

                elif has_german and not has_latin:
                    # German continuation (e.g. wrapped German text)
                    current_german.append(german_text)

            # Flush last entry on each page
            if current_latin:
                entries.append(
                    (" ".join(current_latin), " ".join(current_german))
                )
                current_latin = []
                current_german = []

    return entries


def clean(text):
    """Strip PDF artifacts from extracted text."""
    # □ (U+25A1) is a checkbox/bullet glyph used in the PDF to mark entries
    text = text.replace("\u25a1", "").replace("\ufffd", "")
    return text.strip()


# Matches a gender marker (m./f./n., optionally + Pl. or / f. etc.) only when
# it is followed by end-of-string or an opening parenthesis — not mid-entry text.
_GENDER_RE = re.compile(
    r" ((?:[mfn]\.)(?:\s*/\s*[mfn]\.)?(?:\s+Pl\.?)?)"
    r"(?=\s*(?:$|\())"
)


def format_latin(text):
    """Wrap gender markers in parentheses: 'aetas, -atis f.' → 'aetas, -atis (f.)'"""
    return _GENDER_RE.sub(r" (\1)", text)


def main():
    print(f"Reading {PDF_PATH} …")
    pairs = extract_pairs(PDF_PATH)

    # Filter out entries with no German, or where Latin is a grammar note
    note_prefixes = ("Kompar.", "Superl.", "Gen.:", "Dat.:", "Abl.:")
    pairs = [
        (lat, ger) for lat, ger in pairs
        if lat and ger and not lat.startswith(note_prefixes)
    ]

    print(f"Extracted {len(pairs)} entries. Writing {CSV_PATH} …")

    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["latin", "german"])
        for lat, ger in pairs:
            writer.writerow([format_latin(clean(lat)), clean(ger)])

    print("\nFirst 15 entries:")
    for lat, ger in pairs[:15]:
        print(f"  {clean(lat)!r:50s} -> {clean(ger)!r}")

    print(f"\nDone. {len(pairs)} rows written to {CSV_PATH}")


if __name__ == "__main__":
    main()
