# Prompts 79-91: stories

Read only the section of your prompt. `CLAUDE.md` gives the routine every prompt follows.

- Story data is text: your "picture" is a short sample printed in the report (30 lines at most).
- Public names (streets, notable families, guild heads, faction leaders, legends) never use
  real people: they skip the surnames in `[stories] avoid_names` (prompt 79 creates it: Ben Ali,
  Bourguiba, Bouden, Marzouki, Jebali, Karoui, Essebsi, Ghannouchi, Saied, Ben Youssef, Ben
  Salah, Ben Ammar, Ben Jaafar, Trabelsi, Hached, Chebbi, Mzali, Nouira, Mebazaa). Ordinary
  households may keep these common surnames. Brotherhoods and parties get invented names (never
  Qadiriyya, Tijaniyya, Shadhiliyya, Aissawiyya, Destour, Ennahdha, Nidaa Tounes, UGTT).
- Never draw Arabic with Pillow: it cannot shape Arabic here (no raqm), so letters would come
  out separate and left to right. Arabic lives in JSON, Markdown, SVG and the browser (Chromium
  shapes it; Geeza Pro and SF Arabic are installed). PNG maps stay Latin; show Ali Arabic
  samples as text or in a small HTML page.
- Fields shown on the viewer's house card must also pass through `slim_plan` in
  `tools/make_artifact.py`, or the phone page drops them.

## 79. D7 - Street names and house numbers

Model: Sonnet | Effort: medium | Size: M | Needs: 71 | Look: sample

**Do.**
1. Name parts come only from new `[streets.names]` lists in the style, each entry with its
   Arabic form: French generic names with accents and elision (de la République, de la Liberté,
   des Martyrs, de l'Indépendance: "de" becomes "d'" before a vowel), old-town trade plurals
   (Haddadine, Nahhasine, Sabbaghine, Najjarine, Sarrajine), invented people (`NameMaker`, own
   stream), places of the world. Never `[lore]` sentences or English trade words.
2. Latin forms as on Tunisian signs: Avenue, Rue, Place, Impasse (also in the medina, for
   example "Rue Tourbet el Bey"); Arabic forms شارع، نهج، ساحة، زنقة. Souks keep their
   "Souk el ..." names. Long streets keep one name across segments; own stream per street.
3. House numbers along each street, odd on one side and even on the other, starting at the end
   nearer the city center; every building with an entrance (prompt 71) gets an address.
4. plan.json and streets.json fields; a street index in the gazetteer; the viewer card shows the
   address ("12, Rue des Haddadine"), carried through `slim_plan`.

**Check.** Fingerprint may change: `plan/*`, `files/cities/*`, `gazetteer`. Tests: names unique
within a city (one name per long street), numbers increase along streets, no avoided surname.

**Done when.** A 20-line sample of streets and addresses reads like a real North African city.

## 80. D6 - Residents

Model: Sonnet | Effort: medium | Size: M | Needs: - | Look: sample

**Do.** Each household gets members: given names, ages, relations (parents, children, sometimes
a grandparent), occupations that fit the household's trade, wealth and ages (children at school,
a retired grandfather). Keep `[life] given_names` exactly as it is (family names draw from it
through the `family-names` stream: changing it reshuffles every family name); add new keys
(`female_names`, `male_names_extra`). Every resident choice comes from
`ctx.rng("residents", b)` (b = the household's building index), never from the name maker or
the households stream. The viewer card lists the family (through `slim_plan`); the gazetteer
shows a few.

**Check.** Fingerprint may change: `plan/*/households`, `gazetteer`. Tests: every existing
household field is identical to before; ages are consistent (parents 18+ years older than their
children); counts match `members`.

**Done when.** A 10-household sample reads like real families.

## 81. D1a - District histories

Model: Sonnet | Effort: medium | Size: S | Needs: 1 | Look: sample

**Do.** For each district, a 2-4 sentence history built from templates in the style and the
facts of the world (era founded, district kind, landmarks, trades, souks, the kasbah, the port),
own stream, overridable through `[canon]` (prompt 84 extends canon). In the gazetteer and
plan.json.

**Check.** Fingerprint may change: `plan/*/districts`, `gazetteer`.

**Done when.** The capital's district histories read well and never contradict the map.

## 82. D1b - Notable families, trades and guilds

Model: Sonnet | Effort: medium | Size: S | Needs: 80 | Look: sample

**Do.** Per city: 5-10 notable families (surnames of real households, never an avoided name;
their quarter, trade, wealth, the era they rose), the guild of each souk trade with its head (the
amin, a real resident), in the gazetteer and plan.json.

**Check.** Fingerprint may change: `plan/*`, `gazetteer`.

**Done when.** The notable families and guilds of the capital read like a city chronicle.

## 83. D1c - Local legends

Model: Sonnet | Effort: medium | Size: S | Needs: 81 | Look: sample

**Do.** Two or three legends per city from templates that point at real generated places (a
saint's tomb near a gate, an old well, a corsair captain's house, a lost caravan, the kasbah's
hidden room), own stream, in the gazetteer.

**Check.** Fingerprint may change: `gazetteer`.

**Done when.** The legends are evocative and every place they name exists. Tick D1.

## 84. D3 - Canon for everything

Model: Sonnet | Effort: medium | Size: S | Needs: 81 | Look: sample

**Do.** Extend `[canon]` in world files to pin district names, populations, landmark names,
street names, family names of chosen buildings and district histories; the gazetteer marks
pinned facts; `worlds/example.toml` shows each kind of pin. A pinned Latin name without an
Arabic pin gets no `name_ar` (prompt 87 adds `[canon.names_ar]`).

**Check.** Fingerprint: `--allow ""` on the default build (no pins). Test the pins with a
temporary world file.

**Done when.** Pinning a landmark name in a world file changes it in the gazetteer, the maps and
plan.json, and nothing else. Tick D3.

## 85. D4a - Timeline

Model: Sonnet | Effort: high | Size: M | Needs: 81 | Look: sample

**Do.** A generated history: per era of `[lore] eras`, events tied to real places (foundings,
sieges of walled cities, trade booms in ports, droughts, a protectorate treaty, independence)
with years, causes and consequences. world.json is written before any city is planned and must
not depend on which cities were planned: the timeline uses world-level facts only (settlements,
kinds, coast, roads, rivers, and style rules such as walls and ports by settlement kind), on
`stream(seed, "history")`. `world.json` `history`; a gazetteer chapter; district histories may
quote events.

**Check.** Fingerprint may change: `world`, `gazetteer`, `plan/*/districts`. Test: world.json is
identical for `--area none` and `--area capital`.

**Done when.** A 15-event timeline sample is coherent and dates are in order.

## 86. D4b - Factions

Model: Sonnet | Effort: medium | Size: M | Needs: 85 | Look: sample

**Do.** Factions (merchant leagues, Sufi brotherhoods, corsair clans, the protectorate
administration, modern parties) with invented names, seats in cities, goals and rivalries tied
to timeline events. Leaders get names from `stream(seed, "factions")` (world-level, so
world.json stays independent of planning); the gazetteer links a leader to a notable family only
for planned cities. world.json and the gazetteer.

**Check.** Fingerprint may change: `world`, `gazetteer`. Test: world.json identical for
`--area none` and `--area capital`.

**Done when.** The factions explain at least three timeline events. Tick D4.

## 87. D5a - Names in Arabic script: places

Model: Sonnet | Effort: high | Size: M | Needs: 1 | Look: sample for Ali

**Goal.** Every place name in Arabic script and in Latin letters, without changing a single
Latin name or a single random draw.

**Read.** `citygen/names.py` (`NameMaker`: `_pick`, `_syllable`, `_core`, `core`, `country`,
`settlement`, `district`), the `[names]` lists in `styles/maghreb.toml`, `city/life.py` (souk
names), `city/__init__.py` and `city/medina.py` (names built in code).

**Do.**
1. Aligned Arabic twins: add `onsets_ar`, `vowels_ar`, `codas_ar`, `endings_ar`,
   `berber_endings_ar`, `country_endings_ar`, prefix and descriptor twins, each the same length
   as its Latin list (tested). Add `_pick_i(seq) -> (index, value)` using the same single
   `rng.integers(len(seq))` call, and leave `_pick` unchanged (`life.family_name` uses it).
   Build each name as a list of (Latin part, Arabic part) pairs in Latin order (note that
   `_syllable` draws the coda before the onset and vowel but writes onset, vowel, coda), so
   retries, the fallback ending of `core()` and the last-letter cut of `country()` act on the
   same part in both scripts.
2. Spelling: the repeated "a" vowels map partly to "ا" and partly to nothing (short vowels are
   not written); "i" to "ي"; "ou" and "o" to "و"; "e" to nothing. Repeated onsets can map to the
   emphatic letters ("s" to "س" and "ص", "t" to "ت" and "ط", "k" to "ك" and "ق"). Latin "g" to
   "ق" as in official Tunisian names (قفصة، قابس), "ڨ" only behind a style option; "ch" "ش",
   "dj" "ج", "gh" "غ", "kh" "خ", "h" "ح"; the Berber prefix "ta" to "ت". Endings: "a" "ة", "ia"
   "ية", "ane" "ان", "ine" "ين", "ouna" "ونة", and so on. The article (el, es, ech...) is always
   "ال" joined to its word with no space (رأس المقران، السوق); "Bou" is joined too (بوسالم).
3. Every other kind of name: `[names.districts]` template twins (Quartier, Cite, Hay: حي;
   Ville: مدينة; Riadh: رياض; Jardins de: حدائق; Zone Industrielle: المنطقة الصناعية; Port de:
   ميناء; Parc: منتزه; Bab: باب; Jamaa: جامع; Cemetery of Sidi: مقبرة سيدي), `word_ar` for each
   `[[souk]]` (العطارين، الشواشية، النحاس، الزرابي، الخضرة، الفخارة، القماش) and the souk repeat
   suffixes, the English names built in code ("Medina of X", "Great Mosque of X", "Mosque of X")
   moved into style templates with Arabic twins (مدينة {n} العتيقة، الجامع الكبير ب{n}), the
   natural names of prompt 68, `[world] name_ar`, and `[canon.names_ar]`.
4. `name_ar` on the country, settlements, districts, landmarks, souks and natural features in
   world.json and plan.json; the gazetteer shows both scripts; the viewer card too (through
   `slim_plan`).
5. Tests: every `*_ar` list matches its Latin list in length; every Arabic name uses Arabic
   letters only; a build with every `*_ar` key removed and a normal build give identical
   world.json and plan.json once the `*_ar` fields are dropped. Report settlements whose Arabic
   spellings collide once short vowels are dropped.

**Check.** Fingerprint may change: `world`, `plan/*`, `gazetteer`, only by new `*_ar` fields.

**Done when.** Ali, a native Arabic speaker, approves a sample of 30 names in both scripts
(print them in your report as text).

## 88. D5b - Names in Arabic script: people and streets

Model: Sonnet | Effort: high | Size: M | Needs: 87, 79 | Look: sample for Ali

**Do.**
1. Made-up nisba names: each root sound maps to one Arabic letter by a fixed table (no new
   random draw), and each word pattern has an Arabic template, for example `1a23i` to
   "{1}{2}{3}ي", `ma12ou3i` to "م{1}{2}و{3}ي", `1e2a3i` to "{1}{2}ا{3}ي". Any variety comes from
   `rng.key` of the Latin name, never from a stream.
2. Nisba surnames usually carry the article in Tunisian civil records (Marzouki: المرزوقي,
   Labidi: العبيدي), trade names too (Haddad: الحداد): propose this rule to Ali in your report
   before relying on it. "Ben" is "بن"; "Bou" is joined (بوزيد). The real name lists get their
   standard spellings; given names keep the article Tunisians write (Larbi: العربي, Tahar:
   الطاهر).
3. Given names (prompt 80), street names (prompt 79) and addresses; house numbers use the digits
   0-9 (never ١٢٣). The viewer card shows both scripts with right-to-left text (through
   `slim_plan`).

**Check.** Fingerprint may change: `plan/*/households`, `plan/*/streets`, `files/cities/*`,
`gazetteer`, only by new Arabic fields. Tests as in prompt 87.

**Done when.** Ali approves 30 people and street names in both scripts. Tick D5.

## 89. D2a - Country poster map (SVG)

Model: Sonnet | Effort: high | Size: M | Needs: 87, 68 | Look: poster

**Do.**
1. `python -m citygen poster country` writes `maps/country-poster.svg` and a PDF: shaded relief
   (an embedded JPEG at 150 dpi, under 8 MB), coastline, rivers, lakes, chotts, roads,
   settlements by kind, regions, mountain, cape and bay labels in Latin and Arabic, a legend, a
   compass rose, a scale bar and a title cartouche; A2 print size; fonts with fallbacks (Arabic:
   "Geeza Pro", "SF Arabic", "Noto Naskh Arabic", serif).
2. Render and check it with a short Playwright script: start `citygen.view.start_server`,
   `page.goto` the SVG, `page.screenshot(full_page=True)` for your one picture; read every
   label's `getBBox()` with `page.evaluate` and fix overlaps; `page.pdf(width="420mm",
   height="594mm")` writes the print PDF with embedded fonts.

**Check.** Fingerprint may change: `maps/country-poster.svg`, `maps/country-poster.pdf` only.

**Done when.** It looks like a printed atlas page and no two labels overlap.

## 90. D2b - City poster map (SVG)

Model: Sonnet | Effort: high | Size: M | Needs: 89, 79 | Look: poster

**Do.** `python -m citygen poster city NAME`, rendered and checked like prompt 89: districts in
soft colors, buildings, streets with their names along the lines, landmarks with small icons,
the kasbah, the port, a legend, scale, compass and a bilingual title; SVG and PDF.

**Check.** Fingerprint may change: `maps/*-poster.svg`, `maps/*-poster.pdf` only.

**Done when.** The capital's poster reads like a tourist map you would buy. Tick D2.

## 91. CP8 - Checkpoint: stories

Model: Opus | Effort: medium | Size: review | Needs: 79-90 | Look: samples + posters

Follow the checkpoint routine of prompt 6 (`## 6.` in docs/prompts/01-foundations.md) for
prompts 79 to 90, comparing with `cp7` (pass `output/bodjantouna-42`). Extra checks:
- Consistency: the gazetteer, plan.json, the maps and the posters tell the same story.
- No real people's names in public names; no offensive or silly combinations in 200 random
  names and sentences (scan them).
- Ask Ali to read 20 Arabic names and one district history.
Save `fingerprint save cp8 output/bodjantouna-42`. Fix prompts go in `## 91.1. ...`.
