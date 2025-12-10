from typing import List, Dict


class TextChunker:
    """Chunk text with overlap for better context preservation."""
    
    def __init__(self, chunk_size: int = 1000, overlap: int = 200):
        """
        Initialize chunker.
        
        Args:
            chunk_size: Maximum characters per chunk
            overlap: Number of characters to overlap between chunks
        """
        if overlap >= chunk_size:
            raise ValueError("Overlap must be less than chunk_size")
        
        self.chunk_size = chunk_size
        self.overlap = overlap
    
    def chunk_text(self, text: str, start_page: int = 1) -> List[Dict]:
        """
        Chunk text with overlap.
        
        Args:
            text: Full text to chunk
            start_page: Starting page number for metadata
        
        Returns:
            List of dicts with keys: chunk_index, text, char_count, start_page, end_page
        """
        if not text or not text.strip():
            return []
        
        chunks = []
        text_length = len(text)
        current_position = 0
        chunk_index = 0
        
        while current_position < text_length:
            # Calculate end position for this chunk
            end_position = min(current_position + self.chunk_size, text_length)
            
            # Extract chunk text
            chunk_text = text[current_position:end_position]
            
            # Try to break at sentence or word boundary if not at the end
            if end_position < text_length:
                # Look for sentence endings
                last_period = chunk_text.rfind(". ")
                last_newline = chunk_text.rfind("\n")
                last_break = max(last_period, last_newline)
                
                # If we found a good break point and it's not too far back
                if last_break > self.chunk_size * 0.7:
                    end_position = current_position + last_break + 1
                    chunk_text = text[current_position:end_position]
                else:
                    # Fall back to word boundary
                    last_space = chunk_text.rfind(" ")
                    if last_space > self.chunk_size * 0.5:
                        end_position = current_position + last_space
                        chunk_text = text[current_position:end_position]
            
            # Create chunk metadata
            chunk_data = {
                "chunk_index": chunk_index,
                "text": chunk_text.strip(),
                "char_count": len(chunk_text.strip()),
                "start_page": start_page,  # Simplified - would need page tracking for accurate values
                "end_page": start_page
            }
            
            chunks.append(chunk_data)
            chunk_index += 1
            
            # Move position forward, accounting for overlap
            if end_position >= text_length:
                break
            
            current_position = end_position - self.overlap
            
            # Ensure we make progress
            if current_position <= chunks[-1]["char_count"] - self.overlap:
                current_position = end_position
        
        return chunks
    
    def chunk_by_paragraphs(self, text: str, start_page: int = 1) -> List[Dict]:
        """
        Alternative chunking strategy: chunk by paragraphs with size limit.
        
        Args:
            text: Full text to chunk
            start_page: Starting page number for metadata
        
        Returns:
            List of chunk dictionaries
        """
        if not text or not text.strip():
            return []
        
        # Split into paragraphs
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        
        chunks = []
        current_chunk = []
        current_length = 0
        chunk_index = 0
        
        for paragraph in paragraphs:
            para_length = len(paragraph)
            
            # If single paragraph exceeds chunk_size, split it
            if para_length > self.chunk_size:
                # Save current chunk if exists
                if current_chunk:
                    chunk_text = "\n\n".join(current_chunk)
                    chunks.append({
                        "chunk_index": chunk_index,
                        "text": chunk_text,
                        "char_count": len(chunk_text),
                        "start_page": start_page,
                        "end_page": start_page
                    })
                    chunk_index += 1
                    current_chunk = []
                    current_length = 0
                
                # Chunk the long paragraph
                sub_chunker = TextChunker(self.chunk_size, self.overlap)
                sub_chunks = sub_chunker.chunk_text(paragraph, start_page)
                for sub_chunk in sub_chunks:
                    sub_chunk["chunk_index"] = chunk_index
                    chunks.append(sub_chunk)
                    chunk_index += 1
            
            # If adding paragraph would exceed size, save current chunk
            elif current_length + para_length > self.chunk_size and current_chunk:
                chunk_text = "\n\n".join(current_chunk)
                chunks.append({
                    "chunk_index": chunk_index,
                    "text": chunk_text,
                    "char_count": len(chunk_text),
                    "start_page": start_page,
                    "end_page": start_page
                })
                chunk_index += 1
                
                # Start new chunk with overlap (keep last paragraph if small enough)
                if current_chunk and len(current_chunk[-1]) < self.overlap:
                    current_chunk = [current_chunk[-1], paragraph]
                    current_length = len(current_chunk[-1]) + para_length
                else:
                    current_chunk = [paragraph]
                    current_length = para_length
            
            # Add paragraph to current chunk
            else:
                current_chunk.append(paragraph)
                current_length += para_length
        
        # Add final chunk if exists
        if current_chunk:
            chunk_text = "\n\n".join(current_chunk)
            chunks.append({
                "chunk_index": chunk_index,
                "text": chunk_text,
                "char_count": len(chunk_text),
                "start_page": start_page,
                "end_page": start_page
            })
        
        return chunks
