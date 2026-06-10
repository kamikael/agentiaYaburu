import logging
from typing import List, Dict, Any
from config import settings

logger = logging.getLogger(__name__)

class ChunkingService:
    def __init__(self):
        self.chunk_size = settings.RAG_CHUNK_SIZE
        self.chunk_overlap = settings.RAG_CHUNK_OVERLAP
        # Separators in order of priority (same as LangChain's RecursiveCharacterTextSplitter)
        self.separators = ["\n\n", "\n", " ", ""]

    def split_text(self, text: str) -> List[str]:
        """
        Split text into chunks using recursive character splitting.
        """
        return self._split_text_with_separators(text, self.separators)

    def _split_text_with_separators(self, text: str, separators: List[str]) -> List[str]:
        # Base cases
        if not text:
            return []
        if len(text) <= self.chunk_size:
            return [text]

        # Find the best separator
        separator = separators[-1]
        new_separators = []
        for i, _s in enumerate(separators):
            if _s == "":
                separator = _s
                break
            if _s in text:
                separator = _s
                new_separators = separators[i + 1:]
                break

        # Split by the chosen separator
        if separator:
            splits = text.split(separator)
        else:
            splits = list(text)

        # Merge splits
        good_splits = []
        final_chunks = []
        _separator = separator if separator is not None else ""
        
        for s in splits:
            if len(s) < self.chunk_size:
                good_splits.append(s)
            else:
                # If a split is too long, we need to split it recursively
                if good_splits:
                    merged_text = self._merge_splits(good_splits, _separator)
                    final_chunks.extend(merged_text)
                    good_splits = []
                if not new_separators:
                    good_splits.append(s)
                else:
                    other_info = self._split_text_with_separators(s, new_separators)
                    final_chunks.extend(other_info)

        if good_splits:
            merged_text = self._merge_splits(good_splits, _separator)
            final_chunks.extend(merged_text)
            
        return final_chunks
        
    def _merge_splits(self, splits: List[str], separator: str) -> List[str]:
        """
        Merge splits into chunks, respecting chunk_size and chunk_overlap.
        """
        chunks = []
        current_doc = []
        total = 0
        
        for d in splits:
            _len = len(d)
            if total + _len + (len(separator) if len(current_doc) > 0 else 0) > self.chunk_size:
                if total > 0:
                    chunk = separator.join(current_doc)
                    if chunk:
                        chunks.append(chunk)
                    
                    # Manage overlap
                    while total > self.chunk_overlap or (
                        total + _len + (len(separator) if len(current_doc) > 0 else 0) > self.chunk_size and total > 0
                    ):
                        if len(current_doc) > 1:
                            total -= len(current_doc[0]) + len(separator)
                            current_doc.pop(0)
                        else:
                            break
            
            current_doc.append(d)
            total += _len + (len(separator) if len(current_doc) > 1 else 0)
            
        if current_doc:
            chunk = separator.join(current_doc)
            if chunk:
                chunks.append(chunk)
                
        return chunks

chunking_service = ChunkingService()
