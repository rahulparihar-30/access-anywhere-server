# API Documentation - File Transfer Optimization

## Overview

This document describes the optimized file transfer API endpoints that implement compression and parallel chunking for improved transfer speeds, especially over slower internet connections.

## Key Features

1. **File Compression**: Automatic gzip compression for files that benefit from it
2. **Parallel Chunking**: Split large files into chunks that can be transferred in parallel
3. **Integrity Verification**: SHA256 hash verification for each chunk
4. **Smart Compression**: Automatically detects if a file should be compressed based on its type
5. **Session Management**: Robust upload session handling with automatic cleanup

## Configuration

The following constants can be configured in `main.py`:

- `CHUNK_SIZE`: Size of each chunk (default: 1MB)
- `COMPRESSION_LEVEL`: Gzip compression level 1-9 (default: 6)
- `MAX_PARALLEL_CHUNKS`: Maximum parallel chunk transfers (default: 5)

## Download Endpoints

### 1. Get File Information

**Endpoint**: `GET /file/info`

Get metadata about a file including chunk information for optimized download.

**Query Parameters**:
- `path` (required): Relative path to the file

**Response**:
```json
{
  "filename": "example.pdf",
  "file_size": 10485760,
  "chunk_size": 1048576,
  "total_chunks": 10,
  "last_modified": 1696723200.0,
  "should_compress": true,
  "estimated_compression_ratio": 0.65,
  "recommended_chunk_size": 1048576,
  "max_parallel_chunks": 5
}
```

### 2. Download File (with optional compression)

**Endpoint**: `GET /download`

Download a file with optional compression.

**Query Parameters**:
- `path` (required): Relative path to the file
- `compress` (optional): Set to "true" to enable compression (default: false)

**Response**: File data (compressed if requested and beneficial)

**Example**:
```
GET /download?path=Documents/report.pdf&compress=true
```

### 3. Download File Chunk

**Endpoint**: `GET /download/chunk`

Download a specific chunk of a file for parallel downloading.

**Query Parameters**:
- `path` (required): Relative path to the file
- `chunk_id` (required): Zero-based chunk index
- `compress` (optional): Set to "true" to compress the chunk (default: true)

**Response Headers**:
- `X-Chunk-Id`: The chunk ID
- `X-Chunk-Hash`: SHA256 hash of the chunk
- `X-Chunk-Size`: Size of the chunk in bytes
- `X-Total-Chunks`: Total number of chunks
- `X-Compressed`: Whether the chunk is compressed

**Response**: Chunk data (compressed if requested)

**Example**:
```
GET /download/chunk?path=Documents/large_file.zip&chunk_id=0&compress=true
```

## Upload Endpoints

### 1. Initialize Upload Session

**Endpoint**: `POST /upload/init`

Initialize a new upload session for chunked upload.

**Request Body**:
```json
{
  "filename": "large_video.mp4",
  "total_chunks": 100,
  "path": "Videos",
  "compressed": true
}
```

**Response**:
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "initialized",
  "filename": "large_video.mp4",
  "total_chunks": 100,
  "max_parallel_chunks": 5
}
```

### 2. Upload Chunk

**Endpoint**: `POST /upload/chunk`

Upload a single chunk of a file.

**Form Data**:
- `session_id` (required): Session ID from init
- `chunk_id` (required): Zero-based chunk index
- `chunk_hash` (optional): SHA256 hash for verification
- `chunk_data` (required): File data for the chunk

**Response**:
```json
{
  "status": "chunk_received",
  "chunk_id": 5,
  "received_chunks": 6,
  "total_chunks": 100,
  "is_complete": false,
  "missing_chunks": [0, 1, 2, 3, 4, 6, 7, ...]
}
```

**Example (Python)**:
```python
import requests

files = {'chunk_data': open('chunk_5.dat', 'rb')}
data = {
    'session_id': session_id,
    'chunk_id': 5,
    'chunk_hash': '...'
}
response = requests.post(f'{base_url}/upload/chunk', files=files, data=data)
```

### 3. Get Upload Status

**Endpoint**: `GET /upload/status`

Check the status of an upload session.

**Query Parameters**:
- `session_id` (required): Session ID

**Response**:
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "large_video.mp4",
  "total_chunks": 100,
  "received_chunks": 75,
  "is_complete": false,
  "missing_chunks": [10, 23, 45, 67, 89, ...]
}
```

### 4. Finalize Upload

**Endpoint**: `POST /upload/finalize`

Finalize the upload by reassembling all chunks.

**Request Body**:
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "path": "Videos"
}
```

**Response**:
```json
{
  "status": "completed",
  "filename": "large_video.mp4",
  "file_size": 104857600,
  "path": "/path/to/Videos/large_video.mp4"
}
```

### 5. Cancel Upload

**Endpoint**: `POST /upload/cancel`

Cancel an upload session and clean up resources.

**Request Body**:
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response**:
```json
{
  "status": "cancelled"
}
```

## Client Implementation Guide

### Parallel Download Example (Python)

```python
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

def download_file_parallel(base_url, file_path, output_path, max_workers=5):
    # Get file information
    info_response = requests.get(f'{base_url}/file/info', params={'path': file_path})
    file_info = info_response.json()
    
    total_chunks = file_info['total_chunks']
    should_compress = file_info['should_compress']
    
    chunks = {}
    
    def download_chunk(chunk_id):
        response = requests.get(
            f'{base_url}/download/chunk',
            params={
                'path': file_path,
                'chunk_id': chunk_id,
                'compress': 'true' if should_compress else 'false'
            }
        )
        
        chunk_data = response.content
        chunk_hash = response.headers.get('X-Chunk-Hash')
        compressed = response.headers.get('X-Compressed') == 'True'
        
        return chunk_id, chunk_data, compressed
    
    # Download chunks in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(download_chunk, i) for i in range(total_chunks)]
        
        for future in as_completed(futures):
            chunk_id, chunk_data, compressed = future.result()
            chunks[chunk_id] = (chunk_data, compressed)
            print(f"Downloaded chunk {chunk_id + 1}/{total_chunks}")
    
    # Reassemble file
    with open(output_path, 'wb') as f:
        for i in range(total_chunks):
            chunk_data, compressed = chunks[i]
            if compressed:
                import gzip
                chunk_data = gzip.decompress(chunk_data)
            f.write(chunk_data)
    
    print(f"File downloaded successfully to {output_path}")

# Usage
download_file_parallel(
    base_url='http://localhost:3000',
    file_path='Documents/large_file.pdf',
    output_path='downloaded_file.pdf',
    max_workers=5
)
```

### Parallel Upload Example (Python)

```python
import requests
import os
import gzip
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed

def upload_file_parallel(base_url, file_path, destination_path, 
                        chunk_size=1024*1024, max_workers=5, compress=True):
    filename = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)
    total_chunks = (file_size + chunk_size - 1) // chunk_size
    
    # Initialize upload session
    init_response = requests.post(
        f'{base_url}/upload/init',
        json={
            'filename': filename,
            'total_chunks': total_chunks,
            'path': destination_path,
            'compressed': compress
        }
    )
    session_id = init_response.json()['session_id']
    print(f"Upload session initialized: {session_id}")
    
    def upload_chunk(chunk_id):
        offset = chunk_id * chunk_size
        
        with open(file_path, 'rb') as f:
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
        
        response = requests.post(f'{base_url}/upload/chunk', files=files, data=data)
        return chunk_id, response.json()
    
    # Upload chunks in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(upload_chunk, i) for i in range(total_chunks)]
        
        for future in as_completed(futures):
            chunk_id, result = future.result()
            print(f"Uploaded chunk {chunk_id + 1}/{total_chunks}")
    
    # Finalize upload
    finalize_response = requests.post(
        f'{base_url}/upload/finalize',
        json={
            'session_id': session_id,
            'path': destination_path
        }
    )
    
    print(f"Upload completed: {finalize_response.json()}")

# Usage
upload_file_parallel(
    base_url='http://localhost:3000',
    file_path='local_large_file.mp4',
    destination_path='Videos',
    chunk_size=1024*1024,
    max_workers=5,
    compress=True
)
```

## Performance Considerations

1. **Compression Overhead**: Compression adds CPU overhead but reduces network transfer time. For slow connections, this is usually beneficial.

2. **Chunk Size**: 
   - Smaller chunks (256KB-512KB): Better for unstable connections, easier to retry
   - Larger chunks (2MB-5MB): Better for stable connections, less overhead

3. **Parallel Connections**: 
   - More connections can saturate bandwidth faster
   - Too many connections may overwhelm the server or be throttled by network
   - Recommended: 3-8 parallel connections

4. **File Types**:
   - Text, code, logs: High compression ratio (50-80% reduction)
   - Images (PNG, BMP): Good compression ratio (30-50% reduction)
   - Already compressed (ZIP, MP4, JPEG): No compression benefit

## Error Handling

All endpoints return appropriate HTTP status codes:

- `200 OK`: Success
- `400 Bad Request`: Missing or invalid parameters
- `403 Forbidden`: Path traversal attempt or access denied
- `404 Not Found`: File or session not found
- `500 Internal Server Error`: Server error

Error responses include a JSON object with an `error` field:
```json
{
  "error": "Description of the error"
}
```

## Session Management

- Upload sessions automatically expire after 1 hour of inactivity
- Expired sessions are cleaned up every 5 minutes
- Always finalize or cancel sessions to free up resources immediately
- Session data is stored in memory, so sessions are lost if the server restarts

## Security Considerations

1. All file paths are validated using the `safe_path()` function to prevent directory traversal
2. Chunk integrity can be verified using SHA256 hashes
3. Maximum file size is limited by Flask configuration
4. Session IDs are UUIDs to prevent guessing

## Migration from Old API

The existing `/download` endpoint remains unchanged for backward compatibility. Add `?compress=true` to enable compression for single-request downloads.

For new implementations, use the chunked endpoints for better performance on large files.
