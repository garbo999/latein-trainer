"""
generate_sentences.py
One-time script: generates a short Latin example sentence for each vocabulary
entry and saves results to sentences.json.

Resumable: already-generated entries are skipped on re-run.
Uses claude-haiku-4-5 (fast and cheap for 569 short generations).
"""

import csv
import json
import os
import time
import anthropic

CSV_PATH = "vocabulary.csv"
OUTPUT_PATH = "sentences.json"

SYSTEM_PROMPT = (
    "You are a Latin teacher. For each vocabulary item given, produce exactly one "
    "short, simple Latin example sentence (5–12 words) that naturally uses the word. "
    "The sentence should be appropriate for a high-school student preparing for their "
    "Abitur exam. Reply with ONLY the Latin sentence — no translation, no explanation, "
    "no quotation marks, no punctuation other than the sentence-final period."
)


def load_existing(path: str) -> dict:
    """Load already-generated sentences from the output file."""
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_vocab(path: str) -> list[dict]:
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append({"latin": row["latin"], "german": row["german"]})
    return rows


def make_prompt(latin: str, german: str) -> str:
    return (
        f"Latin vocabulary entry:\n"
        f"  Latin:  {latin}\n"
        f"  German: {german}\n\n"
        f"Write one short Latin example sentence using this word."
    )


def generate_sentence(client: anthropic.Anthropic, latin: str, german: str) -> str:
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=128,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": make_prompt(latin, german)}],
    )
    return response.content[0].text.strip()


def main():
    vocab = load_vocab(CSV_PATH)
    sentences = load_existing(OUTPUT_PATH)

    # Determine which entries still need generation
    todo = [v for v in vocab if v["latin"] not in sentences]
    total = len(vocab)
    done_start = total - len(todo)

    print(f"Total entries : {total}")
    print(f"Already done  : {done_start}")
    print(f"To generate   : {len(todo)}")
    print()

    if not todo:
        print("All sentences already generated. Nothing to do.")
        return

    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

    errors = 0
    for i, entry in enumerate(todo, start=1):
        latin = entry["latin"]
        german = entry["german"]
        overall = done_start + i

        try:
            sentence = generate_sentence(client, latin, german)
            sentences[latin] = sentence

            # Save after every entry so progress is never lost
            save(OUTPUT_PATH, sentences)

            # Progress line (ASCII-safe to avoid Windows cp1252 issues)
            latin_safe = latin.encode("ascii", errors="replace").decode("ascii")
            print(f"[{overall:3d}/{total}] {latin_safe[:50]:<50s}  OK")

        except anthropic.RateLimitError:
            print(f"[{overall:3d}/{total}] Rate limited — waiting 60 s ...")
            time.sleep(60)
            # Retry once
            try:
                sentence = generate_sentence(client, latin, german)
                sentences[latin] = sentence
                save(OUTPUT_PATH, sentences)
                print(f"           Retry OK")
            except Exception as e2:
                print(f"           Retry failed: {e2}")
                errors += 1

        except Exception as e:
            print(f"[{overall:3d}/{total}] ERROR: {e}")
            errors += 1
            # Keep going; the entry will be retried on the next run

        # Small delay to stay comfortably within rate limits
        time.sleep(0.3)

    print()
    print(f"Done. {len(sentences)} sentences in {OUTPUT_PATH}  ({errors} errors)")


if __name__ == "__main__":
    main()
