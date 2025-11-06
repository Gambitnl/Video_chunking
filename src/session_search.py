"""
Provides functionality to search across all session transcripts.
"""

import os
from pathlib import Path

class SessionSearcher:
    """Searches for text within session transcripts."""

    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)

    def search(self, query: str) -> list[dict]:
        """
        Searches for a query string in all session transcripts.

        Args:
            query: The string to search for.

        Returns:
            A list of match results, where each result is a dictionary.
        """
        matches = []
        lower_query = query.lower()

        for txt_file in self.output_dir.rglob("*_full.txt"):
            session_id = txt_file.stem.replace("_full", "")
            try:
                with open(txt_file, 'r', encoding='utf-8') as f:
                    for i, line in enumerate(f):
                        if lower_query in line.lower():
                            matches.append({
                                "session_id": session_id,
                                "file_path": str(txt_file),
                                "line_number": i + 1,
                                "line_content": line.strip(),
                            })
            except Exception as e:
                print(f"Error reading file {txt_file}: {e}")
        
        return matches
