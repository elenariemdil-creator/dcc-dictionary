#!/usr/bin/env python3
"""Add a contextual glossary from the EPUB references to the StarDict files."""

from __future__ import annotations

import argparse
import html
import re
import struct
import zipfile
from collections import Counter, defaultdict
from datetime import date
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REFERENCES = ROOT / "referance"
PREFIX = "Dungeon-Crawler-Carl-Dictionary"
TARGET_BOOK_ENTRIES = 3100
TARGET_MULTIWORD_ENTRIES = 2273
PHRASE = re.compile(
    r"\b[A-Z][a-z]+(?:['’][A-Za-z]+)?"
    r"(?:\s+(?:(?:of|the|and|for|in|on|to|at|from|with|by|de|van|el|la)\s+)?"
    r"[A-Z][a-z]+(?:['’][A-Za-z]+)?)*\b"
)
SENTENCES = re.compile(r"(?<=[.!?])\s+|[\r\n]+")
WORDS = re.compile(r"[A-Za-z]+(?:['’][A-Za-z]+)?")
INITIAL_STOPWORDS = {
    "A", "An", "And", "As", "At", "Because", "Before", "But", "By",
    "For", "From", "He", "Her", "Here", "His", "How", "I", "If", "In",
    "It", "My", "No", "Not", "Of", "On", "Or", "Our", "She", "So",
    "That", "The", "Their", "They", "This", "Those", "Though", "Through",
    "To", "Upon", "We", "What", "When", "Where", "While", "Who", "With",
    "You",
}
CONNECTORS = {"and", "at", "by", "de", "el", "for", "from", "in", "la", "of", "on", "the", "to", "van", "with"}
PHRASE_EDGES = set("across along around back behind below beneath beside between beyond center end entire fellow former front inside into main middle near outside previous side through throughout top toward towards toward underneath within without".split())
PHRASE_VERBS = set("added appeared asked ask cast casts casting cried cry entered exiting filled find found going go got grabbed had heard hit hold holding looked looking made make moved need opened pulled put reached replied replied said say saw see shouted showed tell told turned wanted was were went whispered yelled rubbed".split())
PHRASE_HEADS = set("spell spells skill skills ability abilities item items weapon weapons armor armour ring rings sword swords gun guns rifle rifles knife knives shield shields potion potions loot box boxes scroll scrolls book books class classes race races trait traits buff buffs curse curses attack attacks effect effects artifact artifacts gear equipment mask masks boots gloves helmet helmets shard shards orb orbs crystal crystals gem gems card cards quest quests achievement achievements floor floors level levels dungeon dungeons city cities town towns kingdom kingdoms world worlds realm realms zone zones room rooms tower towers gate gates bridge bridges party parties team teams guild guilds clan clans faction factions militia army crew corporation system crawler crawlers monster monsters creature creatures god gods goddess goddesses deity deities boss bosses npc npcs character characters sponsor sponsors merchant merchants vendor vendors shop shops event events war wars game games show shows trial trials challenge challenges tournament festival tradition rule rules protocol device devices vehicle vehicles ship ships house houses building buildings door doors market markets club clubs bar bars species family families empire empires planet planets country countries grounds woods forest forests river rivers lake lakes mountain mountains cave caves restaurant palace apartment condo elf elves dwarf dwarves goblin goblins dragon dragons demon demons angel angels machine machines robot robots doll dolls pet pets cat cats dog dogs bear bears pig pigs horse horses boat boats car cars train trains elevator elevators token tokens key keys map maps badge badges crown crowns necklace necklaces pendant pendants bracelet bracelets tattoo tattoos elixir elixirs spellbook spellbooks power powers maneuver maneuvers strike strikes shot shots blast blasts bolt bolts missile missiles bomb bombs grenade grenades mana empress emperor queen king princess prince baroness lord lady captain colonel general judge sister mother".split())
SINGLE_STOPWORDS = set("""
about above after again against all am an and any are aren't as at be because
been before being below between both but by can can't cannot could couldn't did
didn't do does doesn't doing don't down during each either else enough even ever
every few for from further get gets getting got had hadn't has hasn't have haven't
having he he'd he'll he's her here here's hers herself him himself his how how's
i i'd i'll i'm i've if in into is isn't it it's its itself just let's like many
may maybe me might more most much must my myself neither never no nor not now of
off on once one only or other ought our ours ourselves out over own same she
she'd she'll she's should shouldn't so some such than that that's the their theirs
them themselves then there there's these they they'd they'll they're they've this
those through to too under until up upon us very was wasn't we we'd we'll we're
we've were weren't what what's when whenever where whereas wherever whether which
while who whoever whom whose why will with won't would wouldn't you you'd you'll
you're you've your yours yourself yourselves a an chapter chapters book books
first second third fourth fifth sixth seventh eighth ninth tenth one two three
four five six seven eight nine ten zero once twice oh okay yeah yup yes no hey
well wait sure right really maybe just now still even also both each every new
old next last another same different little big good bad great much many more most
several something someone somebody anything anyone everybody everything nothing
nobody anything
""".split())
BOOKS = {
    "Dungeon Crawler Carl - Matt Dinniman.epub": (1, "Dungeon Crawler Carl"),
    "Carls Doomsday Scenario.epub": (2, "Carl's Doomsday Scenario"),
    "Dungeon Anarchist's Cookbook, The.epub": (3, "The Dungeon Anarchist's Cookbook"),
    "Gate Of The Feral Gods, The.epub": (4, "The Gate of the Feral Gods"),
    "Butchers Masquerade, The.epub": (5, "The Butcher's Masquerade"),
    "Eye Of The Bedlam Bride, The.epub": (6, "The Eye of the Bedlam Bride"),
    "Parade of Horribles, A - Matt Dinniman.epub": (7, "A Parade of Horribles"),
    "This Inevitable Ruin.epub": (8, "This Inevitable Ruin"),
}


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.ignored = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "head"}:
            self.ignored += 1
        elif tag in {"p", "div", "br", "li", "h1", "h2", "h3"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "head"} and self.ignored:
            self.ignored -= 1
        elif tag in {"p", "div", "br", "li", "h1", "h2", "h3"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.ignored:
            self.parts.append(data)


def extract_text(data: bytes) -> str:
    parser = TextExtractor()
    parser.feed(data.decode("utf-8", "replace"))
    return re.sub(r"\s+", " ", " ".join(parser.parts)).strip()


def read_dictionary() -> tuple[list[tuple[str, bytes]], bytes, bytes]:
    idx_path = ROOT / f"{PREFIX}.idx"
    dict_path = ROOT / f"{PREFIX}.dict"
    syn_path = ROOT / f"{PREFIX}.syn"
    index = idx_path.read_bytes()
    data = dict_path.read_bytes()
    entries: list[tuple[str, bytes]] = []
    offset = 0
    while offset < len(index):
        end = index.index(b"\0", offset)
        word = index[offset:end].decode("utf-8")
        body_offset, body_size = struct.unpack(">II", index[end + 1:end + 9])
        entries.append((word, data[body_offset:body_offset + body_size]))
        offset = end + 9
    return entries, syn_path.read_bytes(), index


def read_synonyms(raw: bytes, old_entries: list[tuple[str, bytes]]) -> list[tuple[str, str]]:
    synonyms: list[tuple[str, str]] = []
    offset = 0
    while offset < len(raw):
        end = raw.index(b"\0", offset)
        alias = raw[offset:end].decode("utf-8")
        target = struct.unpack(">I", raw[end + 1:end + 5])[0]
        synonyms.append((alias, old_entries[target][0]))
        offset = end + 5
    return synonyms


def collect_candidates(existing: set[str]) -> tuple[Counter[str], dict[str, tuple[int, str]]]:
    counts: Counter[str] = Counter()
    contexts: dict[str, tuple[int, str]] = {}

    def record(term: str, book_number: int, sentence: str) -> None:
        counts[term] += 1
        previous = contexts.get(term)
        score = min(len(sentence), 240) + (40 if re.search(
            r"\b(?:is|are|was|were|called|known as|refers to|means)\b",
            sentence,
            re.IGNORECASE,
        ) else 0)
        if previous is None:
            contexts[term] = (book_number, sentence)
            return
        old_number, old_sentence = previous
        old_score = min(len(old_sentence), 240) + (40 if re.search(
            r"\b(?:is|are|was|were|called|known as|refers to|means)\b",
            old_sentence,
            re.IGNORECASE,
        ) else 0)
        if score > old_score:
            contexts[term] = (book_number, sentence)

    for path in sorted(REFERENCES.glob("*.epub")):
        book_number, book_title = BOOKS.get(path.name, (0, path.stem))
        with zipfile.ZipFile(path) as epub:
            for name in epub.namelist():
                if not name.lower().endswith((".xhtml", ".html", ".htm")):
                    continue
                text = extract_text(epub.read(name))
                for sentence in SENTENCES.split(text):
                    recorded_in_sentence: set[str] = set()
                    for match in PHRASE.finditer(sentence):
                        term = match.group().strip().rstrip("'’")
                        if match.start() == 0 and term.split()[0] in INITIAL_STOPWORDS:
                            term = " ".join(term.split()[1:])
                        term = re.sub(r"['’]s$", "", term).strip()
                        parts = term.split()
                        if not term:
                            continue
                        if len(parts) == 1:
                            if len(term) < 3 or term.casefold() in SINGLE_STOPWORDS:
                                continue
                        elif not 2 <= len(parts) <= 5:
                            continue
                        elif not any(part.casefold() not in CONNECTORS for part in parts):
                            continue
                        if term.casefold() in existing or len(sentence) < 20:
                            continue
                        if term.casefold() in recorded_in_sentence:
                            continue
                        recorded_in_sentence.add(term.casefold())
                        record(term, book_number, sentence)

                    matches = list(WORDS.finditer(sentence))
                    for size in range(2, 6):
                        for start in range(len(matches) - size + 1):
                            span = matches[start:start + size]
                            if any(sentence[left.end():right.start()].strip() for left, right in zip(span, span[1:])):
                                continue
                            parts = [match.group() for match in span]
                            term = " ".join(parts)
                            folded_parts = [part.casefold() for part in parts]
                            if term.casefold() in existing or len(sentence) < 20:
                                continue
                            if term.casefold() in recorded_in_sentence:
                                continue
                            if folded_parts[0] in SINGLE_STOPWORDS | CONNECTORS | PHRASE_EDGES:
                                continue
                            if folded_parts[-1] in SINGLE_STOPWORDS | CONNECTORS | PHRASE_EDGES:
                                continue
                            if any(part in PHRASE_VERBS for part in folded_parts):
                                continue
                            content = [part for part in folded_parts if part not in SINGLE_STOPWORDS | CONNECTORS]
                            if len(content) < 2 or any(len(part) < 3 for part in content):
                                continue
                            if folded_parts[-1] not in PHRASE_HEADS and not all(part[:1].isupper() for part in parts):
                                continue
                            if not any(part[:1].isupper() for part in parts):
                                term = term[0].upper() + term[1:]
                            recorded_in_sentence.add(term.casefold())
                            record(term, book_number, sentence)
    repeated = Counter({
        term: count
        for term, count in counts.items()
        if count >= (5 if " " not in term else 3)
    })
    return repeated, contexts


def make_definition(term: str, book_number: int, sentence: str) -> str:
    book_title = next((title for number, title in BOOKS.values() if number == book_number), "the series")
    clean_sentence = re.sub(r"\s+", " ", sentence).strip()
    clean_sentence = clean_sentence[:210].rsplit(" ", 1)[0].rstrip(" ,;:")
    quoted_context = html.escape(clean_sentence, quote=False)
    escaped_term = re.escape(term)
    description = re.search(
        rf"(?:^|\b){escaped_term}\b\s+(?:is|are|was|were|refers to|means|is called|was called|is known as|was known as)\s+([^.!?;]{{4,180}})",
        clean_sentence,
        re.IGNORECASE,
    )
    if description:
        core = description.group(1).strip(" \"'“”")
        if core:
            return f"In {book_title}, {html.escape(term)} is described as {html.escape(core, quote=False)}."
    return (
        f"A named term in {book_title}; the book associates it with this event or detail: "
        f"{quoted_context}."
    )


def make_entry(term: str, definition: str, book_number: int) -> bytes:
    html_term = html.escape(term, quote=False)
    body = (
        '<div class="entry">'
        f'<p class="headword"><b>{html_term}</b></p>'
        f'<p class="spoiler-note"><b>Book source:</b> Book {book_number}.</p>'
        f'<ul class="definition"><li>{definition}</li></ul>'
        "</div>"
    )
    return body.encode("utf-8")


def make_index(entries: list[tuple[str, bytes]]) -> tuple[bytes, bytes]:
    data = bytearray()
    index = bytearray()
    offsets: list[int] = []
    for word, body in entries:
        offsets.append(len(data))
        index.extend(word.encode("utf-8"))
        index.append(0)
        index.extend(struct.pack(">II", len(data), len(body)))
        data.extend(body)
    return bytes(index), bytes(data)


def make_sample_index(magic: bytes, source: bytes, count: int, offsets: list[int]) -> bytes:
    stride = 256
    samples = [offsets[position] for position in range(0, count, stride)]
    return magic + struct.pack("<IIIII", 2, stride, len(samples), len(source), count) + b"".join(
        struct.pack("<I", offset) for offset in samples
    )


def write_package(
    entries: list[tuple[str, bytes]],
    synonyms: list[tuple[str, str]],
) -> None:
    entries.sort(key=lambda item: (item[0].casefold(), item[0]))
    index, data = make_index(entries)
    word_positions = {word: position for position, (word, _) in enumerate(entries)}
    synonym_records = sorted(
        ((alias, word_positions[target]) for alias, target in synonyms if target in word_positions),
        key=lambda item: (item[0].casefold(), item[0]),
    )
    syn = bytearray()
    syn_offsets: list[int] = []
    for alias, target_position in synonym_records:
        syn_offsets.append(len(syn))
        syn.extend(alias.encode("utf-8"))
        syn.append(0)
        syn.extend(struct.pack(">I", target_position))

    (ROOT / f"{PREFIX}.idx").write_bytes(index)
    (ROOT / f"{PREFIX}.dict").write_bytes(data)
    (ROOT / f"{PREFIX}.syn").write_bytes(syn)
    (ROOT / f"{PREFIX}.qidx").write_bytes(make_sample_index(b"QIDX", index, len(entries), [
        offset for offset in _index_offsets(index)
    ]))
    (ROOT / f"{PREFIX}.sidx").write_bytes(make_sample_index(b"SIDX", bytes(syn), len(synonym_records), syn_offsets))

    ifo_path = ROOT / f"{PREFIX}.ifo"
    lines = ifo_path.read_text(encoding="utf-8").splitlines()
    values = {
        "wordcount": str(len(entries)),
        "synwordcount": str(len(synonym_records)),
        "idxfilesize": str(len(index)),
        "author": "Generated from Dungeon Crawler Carl Wiki contributors and authorized book references",
        "description": "Fan dictionary with wiki-derived entries and book-context additions; see ATTRIBUTION.md.",
        "date": date.today().strftime("%Y.%m.%d"),
    }
    updated = []
    seen = set()
    for line in lines:
        key, separator, _ = line.partition("=")
        if separator and key in values:
            updated.append(f"{key}={values[key]}")
            seen.add(key)
        else:
            updated.append(line)
    for key, value in values.items():
        if key not in seen:
            updated.append(f"{key}={value}")
    ifo_path.write_text("\n".join(updated) + "\n", encoding="utf-8")


def _index_offsets(index: bytes) -> list[int]:
    offsets: list[int] = []
    position = 0
    while position < len(index):
        offsets.append(position)
        end = index.index(b"\0", position)
        position = end + 9
    return offsets


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="report additions without changing dictionary files")
    args = parser.parse_args()

    all_entries, raw_synonyms, _ = read_dictionary()
    synonyms = read_synonyms(raw_synonyms, all_entries)
    generated_marker = b'<p class="spoiler-note"><b>Book source:</b> Book '
    old_entries = [(word, body) for word, body in all_entries if generated_marker not in body]
    generated_entries = [(word, body) for word, body in all_entries if generated_marker in body]
    existing = {word.casefold() for word, _ in old_entries + generated_entries}
    counts, contexts = collect_candidates(existing)
    needed = max(0, TARGET_BOOK_ENTRIES - len(generated_entries))
    generated_multiword = sum(" " in word for word, _ in generated_entries)
    needed_multiword = max(0, TARGET_MULTIWORD_ENTRIES - generated_multiword)
    selected = []
    seen = set(existing)
    ranked = lambda terms: sorted(terms, key=lambda item: (-counts[item], item.casefold(), item))
    multiword_candidates = ranked(term for term in counts if " " in term)
    for term in multiword_candidates:
        if len(selected) >= needed_multiword:
            break
        if term.casefold() in seen:
            continue
        selected.append(term)
        seen.add(term.casefold())
    if len(selected) < needed_multiword:
        raise SystemExit(f"Only {len(selected)} new multiword terms found; {needed_multiword} are required.")
    for term in ranked(term for term in counts if " " not in term):
        if len(selected) >= needed:
            break
        if term.casefold() in seen:
            continue
        selected.append(term)
        seen.add(term.casefold())
    if len(selected) < needed:
        raise SystemExit(f"Only {len(selected)} additional terms found; {needed} are required to reach {TARGET_BOOK_ENTRIES} book entries.")

    new_entries = []
    for term in selected:
        book_number, sentence = contexts[term]
        definition = make_definition(term, book_number, sentence)
        new_entries.append((term, make_entry(term, definition, book_number)))

    print(f"Existing entries: {len(old_entries)}")
    print(f"Existing book-context definitions: {len(generated_entries)}")
    print(f"Additional contextual definitions: {len(new_entries)}")
    print(f"Total book-context definitions: {len(generated_entries) + len(new_entries)}")
    print(f"Total multiword book entries: {generated_multiword + sum(' ' in term for term in selected)}")
    print(f"Total dictionary entries: {len(old_entries) + len(generated_entries) + len(new_entries)}")
    print("Sample additions:")
    for term, _ in new_entries[:12]:
        print(f"  {term} ({counts[term]} mentions)")
    if not args.dry_run:
        write_package(old_entries + generated_entries + new_entries, synonyms)
        print("Updated StarDict package files.")


if __name__ == "__main__":
    main()