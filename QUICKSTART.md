# Quick Start Guide - Optimized File Transfer

This guide will help you get started with the optimized file transfer features including compression and parallel chunking.

## Prerequisites

- Python 3.8 or higher
- Flask and dependencies installed (see requirements.txt)

## Installation

1. **Install dependencies** (if not already done):
   ```bash
   pip install -r requirements.txt
   ```

2. **Start the server**:
   ```bash
   python main.py
   ```
   
   The server will start on `http://0.0.0.0:3000`

## Testing the Features

### Option 1: Using the Example Client (Recommended)

The `example_client.py` script provides a ready-to-use Python client:

```python
from example_client import OptimizedFileTransferClient

# Initialize client
client = OptimizedFileTransferClient(
    base_url='http://localhost:3000',
    max_workers=5  # Number of parallel connections
)

# Upload a file
client.upload_file(
    local_path='my_file.pdf',
    destination_path='Documents',
    compress=True
)

# Download a file
client.download_file(
    remote_path='Documents/my_file.pdf',
    local_path='downloaded_file.pdf',
    use_chunking=True,
    compress=True
)
```

### Option 2: Using cURL (for testing individual endpoints)

#### Get file information:
```bash
curl "http://localhost:3000/file/info?path=example.txt"
```

#### Download with compression:
```bash
curl "http://localhost:3000/download?path=example.txt&compress=true" -o file.gz
```

#### Initialize upload:
```bash
curl -X POST http://localhost:3000/upload/init \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "test.txt",
    "total_chunks": 5,
    "path": "",
    "compressed": true
  }'
```

#### Upload a chunk:
```bash
curl -X POST http://localhost:3000/upload/chunk \
  -F "session_id=YOUR_SESSION_ID" \
  -F "chunk_id=0" \
  -F "chunk_hash=abc123..." \
  -F "chunk_data=@chunk_0.dat"
```

### Option 3: Running Performance Tests

Run the performance testing script to compare standard vs optimized transfers:

```bash
python performance_test.py
```

This will:
- Create test files of various sizes and types
- Test different transfer methods (standard, compressed, parallel, optimized)
- Display performance comparisons with improvement percentages

## Configuration

You can adjust these settings in `main.py`:

```python
# Chunk size (default: 1MB)
CHUNK_SIZE = 1024 * 1024

# Compression level (1-9, where 9 is maximum compression)
COMPRESSION_LEVEL = 6

# Maximum parallel chunk transfers
MAX_PARALLEL_CHUNKS = 5
```

### Recommended Settings by Use Case:

**Slow Internet (< 5 Mbps):**
```python
CHUNK_SIZE = 512 * 1024      # 512KB chunks
COMPRESSION_LEVEL = 9         # Maximum compression
MAX_PARALLEL_CHUNKS = 3       # Fewer connections
```

**Fast Internet (> 50 Mbps):**
```python
CHUNK_SIZE = 2 * 1024 * 1024  # 2MB chunks
COMPRESSION_LEVEL = 3         # Light compression
MAX_PARALLEL_CHUNKS = 8       # More connections
```

**Unstable Connection:**
```python
CHUNK_SIZE = 256 * 1024       # Smaller chunks (easier to retry)
COMPRESSION_LEVEL = 6         # Balanced
MAX_PARALLEL_CHUNKS = 2       # Fewer connections
```

## Expected Performance Improvements

Based on typical scenarios:

### Text/Code Files (High Compressibility)
- **3-5x faster** downloads with compression
- **50-80%** bandwidth reduction
- **2-3x faster** uploads with parallel chunking

### Images/Documents (Moderate Compressibility)
- **2-3x faster** downloads with compression
- **30-50%** bandwidth reduction
- **1.5-2x faster** uploads with parallel chunking

### Already Compressed Files (ZIP, MP4, JPEG)
- **No compression benefit** (automatically detected)
- **1.5-2x faster** with parallel chunking only

### Large Files (> 100MB)
- **2-4x faster** with parallel chunking
- Best performance with both compression and parallel transfer

## API Endpoints Overview

### Download Endpoints
- `GET /file/info` - Get file metadata
- `GET /download` - Download file (with optional compression)
- `GET /download/chunk` - Download specific chunk

### Upload Endpoints
- `POST /upload/init` - Start upload session
- `POST /upload/chunk` - Upload a chunk
- `GET /upload/status` - Check upload progress
- `POST /upload/finalize` - Complete upload
- `POST /upload/cancel` - Cancel upload

For detailed API documentation, see [API_DOCUMENTATION.md](./API_DOCUMENTATION.md)

## Troubleshooting

### Issue: Slow upload/download despite optimization

**Solutions:**
- Increase `MAX_PARALLEL_CHUNKS` (but don't exceed ~10)
- Adjust `CHUNK_SIZE` based on your connection
- Check if the file type benefits from compression

### Issue: Upload session expired

**Solution:**
- Sessions expire after 1 hour of inactivity
- Always finalize or cancel uploads
- For very large files, increase timeout in `file_transfer_utils.py`:
  ```python
  upload_manager = UploadSessionManager(session_timeout=7200)  # 2 hours
  ```

### Issue: Memory usage is high

**Solutions:**
- Reduce `MAX_PARALLEL_CHUNKS`
- Decrease `CHUNK_SIZE`
- The cleanup thread runs every 5 minutes to free memory

### Issue: Compression not helping

**Solution:**
- Some files are already compressed (ZIP, JPEG, MP4, etc.)
- The system automatically detects this and skips compression
- Check file type with `/file/info` endpoint

## Security Considerations

1. **Path Validation**: All paths are validated using `safe_path()` to prevent directory traversal
2. **Chunk Integrity**: SHA256 hashes verify chunk integrity
3. **Session IDs**: UUIDs prevent session hijacking
4. **File Size Limits**: Maximum file size is configurable in Flask

## Next Steps

- Read the full [API Documentation](./API_DOCUMENTATION.md)
- Integrate the client code into your mobile app
- Adjust configuration based on your users' typical connection speeds
- Monitor performance with the test scripts

## Support

For issues or questions:
1. Check the [API Documentation](./API_DOCUMENTATION.md)
2. Review the example code in `example_client.py`
3. Open an issue on GitHub

## Contributing

Contributions are welcome! Areas for improvement:
- Additional compression algorithms (Brotli, Zstandard)
- Resume support for interrupted downloads
- Bandwidth throttling
- Progress callbacks for UI integration
