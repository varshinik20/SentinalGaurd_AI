"""
Document text cleaning service.

Responsible for normalizing extracted text before chunking.

Operations:
- Normalize line endings
- Remove excessive whitespace
- Remove blank lines
- Collapse multiple spaces
- Preserve paragraph structure
"""

import re


class TextCleaner:
    """Clean extracted document text."""

    def clean(self, text: str) -> str:
        """
        Clean extracted text.

        Args:
            text: Raw extracted text.

        Returns:
            Cleaned text.
        """

        if not text:
            return ""

        # Normalize line endings
        text = text.replace("\r\n", "\n")
        text = text.replace("\r", "\n")

        # Remove tabs
        text = text.replace("\t", " ")

        # Remove multiple spaces
        text = re.sub(r"[ ]{2,}", " ", text)

        # Remove blank lines
        lines = [
            line.strip()
            for line in text.split("\n")
            if line.strip()
        ]

        # Preserve paragraph structure
        cleaned = "\n".join(lines)

        return cleaned.strip()