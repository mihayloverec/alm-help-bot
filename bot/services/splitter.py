import re
from typing import List

# Matches a line that starts a numbered clause, e.g. "6", "6.9", "6.9.4",
# optionally followed by "." or ")" and then the clause text.
# Examples that match: "6.9.4 Оскорбление...", "6.10. Текст", "7) Текст".
CLAUSE_RE = re.compile(r"^\s*(\d+(?:\.\d+)*)[.)]?\s+\S")

# Matches non-numeric section headings (appendices, chapters, etc.). These
# also start a new section so e.g. "Приложение 1. Технические Фолы" is split
# off from the preceding numbered clause instead of being glued to it.
HEADING_RE = re.compile(r"^\s*(приложение|глава|раздел|часть|статья)\b", re.IGNORECASE)


def _is_section_start(line: str) -> bool:
    return bool(CLAUSE_RE.match(line) or HEADING_RE.match(line))


class TextSplitter:
    """
    Structure-aware splitter for the regulation text.

    The regulation is organised as numbered clauses (6, 6.9, 6.9.4, ...).
    Instead of cutting blind fixed-size windows — which slice through the
    middle of clauses and produce "smeared" chunks that mix the tail of one
    rule with the head of the next — we split on clause boundaries and pack
    whole clauses together up to `chunk_size`. Each chunk then holds one or a
    few complete rules, so retrieval returns the actual point, not noise.

    `chunk_size` is the soft upper bound (characters) for a packed chunk.
    `overlap` prepends a tail of the previous chunk to preserve context across
    boundaries (e.g. a parent heading before its sub-clauses).
    """

    def __init__(self, chunk_size: int = 1200, overlap: int = 200):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def split_text(self, text: str) -> List[str]:
        if not text:
            return []

        clauses = self._split_into_clauses(text)

        # Fallback: no clause structure detected (e.g. a flat document) —
        # use the previous character-window behaviour so we never return empty.
        if len(clauses) <= 1:
            return self._split_by_chars(text)

        chunks: List[str] = []
        current = ""

        for clause in clauses:
            # A single clause/section larger than the budget is split on its
            # own, repeating its heading in every piece so the topic (e.g.
            # "Технические Фолы") stays attached to each list item.
            if len(clause) > self.chunk_size:
                if current.strip():
                    chunks.append(current.strip())
                    current = ""
                heading = self._section_heading(clause)
                chunks.extend(self._split_by_chars(clause, heading=heading))
                continue

            # Packing this clause would overflow → flush and start a new chunk
            # (carrying a small overlap tail for cross-boundary context).
            if current and len(current) + len(clause) > self.chunk_size:
                chunks.append(current.strip())
                current = self._overlap_tail(current) + clause
            else:
                current = f"{current}\n{clause}" if current else clause

        if current.strip():
            chunks.append(current.strip())

        return [c for c in chunks if c.strip()]

    def _split_into_clauses(self, text: str) -> List[str]:
        """Groups the text into sections, each starting at a clause or heading."""
        lines = text.splitlines()
        clauses: List[str] = []
        buf: List[str] = []

        for line in lines:
            if _is_section_start(line) and buf:
                clauses.append("\n".join(buf).strip())
                buf = [line]
            else:
                buf.append(line)

        if buf:
            tail = "\n".join(buf).strip()
            if tail:
                clauses.append(tail)

        return [c for c in clauses if c]

    def _section_heading(self, section: str) -> str:
        """First line(s) of a section, used as a topic label on every piece."""
        lines = [ln.strip() for ln in section.splitlines() if ln.strip()]
        if not lines:
            return ""
        heading = lines[0]
        # A bare label like "Приложение 1." carries little meaning on its own;
        # append the next line (usually the descriptive title) for context.
        if len(lines) > 1 and len(heading) < 40:
            heading = f"{heading} {lines[1]}"
        return heading[:160]

    def _overlap_tail(self, text: str) -> str:
        """Returns the last `overlap` chars of `text` (word-aligned) + newline."""
        if self.overlap <= 0 or len(text) <= self.overlap:
            return ""
        tail = text[-self.overlap:]
        # Start the tail at a word boundary to avoid a dangling half-word.
        space = tail.find(" ")
        if space != -1:
            tail = tail[space + 1:]
        return tail.strip() + "\n"

    def _split_by_chars(self, text: str, heading: str = "") -> List[str]:
        """
        Character-window split with word-boundary snapping.

        When `heading` is given it is prepended to every piece after the first
        (the first already begins with it), so each fragment of a long section
        keeps its topic label for retrieval.
        """
        if not text:
            return []

        chunks: List[str] = []
        start = 0
        text_len = len(text)

        while start < text_len:
            end = start + self.chunk_size

            if end < text_len:
                search_window = text[end - 100:end]
                last_space = -1
                if "\n" in search_window:
                    last_space = search_window.rfind("\n")
                elif " " in search_window:
                    last_space = search_window.rfind(" ")
                if last_space != -1:
                    end = (end - 100) + last_space + 1

            chunk = text[start:end].strip()
            if chunk:
                if heading and chunks and not chunk.startswith(heading):
                    chunk = f"{heading}\n{chunk}"
                chunks.append(chunk)

            if end >= text_len:
                break

            next_start = end - self.overlap
            if next_start <= start:
                next_start = end
            start = next_start

        return chunks
