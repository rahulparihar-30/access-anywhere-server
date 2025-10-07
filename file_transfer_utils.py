"""
Utility module for file compression and chunking operations.
Provides functions for optimizing file transfers through compression and parallel chunking.
"""

import gzip
import os
import json
import hashlib
from typing import Dict, List, Optional, BinaryIO
from dataclasses import dataclass, asdict
import threading
import time


# Configuration constants
DEFAULT_CHUNK_SIZE = 1024 * 1024  # 1MB chunks
COMPRESSION_LEVEL = 6  # Balance between speed and compression ratio (1-9)
MAX_CHUNKS_IN_MEMORY = 10  # Maximum number of chunks to keep in memory


@dataclass
class ChunkMetadata:
    """Metadata for a file chunk"""
    chunk_id: int
    chunk_hash: str
    chunk_size: int
    offset: int
    total_chunks: int
    original_filename: str


@dataclass
class UploadSession:
    """Represents an active upload session"""
    session_id: str
    filename: str
    total_chunks: int
    received_chunks: List[int]
    chunk_data: Dict[int, bytes]
    created_at: float
    last_updated: float
    compressed: bool
    
    def is_complete(self) -> bool:
        """Check if all chunks have been received"""
        return len(self.received_chunks) == self.total_chunks
    
    def get_missing_chunks(self) -> List[int]:
        """Get list of missing chunk IDs"""
        return [i for i in range(self.total_chunks) if i not in self.received_chunks]


class UploadSessionManager:
    """Manages active upload sessions with thread-safe operations"""
    
    def __init__(self, session_timeout: int = 3600):
        self.sessions: Dict[str, UploadSession] = {}
        self.lock = threading.Lock()
        self.session_timeout = session_timeout
        
    def create_session(self, session_id: str, filename: str, total_chunks: int, compressed: bool = True) -> UploadSession:
        """Create a new upload session"""
        with self.lock:
            session = UploadSession(
                session_id=session_id,
                filename=filename,
                total_chunks=total_chunks,
                received_chunks=[],
                chunk_data={},
                created_at=time.time(),
                last_updated=time.time(),
                compressed=compressed
            )
            self.sessions[session_id] = session
            return session
    
    def get_session(self, session_id: str) -> Optional[UploadSession]:
        """Get an existing upload session"""
        with self.lock:
            return self.sessions.get(session_id)
    
    def add_chunk(self, session_id: str, chunk_id: int, chunk_data: bytes) -> bool:
        """Add a chunk to an upload session"""
        with self.lock:
            session = self.sessions.get(session_id)
            if not session:
                return False
            
            if chunk_id not in session.received_chunks:
                session.received_chunks.append(chunk_id)
                session.chunk_data[chunk_id] = chunk_data
                session.last_updated = time.time()
            
            return True
    
    def remove_session(self, session_id: str):
        """Remove a completed or expired session"""
        with self.lock:
            if session_id in self.sessions:
                del self.sessions[session_id]
    
    def cleanup_expired_sessions(self):
        """Remove sessions that have expired"""
        current_time = time.time()
        with self.lock:
            expired_sessions = [
                session_id for session_id, session in self.sessions.items()
                if current_time - session.last_updated > self.session_timeout
            ]
            for session_id in expired_sessions:
                del self.sessions[session_id]


# Global upload session manager
upload_manager = UploadSessionManager()


def compress_file(input_path: str, output_path: str, compression_level: int = COMPRESSION_LEVEL) -> int:
    """
    Compress a file using gzip compression.
    
    Args:
        input_path: Path to the input file
        output_path: Path to save the compressed file
        compression_level: Compression level (1-9, where 9 is maximum compression)
    
    Returns:
        Size of the compressed file in bytes
    """
    with open(input_path, 'rb') as f_in:
        with gzip.open(output_path, 'wb', compresslevel=compression_level) as f_out:
            # Read and compress in chunks to handle large files
            while True:
                chunk = f_in.read(DEFAULT_CHUNK_SIZE)
                if not chunk:
                    break
                f_out.write(chunk)
    
    return os.path.getsize(output_path)


def decompress_file(input_path: str, output_path: str) -> int:
    """
    Decompress a gzip compressed file.
    
    Args:
        input_path: Path to the compressed file
        output_path: Path to save the decompressed file
    
    Returns:
        Size of the decompressed file in bytes
    """
    with gzip.open(input_path, 'rb') as f_in:
        with open(output_path, 'wb') as f_out:
            # Read and decompress in chunks to handle large files
            while True:
                chunk = f_in.read(DEFAULT_CHUNK_SIZE)
                if not chunk:
                    break
                f_out.write(chunk)
    
    return os.path.getsize(output_path)


def compress_data(data: bytes, compression_level: int = COMPRESSION_LEVEL) -> bytes:
    """
    Compress raw bytes data using gzip.
    
    Args:
        data: Raw bytes to compress
        compression_level: Compression level (1-9)
    
    Returns:
        Compressed data as bytes
    """
    return gzip.compress(data, compresslevel=compression_level)


def decompress_data(data: bytes) -> bytes:
    """
    Decompress gzip compressed bytes.
    
    Args:
        data: Compressed bytes
    
    Returns:
        Decompressed data as bytes
    """
    return gzip.decompress(data)


def calculate_chunk_hash(data: bytes) -> str:
    """
    Calculate SHA256 hash of chunk data for integrity verification.
    
    Args:
        data: Chunk data
    
    Returns:
        Hex string of the hash
    """
    return hashlib.sha256(data).hexdigest()


def split_file_into_chunks(file_path: str, chunk_size: int = DEFAULT_CHUNK_SIZE, compress: bool = True) -> List[ChunkMetadata]:
    """
    Split a file into chunks and optionally compress each chunk.
    
    Args:
        file_path: Path to the file to split
        chunk_size: Size of each chunk in bytes
        compress: Whether to compress each chunk
    
    Returns:
        List of ChunkMetadata objects describing each chunk
    """
    file_size = os.path.getsize(file_path)
    total_chunks = (file_size + chunk_size - 1) // chunk_size  # Ceiling division
    chunks_metadata = []
    
    with open(file_path, 'rb') as f:
        for chunk_id in range(total_chunks):
            offset = chunk_id * chunk_size
            f.seek(offset)
            chunk_data = f.read(chunk_size)
            
            if compress:
                chunk_data = compress_data(chunk_data)
            
            chunk_hash = calculate_chunk_hash(chunk_data)
            
            metadata = ChunkMetadata(
                chunk_id=chunk_id,
                chunk_hash=chunk_hash,
                chunk_size=len(chunk_data),
                offset=offset,
                total_chunks=total_chunks,
                original_filename=os.path.basename(file_path)
            )
            chunks_metadata.append(metadata)
    
    return chunks_metadata


def read_file_chunk(file_path: str, chunk_id: int, chunk_size: int = DEFAULT_CHUNK_SIZE, compress: bool = True) -> tuple[bytes, ChunkMetadata]:
    """
    Read a specific chunk from a file.
    
    Args:
        file_path: Path to the file
        chunk_id: ID of the chunk to read (0-indexed)
        chunk_size: Size of each chunk in bytes
        compress: Whether to compress the chunk
    
    Returns:
        Tuple of (chunk_data, ChunkMetadata)
    """
    file_size = os.path.getsize(file_path)
    total_chunks = (file_size + chunk_size - 1) // chunk_size
    offset = chunk_id * chunk_size
    
    with open(file_path, 'rb') as f:
        f.seek(offset)
        chunk_data = f.read(chunk_size)
    
    if compress:
        chunk_data = compress_data(chunk_data)
    
    chunk_hash = calculate_chunk_hash(chunk_data)
    
    metadata = ChunkMetadata(
        chunk_id=chunk_id,
        chunk_hash=chunk_hash,
        chunk_size=len(chunk_data),
        offset=offset,
        total_chunks=total_chunks,
        original_filename=os.path.basename(file_path)
    )
    
    return chunk_data, metadata


def reassemble_chunks(chunks: Dict[int, bytes], output_path: str, decompress: bool = True) -> int:
    """
    Reassemble file chunks into a complete file.
    
    Args:
        chunks: Dictionary mapping chunk_id to chunk_data
        output_path: Path to save the reassembled file
        decompress: Whether to decompress each chunk before writing
    
    Returns:
        Size of the reassembled file in bytes
    """
    # Sort chunks by ID to ensure correct order
    sorted_chunk_ids = sorted(chunks.keys())
    
    with open(output_path, 'wb') as f:
        for chunk_id in sorted_chunk_ids:
            chunk_data = chunks[chunk_id]
            
            if decompress:
                chunk_data = decompress_data(chunk_data)
            
            f.write(chunk_data)
    
    return os.path.getsize(output_path)


def verify_chunk_integrity(chunk_data: bytes, expected_hash: str) -> bool:
    """
    Verify the integrity of a chunk using its hash.
    
    Args:
        chunk_data: The chunk data to verify
        expected_hash: The expected SHA256 hash
    
    Returns:
        True if the hash matches, False otherwise
    """
    actual_hash = calculate_chunk_hash(chunk_data)
    return actual_hash == expected_hash


def get_file_info(file_path: str, chunk_size: int = DEFAULT_CHUNK_SIZE) -> Dict:
    """
    Get information about a file for chunked transfer.
    
    Args:
        file_path: Path to the file
        chunk_size: Size of each chunk in bytes
    
    Returns:
        Dictionary with file information
    """
    file_size = os.path.getsize(file_path)
    total_chunks = (file_size + chunk_size - 1) // chunk_size
    
    return {
        'filename': os.path.basename(file_path),
        'file_size': file_size,
        'chunk_size': chunk_size,
        'total_chunks': total_chunks,
        'last_modified': os.path.getmtime(file_path)
    }


def estimate_compression_ratio(file_path: str, sample_size: int = 1024 * 1024) -> float:
    """
    Estimate compression ratio by compressing a sample of the file.
    
    Args:
        file_path: Path to the file
        sample_size: Size of sample to test (in bytes)
    
    Returns:
        Estimated compression ratio (compressed_size / original_size)
    """
    file_size = os.path.getsize(file_path)
    sample_size = min(sample_size, file_size)
    
    with open(file_path, 'rb') as f:
        sample = f.read(sample_size)
    
    compressed_sample = compress_data(sample)
    
    ratio = len(compressed_sample) / len(sample)
    return ratio


def should_compress_file(file_path: str, threshold: float = 0.9) -> bool:
    """
    Determine if a file should be compressed based on its estimated compression ratio.
    Files that don't compress well (like already compressed formats) should not be compressed.
    
    Args:
        file_path: Path to the file
        threshold: Compression ratio threshold (if ratio > threshold, don't compress)
    
    Returns:
        True if the file should be compressed, False otherwise
    """
    # Check file extension for known compressed formats
    compressed_extensions = {'.zip', '.gz', '.bz2', '.xz', '.7z', '.rar', 
                            '.jpg', '.jpeg', '.png', '.gif', '.mp4', '.mp3', 
                            '.avi', '.mkv', '.pdf', '.apk'}
    
    _, ext = os.path.splitext(file_path.lower())
    if ext in compressed_extensions:
        return False
    
    # Estimate compression ratio for other files
    ratio = estimate_compression_ratio(file_path)
    return ratio < threshold
