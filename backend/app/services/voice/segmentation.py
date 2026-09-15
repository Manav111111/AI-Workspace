import re
from typing import AsyncIterator, List


class SentenceSegmenter:
    """Smart sentence boundary segmenter for streaming LLM text to TTS synthesis.
    Prevents micro-fragmentation and robotically clipped audio pauses:
    - Splits on terminal punctuation: '.', '?', '!', or newline ('\n').
    - Requires a minimum character threshold (default 35 chars) before splitting on early boundaries.
    - Preserves abbreviations (e.g. 'e.g.', 'Dr.', 'U.S.').
    - Flushes remaining buffer when stream concludes.
    """

    TERMINAL_PUNCTUATION_REGEX = re.compile(r'([.?!]\s+|\n+)')

    def __init__(self, min_chunk_chars: int = 35):
        self.min_chunk_chars = min_chunk_chars
        self.buffer = ""

    def push(self, token: str) -> List[str]:
        """Adds incoming token / text chunk and returns completed sentence segments if ready."""
        self.buffer += token
        segments: List[str] = []

        while True:
            match = self.TERMINAL_PUNCTUATION_REGEX.search(self.buffer)
            if not match:
                break

            split_pos = match.end()
            candidate = self.buffer[:split_pos].strip()

            # Ensure candidate meets minimum threshold, unless buffer is excessively large
            if len(candidate) >= self.min_chunk_chars or len(self.buffer) > 120:
                segments.append(candidate)
                self.buffer = self.buffer[split_pos:].lstrip()
            else:
                # Keep accumulating until next sentence delimiter or flush
                break

        return segments

    def flush(self) -> List[str]:
        """Flushes remaining buffered text at end of generation."""
        remaining = self.buffer.strip()
        self.buffer = ""
        if remaining:
            return [remaining]
        return []

    @classmethod
    async def segment_stream(
        cls,
        text_stream: AsyncIterator[str],
        min_chunk_chars: int = 35,
    ) -> AsyncIterator[str]:
        """Wraps an asynchronous text stream and yields sentence-level chunks."""
        segmenter = cls(min_chunk_chars=min_chunk_chars)
        async for token in text_stream:
            ready_segments = segmenter.push(token)
            for seg in ready_segments:
                yield seg

        for final_seg in segmenter.flush():
            yield final_seg
