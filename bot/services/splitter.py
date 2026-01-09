from typing import List

class TextSplitter:
    def __init__(self, chunk_size: int = 1000, overlap: int = 200):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def split_text(self, text: str) -> List[str]:
        """
        Splits text into chunks of `chunk_size` characters with `overlap`.
        """
        if not text:
            return []
            
        chunks = []
        start = 0
        text_len = len(text)

        while start < text_len:
            end = start + self.chunk_size
            
            # If we are not at the end of the text, try to find the last space/newline within the chunk
            # to avoid cutting words in half.
            if end < text_len:
                # Look for the last space within the last 100 chars of the chunk window
                # This is a simple heuristic to preserve word boundaries
                search_window = text[end-100:end]
                last_space = -1
                
                # Check for newline first as it's a better split point
                if '\n' in search_window:
                    last_space = search_window.rfind('\n')
                elif ' ' in search_window:
                    last_space = search_window.rfind(' ')
                
                if last_space != -1:
                    # Adjust end to the found space position relative to the main text
                    end = (end - 100) + last_space + 1

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            # unexpected case: start didn't move
            if end == start:
                 break
                 
            start = start + self.chunk_size - self.overlap
            
            # Ensure we don't get stuck or go backwards if overlap is too big for a small remaining part
            # effectively: next start must be at least start + 1 (unless done)
            if start >= end:
                 start = end  # Should not happen with valid chunk_size > overlap, but safe guard

        return chunks
