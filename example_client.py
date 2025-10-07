"""
Example client script demonstrating optimized file transfer with compression and parallel chunking.
This script shows how to use the new API endpoints for efficient file uploads and downloads.
"""

import requests
import os
import gzip
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from typing import Optional


class OptimizedFileTransferClient:
    """Client for optimized file transfers with compression and parallel chunking"""
    
    def __init__(self, base_url: str, max_workers: int = 5):
        """
        Initialize the client.
        
        Args:
            base_url: Base URL of the server (e.g., http://localhost:3000)
            max_workers: Maximum number of parallel workers for chunk transfers
        """
        self.base_url = base_url.rstrip('/')
        self.max_workers = max_workers
    
    def download_file(self, remote_path: str, local_path: str, 
                     use_chunking: bool = True, compress: bool = True) -> dict:
        """
        Download a file with optional compression and parallel chunking.
        
        Args:
            remote_path: Path to the file on the server
            local_path: Local path to save the file
            use_chunking: Whether to use parallel chunking
            compress: Whether to use compression
        
        Returns:
            Dictionary with download statistics
        """
        start_time = time.time()
        
        if not use_chunking:
            # Simple download
            return self._download_simple(remote_path, local_path, compress)
        
        # Get file information
        info_response = requests.get(
            f'{self.base_url}/file/info',
            params={'path': remote_path}
        )
        info_response.raise_for_status()
        file_info = info_response.json()
        
        total_chunks = file_info['total_chunks']
        should_compress = file_info['should_compress'] and compress
        
        print(f"Downloading: {file_info['filename']}")
        print(f"Size: {file_info['file_size']:,} bytes")
        print(f"Chunks: {total_chunks}")
        print(f"Compression: {'Enabled' if should_compress else 'Disabled'}")
        
        chunks = {}
        
        def download_chunk(chunk_id):
            response = requests.get(
                f'{self.base_url}/download/chunk',
                params={
                    'path': remote_path,
                    'chunk_id': chunk_id,
                    'compress': 'true' if should_compress else 'false'
                }
            )
            response.raise_for_status()
            
            chunk_data = response.content
            chunk_hash = response.headers.get('X-Chunk-Hash')
            compressed = response.headers.get('X-Compressed') == 'True'
            
            # Verify chunk integrity
            actual_hash = hashlib.sha256(chunk_data).hexdigest()
            if chunk_hash and actual_hash != chunk_hash:
                raise ValueError(f"Chunk {chunk_id} integrity check failed")
            
            return chunk_id, chunk_data, compressed
        
        # Download chunks in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(download_chunk, i) for i in range(total_chunks)]
            
            completed = 0
            for future in as_completed(futures):
                chunk_id, chunk_data, compressed = future.result()
                chunks[chunk_id] = (chunk_data, compressed)
                completed += 1
                
                # Progress indicator
                progress = (completed / total_chunks) * 100
                print(f"Progress: {progress:.1f}% ({completed}/{total_chunks} chunks)", end='\r')
        
        print()  # New line after progress
        
        # Reassemble file
        with open(local_path, 'wb') as f:
            for i in range(total_chunks):
                chunk_data, compressed = chunks[i]
                if compressed:
                    chunk_data = gzip.decompress(chunk_data)
                f.write(chunk_data)
        
        elapsed_time = time.time() - start_time
        file_size = os.path.getsize(local_path)
        
        stats = {
            'filename': file_info['filename'],
            'size': file_size,
            'chunks': total_chunks,
            'compressed': should_compress,
            'time': elapsed_time,
            'speed': file_size / elapsed_time / (1024 * 1024)  # MB/s
        }
        
        print(f"Download completed in {elapsed_time:.2f}s ({stats['speed']:.2f} MB/s)")
        
        return stats
    
    def _download_simple(self, remote_path: str, local_path: str, compress: bool) -> dict:
        """Simple single-request download"""
        start_time = time.time()
        
        response = requests.get(
            f'{self.base_url}/download',
            params={
                'path': remote_path,
                'compress': 'true' if compress else 'false'
            },
            stream=True
        )
        response.raise_for_status()
        
        # Check if response is compressed
        is_compressed = response.headers.get('Content-Type') == 'application/gzip'
        
        with open(local_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        # Decompress if needed
        if is_compressed:
            temp_path = local_path + '.tmp'
            with gzip.open(local_path, 'rb') as f_in:
                with open(temp_path, 'wb') as f_out:
                    f_out.write(f_in.read())
            os.replace(temp_path, local_path)
        
        elapsed_time = time.time() - start_time
        file_size = os.path.getsize(local_path)
        
        return {
            'size': file_size,
            'compressed': is_compressed,
            'time': elapsed_time,
            'speed': file_size / elapsed_time / (1024 * 1024)
        }
    
    def upload_file(self, local_path: str, destination_path: str,
                   chunk_size: int = 1024 * 1024, compress: bool = True) -> dict:
        """
        Upload a file with compression and parallel chunking.
        
        Args:
            local_path: Path to the local file
            destination_path: Destination directory on the server
            chunk_size: Size of each chunk in bytes
            compress: Whether to compress chunks
        
        Returns:
            Dictionary with upload statistics
        """
        start_time = time.time()
        
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"File not found: {local_path}")
        
        filename = os.path.basename(local_path)
        file_size = os.path.getsize(local_path)
        total_chunks = (file_size + chunk_size - 1) // chunk_size
        
        print(f"Uploading: {filename}")
        print(f"Size: {file_size:,} bytes")
        print(f"Chunks: {total_chunks}")
        print(f"Compression: {'Enabled' if compress else 'Disabled'}")
        
        # Initialize upload session
        init_response = requests.post(
            f'{self.base_url}/upload/init',
            json={
                'filename': filename,
                'total_chunks': total_chunks,
                'path': destination_path,
                'compressed': compress
            }
        )
        init_response.raise_for_status()
        session_id = init_response.json()['session_id']
        
        print(f"Session initialized: {session_id}")
        
        def upload_chunk(chunk_id):
            offset = chunk_id * chunk_size
            
            with open(local_path, 'rb') as f:
                f.seek(offset)
                chunk_data = f.read(chunk_size)
            
            if compress:
                chunk_data = gzip.compress(chunk_data, compresslevel=6)
            
            chunk_hash = hashlib.sha256(chunk_data).hexdigest()
            
            files = {'chunk_data': chunk_data}
            data = {
                'session_id': session_id,
                'chunk_id': chunk_id,
                'chunk_hash': chunk_hash
            }
            
            response = requests.post(
                f'{self.base_url}/upload/chunk',
                files=files,
                data=data
            )
            response.raise_for_status()
            return chunk_id, response.json()
        
        # Upload chunks in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(upload_chunk, i) for i in range(total_chunks)]
            
            completed = 0
            for future in as_completed(futures):
                chunk_id, result = future.result()
                completed += 1
                
                # Progress indicator
                progress = (completed / total_chunks) * 100
                print(f"Progress: {progress:.1f}% ({completed}/{total_chunks} chunks)", end='\r')
        
        print()  # New line after progress
        
        # Finalize upload
        finalize_response = requests.post(
            f'{self.base_url}/upload/finalize',
            json={
                'session_id': session_id,
                'path': destination_path
            }
        )
        finalize_response.raise_for_status()
        result = finalize_response.json()
        
        elapsed_time = time.time() - start_time
        
        stats = {
            'filename': filename,
            'size': file_size,
            'chunks': total_chunks,
            'compressed': compress,
            'time': elapsed_time,
            'speed': file_size / elapsed_time / (1024 * 1024)  # MB/s
        }
        
        print(f"Upload completed in {elapsed_time:.2f}s ({stats['speed']:.2f} MB/s)")
        print(f"Server path: {result['path']}")
        
        return stats


def main():
    """Example usage"""
    # Initialize client
    client = OptimizedFileTransferClient(
        base_url='http://localhost:3000',
        max_workers=5
    )
    
    # Example: Upload a file
    try:
        print("=" * 60)
        print("UPLOAD EXAMPLE")
        print("=" * 60)
        upload_stats = client.upload_file(
            local_path='example_file.txt',  # Change this to your file
            destination_path='',  # Upload to base directory
            compress=True
        )
        print(f"\nUpload Statistics:")
        print(f"  - File: {upload_stats['filename']}")
        print(f"  - Size: {upload_stats['size']:,} bytes")
        print(f"  - Time: {upload_stats['time']:.2f} seconds")
        print(f"  - Speed: {upload_stats['speed']:.2f} MB/s")
    except Exception as e:
        print(f"Upload failed: {e}")
    
    # Example: Download a file
    try:
        print("\n" + "=" * 60)
        print("DOWNLOAD EXAMPLE")
        print("=" * 60)
        download_stats = client.download_file(
            remote_path='example_file.txt',  # Change this to your file
            local_path='downloaded_file.txt',
            use_chunking=True,
            compress=True
        )
        print(f"\nDownload Statistics:")
        print(f"  - File: {download_stats['filename']}")
        print(f"  - Size: {download_stats['size']:,} bytes")
        print(f"  - Time: {download_stats['time']:.2f} seconds")
        print(f"  - Speed: {download_stats['speed']:.2f} MB/s")
    except Exception as e:
        print(f"Download failed: {e}")


if __name__ == '__main__':
    main()
