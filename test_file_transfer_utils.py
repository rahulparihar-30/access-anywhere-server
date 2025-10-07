"""
Unit tests for file transfer optimization utilities.
Tests compression, chunking, session management, and integrity verification.
"""

import unittest
import tempfile
import os
import gzip
import hashlib
import time
from file_transfer_utils import (
    compress_file, decompress_file, compress_data, decompress_data,
    calculate_chunk_hash, split_file_into_chunks, read_file_chunk,
    reassemble_chunks, verify_chunk_integrity, get_file_info,
    estimate_compression_ratio, should_compress_file,
    UploadSession, UploadSessionManager,
    DEFAULT_CHUNK_SIZE
)


class TestCompressionFunctions(unittest.TestCase):
    """Test compression and decompression functions"""
    
    def setUp(self):
        """Create temporary test files"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.temp_dir, 'test.txt')
        self.test_data = b"This is test data " * 1000  # Compressible data
        
        with open(self.test_file, 'wb') as f:
            f.write(self.test_data)
    
    def tearDown(self):
        """Clean up temporary files"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_compress_decompress_file(self):
        """Test file compression and decompression"""
        compressed_file = os.path.join(self.temp_dir, 'test.txt.gz')
        decompressed_file = os.path.join(self.temp_dir, 'test_decompressed.txt')
        
        # Compress
        compressed_size = compress_file(self.test_file, compressed_file)
        self.assertTrue(os.path.exists(compressed_file))
        self.assertGreater(compressed_size, 0)
        self.assertLess(compressed_size, len(self.test_data))  # Should be smaller
        
        # Decompress
        decompressed_size = decompress_file(compressed_file, decompressed_file)
        self.assertEqual(decompressed_size, len(self.test_data))
        
        # Verify data integrity
        with open(decompressed_file, 'rb') as f:
            decompressed_data = f.read()
        self.assertEqual(decompressed_data, self.test_data)
    
    def test_compress_decompress_data(self):
        """Test data compression and decompression"""
        compressed = compress_data(self.test_data)
        self.assertLess(len(compressed), len(self.test_data))
        
        decompressed = decompress_data(compressed)
        self.assertEqual(decompressed, self.test_data)
    
    def test_compression_levels(self):
        """Test different compression levels"""
        sizes = []
        for level in [1, 5, 9]:
            compressed = compress_data(self.test_data, compression_level=level)
            sizes.append(len(compressed))
        
        # Higher compression level should result in smaller size
        self.assertGreaterEqual(sizes[0], sizes[1])
        self.assertGreaterEqual(sizes[1], sizes[2])


class TestChunkingFunctions(unittest.TestCase):
    """Test file chunking and reassembly"""
    
    def setUp(self):
        """Create temporary test file"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.temp_dir, 'test_large.dat')
        
        # Create a 5MB test file
        self.test_data = os.urandom(5 * 1024 * 1024)
        with open(self.test_file, 'wb') as f:
            f.write(self.test_data)
    
    def tearDown(self):
        """Clean up temporary files"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_split_file_into_chunks(self):
        """Test splitting a file into chunks"""
        chunk_size = 1024 * 1024  # 1MB
        chunks_metadata = split_file_into_chunks(
            self.test_file, 
            chunk_size=chunk_size, 
            compress=False
        )
        
        expected_chunks = (len(self.test_data) + chunk_size - 1) // chunk_size
        self.assertEqual(len(chunks_metadata), expected_chunks)
        
        # Verify metadata
        for i, metadata in enumerate(chunks_metadata):
            self.assertEqual(metadata.chunk_id, i)
            self.assertEqual(metadata.total_chunks, expected_chunks)
            self.assertGreater(len(metadata.chunk_hash), 0)
    
    def test_read_file_chunk(self):
        """Test reading specific chunks"""
        chunk_size = 1024 * 1024
        total_chunks = (len(self.test_data) + chunk_size - 1) // chunk_size
        
        for chunk_id in range(total_chunks):
            chunk_data, metadata = read_file_chunk(
                self.test_file,
                chunk_id,
                chunk_size=chunk_size,
                compress=False
            )
            
            self.assertEqual(metadata.chunk_id, chunk_id)
            self.assertEqual(metadata.total_chunks, total_chunks)
            
            # Verify chunk data
            offset = chunk_id * chunk_size
            expected_data = self.test_data[offset:offset + chunk_size]
            self.assertEqual(chunk_data, expected_data)
    
    def test_reassemble_chunks(self):
        """Test reassembling chunks into a file"""
        chunk_size = 1024 * 1024
        
        # Split file
        chunks_metadata = split_file_into_chunks(
            self.test_file,
            chunk_size=chunk_size,
            compress=False
        )
        
        # Read all chunks
        chunks = {}
        for metadata in chunks_metadata:
            chunk_data, _ = read_file_chunk(
                self.test_file,
                metadata.chunk_id,
                chunk_size=chunk_size,
                compress=False
            )
            chunks[metadata.chunk_id] = chunk_data
        
        # Reassemble
        output_file = os.path.join(self.temp_dir, 'reassembled.dat')
        final_size = reassemble_chunks(chunks, output_file, decompress=False)
        
        self.assertEqual(final_size, len(self.test_data))
        
        # Verify data integrity
        with open(output_file, 'rb') as f:
            reassembled_data = f.read()
        self.assertEqual(reassembled_data, self.test_data)
    
    def test_chunking_with_compression(self):
        """Test chunking with compression enabled"""
        chunk_size = 1024 * 1024
        
        # Create compressible data
        compressible_file = os.path.join(self.temp_dir, 'compressible.txt')
        compressible_data = b"Repeated text pattern. " * 100000
        with open(compressible_file, 'wb') as f:
            f.write(compressible_data)
        
        # Split with compression
        chunks_metadata = split_file_into_chunks(
            compressible_file,
            chunk_size=chunk_size,
            compress=True
        )
        
        # Read chunks
        chunks = {}
        for metadata in chunks_metadata:
            chunk_data, _ = read_file_chunk(
                compressible_file,
                metadata.chunk_id,
                chunk_size=chunk_size,
                compress=True
            )
            chunks[metadata.chunk_id] = chunk_data
        
        # Reassemble with decompression
        output_file = os.path.join(self.temp_dir, 'decompressed.txt')
        reassemble_chunks(chunks, output_file, decompress=True)
        
        # Verify
        with open(output_file, 'rb') as f:
            result_data = f.read()
        self.assertEqual(result_data, compressible_data)


class TestIntegrityFunctions(unittest.TestCase):
    """Test integrity verification functions"""
    
    def test_calculate_chunk_hash(self):
        """Test chunk hash calculation"""
        data = b"Test data for hashing"
        hash1 = calculate_chunk_hash(data)
        hash2 = calculate_chunk_hash(data)
        
        # Same data should produce same hash
        self.assertEqual(hash1, hash2)
        
        # Hash should be 64 characters (SHA256 hex)
        self.assertEqual(len(hash1), 64)
    
    def test_verify_chunk_integrity(self):
        """Test chunk integrity verification"""
        data = b"Test data for verification"
        correct_hash = calculate_chunk_hash(data)
        wrong_hash = "0" * 64
        
        # Correct hash should verify
        self.assertTrue(verify_chunk_integrity(data, correct_hash))
        
        # Wrong hash should not verify
        self.assertFalse(verify_chunk_integrity(data, wrong_hash))


class TestFileInfoFunctions(unittest.TestCase):
    """Test file information functions"""
    
    def setUp(self):
        """Create temporary test file"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.temp_dir, 'test.dat')
        self.test_data = os.urandom(10 * 1024 * 1024)  # 10MB
        
        with open(self.test_file, 'wb') as f:
            f.write(self.test_data)
    
    def tearDown(self):
        """Clean up"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_get_file_info(self):
        """Test getting file information"""
        chunk_size = 1024 * 1024
        info = get_file_info(self.test_file, chunk_size)
        
        self.assertEqual(info['filename'], 'test.dat')
        self.assertEqual(info['file_size'], len(self.test_data))
        self.assertEqual(info['chunk_size'], chunk_size)
        self.assertEqual(info['total_chunks'], 10)
        self.assertIn('last_modified', info)
    
    def test_estimate_compression_ratio(self):
        """Test compression ratio estimation"""
        # Create compressible file
        compressible_file = os.path.join(self.temp_dir, 'compressible.txt')
        compressible_data = b"Repeated pattern " * 100000
        with open(compressible_file, 'wb') as f:
            f.write(compressible_data)
        
        ratio = estimate_compression_ratio(compressible_file)
        
        # Should compress well (ratio < 0.5)
        self.assertLess(ratio, 0.5)
        self.assertGreater(ratio, 0)
    
    def test_should_compress_file(self):
        """Test file compression detection"""
        # Test already compressed file extensions
        compressed_files = [
            'test.zip', 'test.jpg', 'test.mp4', 'test.gz', 'test.png'
        ]
        
        for filename in compressed_files:
            filepath = os.path.join(self.temp_dir, filename)
            with open(filepath, 'wb') as f:
                f.write(b"dummy data")
            
            # Should not compress
            self.assertFalse(should_compress_file(filepath))
        
        # Test text file (should compress)
        text_file = os.path.join(self.temp_dir, 'test.txt')
        with open(text_file, 'wb') as f:
            f.write(b"Compressible text data " * 1000)
        
        self.assertTrue(should_compress_file(text_file))


class TestUploadSession(unittest.TestCase):
    """Test upload session functionality"""
    
    def test_upload_session_creation(self):
        """Test creating an upload session"""
        session = UploadSession(
            session_id='test-123',
            filename='test.txt',
            total_chunks=10,
            received_chunks=[],
            chunk_data={},
            created_at=time.time(),
            last_updated=time.time(),
            compressed=True
        )
        
        self.assertEqual(session.session_id, 'test-123')
        self.assertEqual(session.filename, 'test.txt')
        self.assertEqual(session.total_chunks, 10)
        self.assertFalse(session.is_complete())
    
    def test_session_completion(self):
        """Test session completion detection"""
        session = UploadSession(
            session_id='test-123',
            filename='test.txt',
            total_chunks=3,
            received_chunks=[0, 1, 2],
            chunk_data={},
            created_at=time.time(),
            last_updated=time.time(),
            compressed=True
        )
        
        self.assertTrue(session.is_complete())
    
    def test_missing_chunks(self):
        """Test missing chunk detection"""
        session = UploadSession(
            session_id='test-123',
            filename='test.txt',
            total_chunks=5,
            received_chunks=[0, 2, 4],
            chunk_data={},
            created_at=time.time(),
            last_updated=time.time(),
            compressed=True
        )
        
        missing = session.get_missing_chunks()
        self.assertEqual(set(missing), {1, 3})


class TestUploadSessionManager(unittest.TestCase):
    """Test upload session manager"""
    
    def setUp(self):
        """Create session manager"""
        self.manager = UploadSessionManager(session_timeout=1)  # 1 second timeout
    
    def test_create_session(self):
        """Test creating a session"""
        session = self.manager.create_session('test-123', 'test.txt', 5, True)
        
        self.assertEqual(session.session_id, 'test-123')
        self.assertEqual(session.filename, 'test.txt')
        self.assertEqual(session.total_chunks, 5)
    
    def test_get_session(self):
        """Test retrieving a session"""
        self.manager.create_session('test-123', 'test.txt', 5, True)
        
        session = self.manager.get_session('test-123')
        self.assertIsNotNone(session)
        self.assertEqual(session.session_id, 'test-123')
        
        # Non-existent session
        self.assertIsNone(self.manager.get_session('non-existent'))
    
    def test_add_chunk(self):
        """Test adding chunks to a session"""
        self.manager.create_session('test-123', 'test.txt', 3, True)
        
        # Add chunks
        self.assertTrue(self.manager.add_chunk('test-123', 0, b'chunk0'))
        self.assertTrue(self.manager.add_chunk('test-123', 1, b'chunk1'))
        
        session = self.manager.get_session('test-123')
        self.assertEqual(len(session.received_chunks), 2)
        self.assertEqual(session.chunk_data[0], b'chunk0')
        self.assertEqual(session.chunk_data[1], b'chunk1')
    
    def test_remove_session(self):
        """Test removing a session"""
        self.manager.create_session('test-123', 'test.txt', 5, True)
        self.assertIsNotNone(self.manager.get_session('test-123'))
        
        self.manager.remove_session('test-123')
        self.assertIsNone(self.manager.get_session('test-123'))
    
    def test_cleanup_expired_sessions(self):
        """Test automatic cleanup of expired sessions"""
        # Create session
        self.manager.create_session('test-123', 'test.txt', 5, True)
        
        # Wait for expiration (timeout is 1 second)
        time.sleep(1.5)
        
        # Cleanup
        self.manager.cleanup_expired_sessions()
        
        # Session should be removed
        self.assertIsNone(self.manager.get_session('test-123'))
    
    def test_thread_safety(self):
        """Test thread-safe operations"""
        import threading
        
        def add_chunks():
            for i in range(10):
                self.manager.add_chunk('test-123', i, f'chunk{i}'.encode())
        
        self.manager.create_session('test-123', 'test.txt', 20, True)
        
        # Start multiple threads
        threads = [threading.Thread(target=add_chunks) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Verify chunks were added correctly
        session = self.manager.get_session('test-123')
        self.assertGreaterEqual(len(session.received_chunks), 10)


def run_tests():
    """Run all tests"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestCompressionFunctions))
    suite.addTests(loader.loadTestsFromTestCase(TestChunkingFunctions))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegrityFunctions))
    suite.addTests(loader.loadTestsFromTestCase(TestFileInfoFunctions))
    suite.addTests(loader.loadTestsFromTestCase(TestUploadSession))
    suite.addTests(loader.loadTestsFromTestCase(TestUploadSessionManager))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return exit code
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    exit(run_tests())
