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
        sections = ["Припев", "Куплет", "Вступление", "Проигрыш", "Chorus", "Verse", "Intro", "Bridge", "Outro", "Instrumental"]

        # Check for "Пр.:" specifically or other prefixes
        # If text is long, do NOT classify as section, but as lyrics (it will be handled in merge)
        text_stripped = text.strip()
        is_long = len(text_stripped) > 20 # Arbitrary threshold, if longer than "1. Verse" or "Intro:", it's lyrics

        if (text_stripped.startswith("Пр.:") or text_stripped.startswith("Intro:") or text_stripped.startswith("Instrumental:")) and not is_long:
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

        while i < len(lines):
            current_line = lines[i]

            # Identify directives (pure section headers)
            if current_line['type'] == 'section':
                # Close previous chorus if open
                if in_chorus:
                    self.chordpro_lines.append("{eoc}")
                    in_chorus = False

                # Check if this section starts a chorus
                is_chorus_start = False
                lower_text = current_line['text'].lower()
                if "припев" in lower_text or "chorus" in lower_text or "пр.:" in lower_text:
                    is_chorus_start = True

                self.chordpro_lines.append(f"{{comment: {current_line['text']}}}")

                if is_chorus_start:
                    self.chordpro_lines.append("{soc}")
                    in_chorus = True

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

                    elif next_line['type'] == 'section':
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
                if re.match(r'^\d+\.', lyric_text) or lyric_text.startswith("Пр.:"):
                     if in_chorus:
                         self.chordpro_lines.append("{eoc}")
                         in_chorus = False

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
                         # Remove marker
                         current_line['text'] = re.sub(r'^\d+\.\s*', '', current_line['text'])

                self.chordpro_lines.append(current_line['text'])
                i += 1

        if in_chorus:
             self.chordpro_lines.append("{eoc}")

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

    def _format_chord_line(self, words):
        # Wraps chords in [] but leaves structure markers alone
        chord_pattern = r'^[A-H](?:b|#)?(?:2|5|m|maj|min|dim|aug|sus|add)?(?:[0-9]{1,2})?(?:/[A-H](?:b|#)?)?$'
        parts = []
        for w in words:
            text = w[4]
            # We want to wrap the chord part if attached to structure chars?
            # Or just wrap if it IS a chord.

            clean_text = text.strip(".,;:()[]|")
            if re.match(chord_pattern, clean_text) and clean_text:
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
        return " ".join(parts)

    def _embed_chords(self, chord_words, lyric_words):
        # We construct the string by iterating through lyrics and inserting chords at appropriate indices

        chord_pattern = r'^[A-H](?:b|#)?(?:2|5|m|maj|min|dim|aug|sus|add)?(?:[0-9]{1,2})?(?:/[A-H](?:b|#)?)?$'

        # Sort chords by X
        chord_words = sorted(chord_words, key=lambda w: w[0])
        lyric_words = sorted(lyric_words, key=lambda w: w[0])

        combined = []
        for w in lyric_words:
            combined.append({'type': 'word', 'obj': w, 'x': w[0]})

        # Insert chords into the list based on X position
        for c in chord_words:
            c_center = (c[0] + c[2]) / 2
            c_text = c[4]

            # Determine if we should wrap in []
            clean_text = c_text.strip(".,;:()[]|")
            is_chord = bool(re.match(chord_pattern, clean_text) and clean_text)

            if is_chord:
                if "|" in c_text:
                     wrapped_text = re.sub(f"({re.escape(clean_text)})", r"[\1]", c_text)
                else:
                     wrapped_text = f"[{c_text}]"
            else:
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
                         item['inserts'].append((char_idx, c_text if is_chord else c_text)) # Pass raw text, we wrap in loop
                         # Wait, if we pass raw text, we need to know if it should be wrapped.
                         # Actually, let's just pass the wrapped text.
                         # But wait, the logic below expects chord_text to be put inside [].
                         # Let's adjust logic below.
                         inserted = True
                         break

            if not inserted:
                combined.append({'type': 'chord', 'text': wrapped_text, 'x': c[0]})

        # Reconstruct string
        final_str = ""
        last_item_type = None

        for item in combined:
            if item['type'] == 'word':
                word_text = item['obj'][4]
                if 'inserts' in item:
                    item['inserts'].sort(key=lambda x: x[0], reverse=True)
                    for char_idx, chord_text in item['inserts']:
                        # Re-check pattern to wrap correctly or assume passed chord_text is raw
                        # But wait, we passed raw text above: item['inserts'].append((char_idx, c_text if is_chord else c_text))
                        # We need to wrap it here.

                        clean_text = chord_text.strip(".,;:()[]|")
                        if re.match(chord_pattern, clean_text) and clean_text:
                             if "|" in chord_text:
                                  insert_str = re.sub(f"({re.escape(clean_text)})", r"[\1]", chord_text)
                             else:
                                  insert_str = f"[{chord_text}]"
                        else:
                             insert_str = chord_text

                        word_text = word_text[:char_idx] + insert_str + word_text[char_idx:]

                if last_item_type == 'word':
                    final_str += " " # Add space between words
                final_str += word_text
                last_item_type = 'word'

            elif item['type'] == 'chord':
                if last_item_type == 'word':
                    final_str += " "
                final_str += item['text'] # Already wrapped if needed
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

