# Dungeon Crawler Carl Dictionary

An unofficial StarDict dictionary for looking up characters, places, items,
skills, and other terms from the *Dungeon Crawler Carl* series. It is intended
for use with KOReader.

## Install In KOReader

1. Download and extract the dictionary package, keeping its files together.
2. Copy the `Dungeon-Crawler-Carl-Dictionary` folder into
   `koreader/data/dict/` on your device. The folder should contain the matching
   `.ifo`, `.dict`, `.idx`, and `.css` files. Keep the `.syn`, `.qidx`, and
   `.sidx` files there too when included.
3. Restart KOReader.
4. Open **Dictionary settings → Manage dictionaries** and enable **Dungeon
   Crawler Carl Dictionary**.
5. To prioritize it for all books, move it above your other dictionaries in
   **Manage dictionaries**. To prioritize it for one book, open that book and
   choose **Dictionary settings → Set dictionary priority for this book**.

For more detailed installation steps, see [INSTALL-KOREADER.txt](INSTALL-KOREADER.txt).

## Look Up A Term

Open a book in KOReader and tap a word to open the dictionary lookup. If more
than one dictionary is enabled, KOReader shows results according to the
dictionary order you set. Select **Dungeon Crawler Carl Dictionary** to view
its entry.

## Spoilers And Sources

Entries include material from across the series, including later books, so
lookups may reveal spoilers. Some entries identify the book they refer to.
Content includes wiki-derived entries and contextual additions based on the
reference EPUBs. See [ATTRIBUTION.md](ATTRIBUTION.md) for source and licensing
information.

## Rebuild Book Additions

To regenerate the book-context entries from the EPUBs in `referance/`, run:

```sh
python3 build_book_glossary.py
```

This rewrites the StarDict package files in the project directory. The script
uses Python's standard library; keep the EPUB references in `referance/`.