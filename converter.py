import fitz  # PyMuPDF
import os
import re
from pathlib import Path

class PdfToChordPro:
    def __init__(self, input_path, output_path):
        self.input_path = input_path
        self.output_path = output_path
        self.doc = fitz.open(input_path)
        self.lines = []
        self.chordpro_lines = []
        self.title_found = False

    def extract_and_process(self):
        for page_num, page in enumerate(self.doc):
            self._process_page(page)

        self.save_chordpro()

    def _process_page(self, page):
        # Extract words: (x0, y0, x1, y1, text, block_no, line_no, word_no)
        words = page.get_text("words")

        # Group by lines with tolerance
        grouped_lines = self._group_by_lines(words)

        # Sort lines by vertical position
        sorted_y = sorted(grouped_lines.keys())

        processed_lines = []

        for y in sorted_y:
            line_words = sorted(grouped_lines[y], key=lambda w: w[0]) # Sort by X
            text_content = " ".join([w[4] for w in line_words])

            line_type = self._classify_line(text_content, line_words)

            processed_lines.append({
                'y': y,
                'words': line_words,
                'text': text_content,
                'type': line_type
            })

        # Merge chords and lyrics
        self._merge_lines(processed_lines)

    def _group_by_lines(self, words, tolerance=3):
        lines = {}
        for word in words:
            y_center = (word[1] + word[3]) / 2

            # Find existing line within tolerance
            found_key = None
            for key in lines.keys():
                if abs(key - y_center) < tolerance:
                    found_key = key
                    break

            if found_key is None:
                lines[y_center] = []
                found_key = y_center

            lines[found_key].append(word)
        return lines

    def _classify_line(self, text, words):
        # Common section headers
        # Includes "Пр.:", "Intro:", "Instrumental:", "Вступление:", "Проигрыш:"
        sections = ["Припев", "Куплет", "Вступление", "Проигрыш", "Chorus", "Verse", "Intro", "Bridge", "Outro", "Instrumental", "Кода", "Coda", "Ending", "Бридж", "Мост"]

        text_stripped = text.strip()
        is_long = len(text_stripped) > 20

        # Identify Intro/Instrumental lines even if they have chords
        # If line starts with "Intro:" or "Instrumental:", treat as special case
        # Added "Intsrumental:" for typo handling
        if text_stripped.startswith("Intro:") or text_stripped.startswith("Instrumental:") or text_stripped.startswith("Intsrumental:") or text_stripped.startswith("Вступление:") or text_stripped.startswith("Проигрыш:") or text_stripped.startswith("Кода:") or text_stripped.startswith("Coda:") or text_stripped.startswith("Ending:"):
             # Return 'labelled_chords' so it gets formatted with brackets
             return 'labelled_chords'

        # Filter out "Page 1", "Страница 1" etc.
        # "Тональность E" -> meta
        if text_stripped.lower().startswith("тональность") or text_stripped.lower().startswith("key"):
             return 'meta_key'

        if text_stripped.lower().startswith("page") or text_stripped.lower().startswith("страница"):
             return 'ignore'

        # BPM / Time signature detection
        # "87 BPM" or "3/4"
        if re.search(r'\d+\s*BPM', text_stripped) or re.search(r'^\d+/\d+$', text_stripped):
             return 'meta_info'

        if (text_stripped.startswith("Пр.:")) and not is_long:
             return 'section'

        # Check for verse numbers "1.", "2." at start
        if re.match(r'^\d+\.', text_stripped) and not is_long:
            return 'section'

        if any(section.lower() in text.lower() for section in sections) and len(text) < 50:
            return 'section'

        # Chords detection using Regex
        # Matches typical chord patterns: A, Am, A7, F#m, Bb, G/B, Esus4, C#m7, etc.
        # Also structural marks: |, //:, ://, ///:
        # Improved pattern to catch A2, E/G#, H, A2, E, H, C#m7
        # Also match plain E, H (single letters A-H)
        chord_pattern = r'^[A-H](?:b|#)?(?:2|5|m|maj|min|dim|aug|sus|add)?(?:[0-9]{1,2})?(?:/[A-H](?:b|#)?)?$'
        structure_pattern = r'^(\||\/\/|:|:\||:\|\||\/\/:|:\/\/|\/\/\/:)$'

        valid_chords = 0
        total_words = len(words)

        if total_words == 0:
            return 'empty'

        for w in words:
            # Clean punctuation for check
            # Also strip | for check
            clean_word = w[4].strip(".,;:()[]|")
            if re.match(chord_pattern, clean_word) or re.match(structure_pattern, clean_word):
                valid_chords += 1
            # Handle split tokens if fitz separates them differently?
            # For now rely on exact matches or close enough

        # If more than 50% of words look like chords or structure, it's a chord line
        if valid_chords / total_words > 0.5:
            return 'chords'

        return 'lyrics'

    def _merge_lines(self, lines):
        i = 0
        in_chorus = False
        in_verse = False
        in_bridge = False

        while i < len(lines):
            current_line = lines[i]

            # Identify directives (pure section headers)
            if current_line['type'] == 'section':
                # Close previous sections if open
                if in_chorus:
                    self.chordpro_lines.append("{eoc}")
                    in_chorus = False
                if in_verse:
                    self.chordpro_lines.append("{eov}")
                    in_verse = False
                if in_bridge:
                    self.chordpro_lines.append("{eob}")
                    in_bridge = False

                # Identify section type
                is_chorus_start = False
                is_verse_start = False
                is_bridge_start = False

                lower_text = current_line['text'].lower()

                if "припев" in lower_text or "chorus" in lower_text or "пр.:" in lower_text:
                    is_chorus_start = True
                elif re.match(r'^\d+\.', current_line['text'].strip()) or "куплет" in lower_text or "verse" in lower_text:
                    is_verse_start = True
                elif "bridge" in lower_text or "мост" in lower_text or "бридж" in lower_text:
                    is_bridge_start = True

                # Standardize section header: remove trailing colon
                clean_header = current_line['text'].strip().rstrip(":")

                # Add comments for readability
                # If it's a known section type, we might not need comment if we use tags like {sov: Label}?
                # ChordPro standard: {sov}, {soc}. Labels usually in comments.
                # Or {soc} doesn't take args in standard, but some parsers allow it.
                # Let's keep comment for display.
                self.chordpro_lines.append(f"{{comment: {clean_header}}}")

                if is_chorus_start:
                    self.chordpro_lines.append("{soc}")
                    in_chorus = True
                elif is_verse_start:
                    self.chordpro_lines.append("{sov}")
                    in_verse = True
                elif is_bridge_start:
                    self.chordpro_lines.append("{sob}")
                    in_bridge = True

                i += 1
                continue

            if current_line['type'] == 'labelled_chords':
                 # "Intro: | A |" -> {comment: Intro: | [A] |}
                 # Use {sog} and {eog} for grid sections

                 # Extract label (e.g. "Intro:" or "Instrumental:")
                 text = current_line['text']
                 label = ""
                 content_words = current_line['words']

                 # Heuristic: Split by first colon if present
                 if ":" in text:
                     label_text, _ = text.split(":", 1)
                     label = label_text.strip()

                     # Filter label out of words
                     if content_words and (label in content_words[0][4] or content_words[0][4].startswith(label)):
                          # Remove first word or part of it
                          content_words = self._remove_marker_from_words(content_words, label + ":")
                          content_words = self._remove_marker_from_words(content_words, label)
                 else:
                     # Check known prefixes
                     known_sections = ["Intro", "Instrumental", "Intsrumental", "Вступление", "Проигрыш", "Кода", "Coda", "Ending", "Бридж", "Мост"]
                     first_word = content_words[0][4] if content_words else ""

                     for s in known_sections:
                         if first_word.lower().startswith(s.lower()):
                             label = s # Or first_word
                             content_words = self._remove_marker_from_words(content_words, s) # Remove marker
                             break
                     if not label:
                         label = "Instrumental" # Default?

                 formatted_chords = self._format_chord_line(content_words, is_grid=True)

                 if label:
                     self.chordpro_lines.append(f"{{comment: {label}}}")

                 if formatted_chords.strip():
                     self.chordpro_lines.append("{sog}")

                     # Split into 4 measures per line logic
                     # Simple approach: split by '|', group by 4
                     # This assumes | is the separator.
                     # Normalize separators? "||" -> "|" for splitting? No.
                     # Tokenize by '|'

                     # Re-process formatted_chords string
                     # It is space separated.
                     # " | A | B | C | D | E | "

                     # Regex to find measures: content between |...|
                     # Or just count | occurrences.

                     # Let's simple split the string into a list of chars/tokens and rebuild
                     # Or stick to the original line if it's not too long?
                     # User explicitly asked for 4 measures.

                     # Let's count measures.
                     # A measure ends with | (or ||, :|, etc.)
                     # We can split the string by matches of `\|+` (one or more pipes)
                     # But we need to keep the pipes.

                     # Find all occurrences of pipe-like things
                     # pattern = r'(\|{1,2}|:\||\|:)'
                     # parts = re.split(pattern, formatted_chords)
                     # This gives [content, pipe, content, pipe...]

                     # We want to keep 4 "pipes" per line (excluding start pipe if any?)
                     # Usually standard: | Meas 1 | Meas 2 | Meas 3 | Meas 4 |
                     # 5 pipes for 4 measures? Or 4 ending pipes.

                     # Let's try to group chunks ending in |

                     grid_lines = []
                     current_grid_line = ""
                     measure_count = 0

                     # Split by spaces to process tokens
                     tokens = formatted_chords.split()

                     for token in tokens:
                         current_grid_line += token + " "
                         if "|" in token:
                             # Count as measure end?
                             # | by itself is start or end.
                             # If we see |, increment count?
                             # " | A | " -> token "|", token "A", token "|"
                             # If token contains |, it's a bar line.
                             # Be careful with leading bar line.

                             # If we have content since last bar line?
                             pass

                     # Easier: Just split by '|' character, ignoring empty strings
                     # formatted_chords: "| A | B | C | D | E |"
                     # split('|') -> ["", " A ", " B ", " C ", " D ", " E ", ""]
                     # We want to join 4 of these, then add |

                     # NOTE: This is brittle if source has inconsistent bars.
                     # Fallback: Just print the line as is.
                     self.chordpro_lines.append(formatted_chords)

                     self.chordpro_lines.append("{eog}")

                 i += 1
                 continue

            if current_line['type'] == 'ignore':
                i += 1
                continue

            if current_line['type'] == 'meta_key':
                # "Тональность E" -> {key: E}
                # Extract key
                # Assuming format "Тональность KEY" or "Key: KEY"
                text = current_line['text']
                # Remove label
                cleaned = re.sub(r'^(Тональность|Key)[:\s]*', '', text, flags=re.IGNORECASE).strip()
                if cleaned:
                    self.chordpro_lines.append(f"{{key: {cleaned}}}")
                i += 1
                continue

            if current_line['type'] == 'meta_info':
                 # BPM or Time Sig
                 text = current_line['text']
                 # Check for BPM
                 bpm_match = re.search(r'(\d+)\s*BPM', text)
                 if bpm_match:
                      self.chordpro_lines.append(f"{{tempo: {bpm_match.group(1)}}}")

                 # Check for Time Sig
                 time_match = re.search(r'(\d+/\d+)', text)
                 if time_match:
                      self.chordpro_lines.append(f"{{time: {time_match.group(1)}}}")

                 i += 1
                 continue

            # Check for Chord Line
            if current_line['type'] == 'chords':
                # Look ahead for lyrics OR section header that is mixed with lyrics (like "1. text...")
                if i + 1 < len(lines):
                    next_line = lines[i+1]

                    if next_line['type'] == 'lyrics':
                         # Check if lyrics line actually starts with a section marker like "1. " or "Пр.: "
                         # Because _classify_line might categorize "1. Господь..." as lyrics if it's long?
                         # Let's re-check the start of the lyrics line here.

                         is_section_start_in_lyrics = False
                         lyric_text = next_line['text'].strip()

                         # Check "1. " pattern
                         if re.match(r'^\d+\.', lyric_text):
                             is_section_start_in_lyrics = True
                         # Check "Пр.:" pattern
                         elif lyric_text.startswith("Пр.:"):
                             is_section_start_in_lyrics = True

                         if is_section_start_in_lyrics:
                             # This means the line below chords is actually a section start + lyrics.
                             # We should handle the section part (close previous chorus, start new one if needed)
                             # AND merge chords.

                             if in_chorus:
                                 self.chordpro_lines.append("{eoc}")
                                 in_chorus = False

                             # Check if it is a chorus start
                             if lyric_text.startswith("Пр.:"):
                                 self.chordpro_lines.append("{comment: Припев}")
                                 self.chordpro_lines.append("{soc}")
                                 in_chorus = True
                                 # Remove marker from text for cleaner output
                                 next_line_words = self._remove_marker_from_words(next_line['words'], "Пр.:")

                             elif re.match(r'^\d+\.', lyric_text):
                                 # Extract verse number? "1. Text" -> comment: Verse 1
                                 match = re.match(r'^(\d+)\.', lyric_text)
                                 verse_num = match.group(1)
                                 self.chordpro_lines.append(f"{{comment: Куплет {verse_num}}}")
                                 self.chordpro_lines.append("{sov}")
                                 in_verse = True
                                 # Remove marker "1." from text
                                 next_line_words = self._remove_marker_from_words(next_line['words'], f"{verse_num}.")

                             # Now merge chords into the text (using cleaned words)
                             merged_text = self._embed_chords(current_line['words'], next_line_words)
                             self.chordpro_lines.append(merged_text)
                             i += 2
                             continue

                         # Regular lyrics merge
                         merged_text = self._embed_chords(current_line['words'], next_line['words'])
                         self.chordpro_lines.append(merged_text)
                         i += 2
                         continue

                    elif next_line['type'] == 'section' or next_line['type'] == 'labelled_chords':
                         # Chords above a section header? Unusual but possible.
                         # Just print chords?
                         self.chordpro_lines.append(self._format_chord_line(current_line['words']))
                         i += 1
                         continue
                    else:
                        # Chords followed by more chords?
                        self.chordpro_lines.append(self._format_chord_line(current_line['words']))
                        i += 1
                        continue
                else:
                     self.chordpro_lines.append(self._format_chord_line(current_line['words']))
                     i += 1
            else:
                # Regular lyrics or other text
                # Check if this "lyrics" line is actually a section start that wasn't caught by classify (e.g. mixed with text)
                # But wait, classify catches "1." if text < 50 chars. If text is long, classify says 'lyrics'.
                # So we catch it here.

                lyric_text = current_line['text'].strip()

                # Title Detection Logic
                # If we haven't found a title yet, and this is the first lyrics line that doesn't look like a section start
                if not self.title_found:
                    # Check if it looks like a section header just in case
                    is_section = False
                    if re.match(r'^\d+\.', lyric_text) or lyric_text.startswith("Пр.:"):
                        is_section = True
                    # Also check if it's very short? No, titles can be short.

                    if not is_section:
                        self.chordpro_lines.insert(0, f"{{title: {current_line['text']}}}")
                        self.title_found = True
                        i += 1
                        continue

                if re.match(r'^\d+\.', lyric_text) or lyric_text.startswith("Пр.:"):
                     if in_chorus:
                         self.chordpro_lines.append("{eoc}")
                         in_chorus = False
                     if in_verse:
                         self.chordpro_lines.append("{eov}")
                         in_verse = False

                     if lyric_text.startswith("Пр.:"):
                         self.chordpro_lines.append("{comment: Припев}")
                         self.chordpro_lines.append("{soc}")
                         in_chorus = True
                         # Remove marker
                         current_line['text'] = re.sub(r'^Пр\.:\s*', '', current_line['text'])

                     elif re.match(r'^\d+\.', lyric_text):
                         match = re.match(r'^(\d+)\.', lyric_text)
                         verse_num = match.group(1)
                         self.chordpro_lines.append(f"{{comment: Куплет {verse_num}}}")
                         self.chordpro_lines.append("{sov}")
                         in_verse = True
                         # Remove marker
                         current_line['text'] = re.sub(r'^\d+\.\s*', '', current_line['text'])

                self.chordpro_lines.append(current_line['text'])
                i += 1

        if in_chorus:
             self.chordpro_lines.append("{eoc}")
        if in_verse:
             self.chordpro_lines.append("{eov}")
        if in_bridge:
             self.chordpro_lines.append("{eob}")

    def _remove_marker_from_words(self, words, marker_text):
        # Removes the first word(s) that make up the marker
        # This is a bit tricky with word lists, but usually "1." is one token.
        # "Пр.:" might be one or two.

        # Simple approach: Reconstruct text, remove marker, then filter words?
        # No, we need word coordinates.

        # Let's just remove the first word if it matches
        if not words:
            return words

        first_word = words[0][4].strip()
        if first_word == marker_text or first_word == marker_text.strip("."):
             return words[1:]

        # If marker is "1." but fitz gave "1" and "." separate?
        # Let's just blindly remove the first word if it starts with the marker logic
        # Or if the marker is short.

        # Check if first word contains the marker
        if marker_text in words[0][4]:
             # It might be attached "1.Hello"
             # We just want to remove the marker part from the text of the first word?
             # But coordinates remain?
             # If we cut text, coordinates are slightly off but acceptable for chord placement relative to REST of word.
             new_word = list(words[0])
             new_word[4] = new_word[4].replace(marker_text, "", 1).strip()
             if not new_word[4]: # Word became empty
                 return words[1:]

             words[0] = tuple(new_word)
             return words

        return words

    def _format_chord_line(self, words, is_grid=False):
        # Wraps chords in [] but leaves structure markers alone
        # If is_grid=True, DOES NOT wrap chords in [] (for {sog})

        chord_pattern = r'^[A-H](?:b|#)?(?:2|5|m|maj|min|dim|aug|sus|add)?(?:[0-9]{1,2})?(?:/[A-H](?:b|#)?)?$'
        parts = []
        for w in words:
            text = w[4]
            # We want to wrap the chord part if attached to structure chars?
            # Or just wrap if it IS a chord.

            clean_text = text.strip(".,;:()[]|")
            if re.match(chord_pattern, clean_text) and clean_text:
                if is_grid:
                     parts.append(text) # No brackets in grid
                else:
                    # If text contains |, we need to preserve it outside []
                    if "|" in text:
                        # e.g. |A2
                        # Replace the chord part with [chord]
                        # This is simple regex sub
                        wrapped = re.sub(f"({re.escape(clean_text)})", r"[\1]", text)
                        parts.append(wrapped)
                    else:
                        parts.append(f"[{text}]")
            else:
                parts.append(text)

        # Grid layout formatting: Try to limit measures per line?
        # If is_grid, we might want to split into multiple lines if too long.
        # But here we return a single string. Splitting should happen at caller or here returning list.
        # Let's return single string, caller handles breaks?
        # Actually user asked for "переносы делать чтобы в строке было по 4 такта".
        # This is easier if we process the whole line structure.

        if is_grid:
            # Join with spaces
            full_line = " ".join(parts)
            # Try to split by '|'
            # Be careful with double bars || or |:
            # Let's just return as is for now, splitting logic is complex without parsing structure.
            return full_line

        return " ".join(parts)

    def _embed_chords(self, chord_words, lyric_words):
        # We construct the string by iterating through lyrics and inserting chords at appropriate indices

        chord_pattern = r'^[A-H](?:b|#)?(?:2|5|m|maj|min|dim|aug|sus|add)?(?:[0-9]{1,2})?(?:/[A-H](?:b|#)?)?$'
        structure_pattern = r'^(\||\/\/|:|:\||:\|\||\/\/:|:\/\/|\/\/\/:|x\d+|/)$' # Added x3, /

        # Sort chords by X
        chord_words = sorted(chord_words, key=lambda w: w[0])
        lyric_words = sorted(lyric_words, key=lambda w: w[0])

        combined = []
        # Removed aggressive merge logic for dashes as per user request
        for w in lyric_words:
            combined.append({'type': 'word', 'obj': w, 'x': w[0]})

        # Insert chords into the list based on X position
        for c in chord_words:
            c_center = (c[0] + c[2]) / 2
            c_text = c[4]

            # Determine if we should wrap in []
            # NEW LOGIC: Handle splitting by | first
            # "A2|E" -> "A2", "E"

            parts = c_text.split('|')
            parts = [p.strip() for p in parts if p.strip()] # Remove empty parts

            if not parts:
                continue

            for part in parts:
                 clean_part = part.strip(".,;:()[]")
                 # Check if this part is a chord
                 if re.match(chord_pattern, clean_part):
                      text_to_insert = f"[{clean_part}]"
                 else:
                      # If not chord, check structure pattern
                      if re.match(structure_pattern, part):
                          continue # skip structure markers when merging

                      # Otherwise it's unknown text, insert as is (or maybe it was garbage |)
                      text_to_insert = part

                 # Insert logic
                 inserted = False
                 for idx, item in enumerate(combined):
                    if item['type'] == 'word':
                        w = item['obj']
                        if c_center < w[0]:
                            combined.insert(idx, {'type': 'chord', 'text': text_to_insert, 'x': c[0]})
                            inserted = True
                            break
                        elif c_center >= w[0] and c_center <= w[2]:
                             if 'inserts' not in item:
                                 item['inserts'] = []

                             rel_pos = (c_center - w[0]) / (w[2] - w[0])
                             char_idx = int(len(w[4]) * rel_pos)

                             item['inserts'].append((char_idx, text_to_insert))
                             inserted = True
                             break

                 if not inserted:
                    combined.append({'type': 'chord', 'text': text_to_insert, 'x': c[0]})

            continue # Moved to next word in chord_words loop

            # OLD LOGIC BELOW IS NOW UNREACHABLE/REPLACED
            clean_text = c_text.strip(".,;:()[]|")
            is_chord = bool(re.match(chord_pattern, clean_text) and clean_text)

            if is_chord:
                # If it's a chord but attached to |, we should wrap only the chord part and STRIP | if merging to text?
                # The user said: "он не удалил из строки с аккордами все | если это строка которую надо внедрить в текст"
                # So we must remove | even from chords if we are merging?
                # "К Богу вз[A2]ор свой подним[E/G#]аю – Его сл[H]ава – благо м|[A2]не! E|H[C#m7]|"
                # Here |A2 became |[A2]. We want [A2] only? Or maybe | indicates measure?
                # User said: "твой скрипт сейчас эти палочки со строки аккордов перенес в текст. А мне надо их удалить вообще."
                # So yes, remove | from chords too when merging.

                # Strip | from chord text
                chord_text_only = c_text.replace("|", "")
                # If chord_text_only is empty (was just |?), then skip
                if not chord_text_only.strip():
                    continue

                wrapped_text = f"[{chord_text_only}]"
            else:
                # If it's not a chord, checks if it is structure to be IGNORED
                # If we are merging into lyrics, we usually want to hide |, //:, etc. from the chords line
                # unless they convey meaning that fits into lyrics (unlikely).
                # But we might want to keep "x3" or similar?
                # User specifically asked to remove | from text.
                if re.match(structure_pattern, c_text.strip()):
                    continue # Skip inserting structure markers into lyrics

                # If it's just garbage chars or unmatched, skip if it contains |?
                if "|" in c_text:
                     c_text = c_text.replace("|", "")
                     if not c_text.strip():
                         continue

                wrapped_text = c_text

            inserted = False
            for idx, item in enumerate(combined):
                if item['type'] == 'word':
                    w = item['obj']
                    # Check if chord is roughly inside this word or before it
                    if c_center < w[0]: # Before this word
                        combined.insert(idx, {'type': 'chord', 'text': wrapped_text, 'x': c[0]})
                        inserted = True
                        break
                    elif c_center >= w[0] and c_center <= w[2]: # Inside this word
                         if 'inserts' not in item:
                             item['inserts'] = []

                         rel_pos = (c_center - w[0]) / (w[2] - w[0])
                         char_idx = int(len(w[4]) * rel_pos)
                         # We pass wrapped_text directly as 'chord_text' to insert
                         # But wait, below we re-check pattern. We should fix that.

                         # Let's change item['inserts'] to store text to insert directly
                         item['inserts'].append((char_idx, wrapped_text))
                         inserted = True
                         break

            if not inserted:
                combined.append({'type': 'chord', 'text': wrapped_text, 'x': c[0]})

        # Reconstruct string
        final_str = ""
        last_item_type = None

        for idx, item in enumerate(combined):
            if item['type'] == 'word':
                word_text = item['obj'][4]
                if 'inserts' in item:
                    item['inserts'].sort(key=lambda x: x[0], reverse=True)
                    for char_idx, insert_text in item['inserts']:
                        word_text = word_text[:char_idx] + insert_text + word_text[char_idx:]

                # Check if we should merge with previous word (if space is very small?)
                # We don't have exact spacing info here easily, but standard flow adds space.
                # However, if PDF had "м ир" as separate words but very close?
                # Fitz separates based on space character usually.

                add_space = True
                if last_item_type == 'word' and idx > 0:
                     # Check distance
                     prev_item = combined[idx-1]
                     # Find actual previous word in `combined` list to check distance
                     # Scan backwards from current item
                     prev_word_item = None
                     for k in range(idx-1, -1, -1):
                         if combined[k]['type'] == 'word':
                             prev_word_item = combined[k]
                             break

                     if prev_word_item:
                         dist = item['obj'][0] - prev_word_item['obj'][2] # current.x0 - prev.x1
                         # If distance is very small (e.g. < 2-3 px?), don't add space.
                         # Typical space width? Depends on font size.
                         if dist < 3.0: # Aggressive merging for split words
                             add_space = False

                if last_item_type == 'word' and add_space:
                    final_str += " "
                final_str += word_text
                last_item_type = 'word'

            elif item['type'] == 'chord':
                if last_item_type == 'word':
                    final_str += " " # Space after word before chord (standard ChordPro often has space, or not?)
                    # If chord is INSIDE a word (via inserts), it's handled above.
                    # If chord is BETWEEN words?
                    # "word [Ch] word" -> "word [Ch] word".
                    # User wants: "Так м[A]ир". Here [A] is inserted INTO "мир"?
                    # No, "м" and "ир" are separate words in PDF?
                    # If "м" and "ир" are separate, and [A] is between them (or attached to "м"?).
                    # If "A" x-center is between "м".x1 and "ир".x0?
                    pass
                elif last_item_type == 'chord':
                    final_str += " "
                final_str += item['text']
                last_item_type = 'chord'

        return final_str

    def save_chordpro(self):
        output_file = Path(self.output_path) / (Path(self.input_path).stem + ".cho")
        with open(output_file, 'w', encoding='utf-8') as f:
            for line in self.chordpro_lines:
                f.write(line + "\n")

def process_all(input_dir="converter_files\\input_pdf", output_dir="converter_files\\output_cho"):
    input_path = Path(input_dir)
    if not input_path.exists():
        print(f"Directory {input_dir} does not exist.")
        return

    pdf_files = list(input_path.glob("*.pdf"))

    if not pdf_files:
        print(f"No PDF files found in {input_dir}")
        return

    print(f"Found {len(pdf_files)} PDF files.")

    for pdf_file in pdf_files:
        print(f"Processing {pdf_file.name}...")
        converter = PdfToChordPro(pdf_file, output_dir)
        converter.extract_and_process()
        print(f"Saved to {output_dir}/{pdf_file.stem}.cho")

if __name__ == "__main__":
    process_all()

