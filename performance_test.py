"""
Performance testing script for optimized file transfer.
Compares standard transfer vs optimized transfer with compression and parallel chunking.
"""

import os
import time
import tempfile
import random
from example_client import OptimizedFileTransferClient


def create_test_file(size_mb: int, pattern: str = 'random') -> str:
    """
    Create a test file of specified size.
    
    Args:
        size_mb: Size in megabytes
        pattern: 'random', 'text', or 'binary'
    
    Returns:
        Path to the created test file
    """
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.dat')
    size_bytes = size_mb * 1024 * 1024
    
    if pattern == 'text':
        # Highly compressible text data
        text_data = b"Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 100
        bytes_written = 0
        with open(temp_file.name, 'wb') as f:
            while bytes_written < size_bytes:
                chunk_size = min(len(text_data), size_bytes - bytes_written)
                f.write(text_data[:chunk_size])
                bytes_written += chunk_size
    
    elif pattern == 'binary':
        # Less compressible binary data
        with open(temp_file.name, 'wb') as f:
            bytes_written = 0
            while bytes_written < size_bytes:
                chunk_size = min(8192, size_bytes - bytes_written)
                f.write(os.urandom(chunk_size))
                bytes_written += chunk_size
    
    else:  # random
        # Mix of compressible and non-compressible data
        with open(temp_file.name, 'wb') as f:
            text_data = b"Repeated text pattern for compression testing. " * 20
            bytes_written = 0
            while bytes_written < size_bytes:
                if random.random() > 0.5:
                    # Write text (compressible)
                    chunk_size = min(len(text_data), size_bytes - bytes_written)
                    f.write(text_data[:chunk_size])
                else:
                    # Write random data (less compressible)
                    chunk_size = min(1024, size_bytes - bytes_written)
                    f.write(os.urandom(chunk_size))
                bytes_written += chunk_size
    
    return temp_file.name


def test_upload_performance(client: OptimizedFileTransferClient, 
                           file_path: str, 
                           test_name: str) -> dict:
    """Test upload performance with different configurations"""
    results = {}
    
    print(f"\n{'=' * 70}")
    print(f"Testing: {test_name}")
    print(f"{'=' * 70}")
    
    # Test 1: Standard upload (no compression, no chunking)
    print("\n[1/4] Standard upload (baseline)...")
    try:
        # Note: This would use a simple POST endpoint if available
        # For now, we'll simulate with chunking disabled
        start = time.time()
        stats = client.upload_file(file_path, '', compress=False)
        results['standard'] = {
            'time': stats['time'],
            'speed': stats['speed'],
            'size': stats['size']
        }
    except Exception as e:
        print(f"Failed: {e}")
        results['standard'] = None
    
    # Test 2: With compression only
    print("\n[2/4] With compression only...")
    try:
        stats = client.upload_file(file_path, '', compress=True)
        results['compressed'] = {
            'time': stats['time'],
            'speed': stats['speed'],
            'size': stats['size']
        }
    except Exception as e:
        print(f"Failed: {e}")
        results['compressed'] = None
    
    # Test 3: With parallel chunking (no compression)
    print("\n[3/4] With parallel chunking only...")
    try:
        client.max_workers = 5
        stats = client.upload_file(file_path, '', compress=False)
        results['parallel'] = {
            'time': stats['time'],
            'speed': stats['speed'],
            'size': stats['size']
        }
    except Exception as e:
        print(f"Failed: {e}")
        results['parallel'] = None
    
    # Test 4: Full optimization (compression + parallel chunking)
    print("\n[4/4] Full optimization (compression + parallel chunking)...")
    try:
        client.max_workers = 5
        stats = client.upload_file(file_path, '', compress=True)
        results['optimized'] = {
            'time': stats['time'],
            'speed': stats['speed'],
            'size': stats['size']
        }
    except Exception as e:
        print(f"Failed: {e}")
        results['optimized'] = None
    
    return results


def test_download_performance(client: OptimizedFileTransferClient,
                              remote_path: str,
                              test_name: str) -> dict:
    """Test download performance with different configurations"""
    results = {}
    
    print(f"\n{'=' * 70}")
    print(f"Testing: {test_name}")
    print(f"{'=' * 70}")
    
    # Test 1: Standard download
    print("\n[1/4] Standard download (baseline)...")
    try:
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        stats = client.download_file(remote_path, temp_file.name, 
                                     use_chunking=False, compress=False)
        results['standard'] = {
            'time': stats['time'],
            'speed': stats['speed'],
            'size': stats['size']
        }
        os.unlink(temp_file.name)
    except Exception as e:
        print(f"Failed: {e}")
        results['standard'] = None
    
    # Test 2: With compression only
    print("\n[2/4] With compression only...")
    try:
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        stats = client.download_file(remote_path, temp_file.name,
                                     use_chunking=False, compress=True)
        results['compressed'] = {
            'time': stats['time'],
            'speed': stats['speed'],
            'size': stats['size']
        }
        os.unlink(temp_file.name)
    except Exception as e:
        print(f"Failed: {e}")
        results['compressed'] = None
    
    # Test 3: With parallel chunking only
    print("\n[3/4] With parallel chunking only...")
    try:
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        client.max_workers = 5
        stats = client.download_file(remote_path, temp_file.name,
                                     use_chunking=True, compress=False)
        results['parallel'] = {
            'time': stats['time'],
            'speed': stats['speed'],
            'size': stats['size']
        }
        os.unlink(temp_file.name)
    except Exception as e:
        print(f"Failed: {e}")
        results['parallel'] = None
    
    # Test 4: Full optimization
    print("\n[4/4] Full optimization (compression + parallel chunking)...")
    try:
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        client.max_workers = 5
        stats = client.download_file(remote_path, temp_file.name,
                                     use_chunking=True, compress=True)
        results['optimized'] = {
            'time': stats['time'],
            'speed': stats['speed'],
            'size': stats['size']
        }
        os.unlink(temp_file.name)
    except Exception as e:
        print(f"Failed: {e}")
        results['optimized'] = None
    
    return results


def print_comparison_table(results: dict, operation: str):
    """Print a comparison table of results"""
    print(f"\n{'=' * 70}")
    print(f"{operation} Performance Comparison")
    print(f"{'=' * 70}")
    
    if not any(results.values()):
        print("No results available")
        return
    
    # Get baseline (standard) results
    baseline = results.get('standard')
    if not baseline:
        print("Warning: No baseline results available")
        baseline_time = 1.0  # Avoid division by zero
    else:
        baseline_time = baseline['time']
    
    print(f"\n{'Method':<30} {'Time (s)':<12} {'Speed (MB/s)':<15} {'Improvement':<15}")
    print("-" * 70)
    
    for method, data in results.items():
        if data:
            improvement = ((baseline_time - data['time']) / baseline_time * 100) if baseline else 0
            improvement_str = f"{improvement:+.1f}%" if baseline else "N/A"
            
            method_display = method.replace('_', ' ').title()
            print(f"{method_display:<30} {data['time']:<12.2f} {data['speed']:<15.2f} {improvement_str:<15}")


def main():
    """Run performance tests"""
    print("=" * 70)
    print("FILE TRANSFER OPTIMIZATION - PERFORMANCE TEST")
    print("=" * 70)
    
    # Initialize client
    client = OptimizedFileTransferClient(
        base_url='http://localhost:3000',
        max_workers=5
    )
    
    # Test configurations
    test_configs = [
        {'size_mb': 10, 'pattern': 'text', 'name': '10MB Text File (Highly Compressible)'},
        {'size_mb': 10, 'pattern': 'binary', 'name': '10MB Binary File (Low Compressibility)'},
        {'size_mb': 50, 'pattern': 'random', 'name': '50MB Mixed File (Moderate Compressibility)'},
    ]
    
    all_results = {}
    
    for config in test_configs:
        print(f"\n\n{'#' * 70}")
        print(f"Creating test file: {config['name']}")
        print(f"{'#' * 70}")
        
        # Create test file
        test_file = create_test_file(config['size_mb'], config['pattern'])
        file_size_mb = os.path.getsize(test_file) / (1024 * 1024)
        print(f"Test file created: {test_file} ({file_size_mb:.2f} MB)")
        
        try:
            # Test upload performance
            upload_results = test_upload_performance(client, test_file, 
                                                    f"Upload - {config['name']}")
            
            # Print upload comparison
            print_comparison_table(upload_results, "Upload")
            
            # Store results
            all_results[config['name']] = {
                'upload': upload_results,
                'size_mb': file_size_mb
            }
            
        finally:
            # Clean up test file
            if os.path.exists(test_file):
                os.unlink(test_file)
    
    # Print summary
    print("\n\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    for test_name, data in all_results.items():
        print(f"\n{test_name} ({data['size_mb']:.2f} MB):")
        
        upload = data.get('upload', {})
        
        if upload.get('optimized') and upload.get('standard'):
            opt = upload['optimized']
            std = upload['standard']
            time_improvement = ((std['time'] - opt['time']) / std['time'] * 100)
            speed_improvement = ((opt['speed'] - std['speed']) / std['speed'] * 100)
            
            print(f"  Upload Optimization:")
            print(f"    - Time reduced by: {time_improvement:.1f}%")
            print(f"    - Speed increased by: {speed_improvement:.1f}%")
            print(f"    - From {std['speed']:.2f} MB/s to {opt['speed']:.2f} MB/s")
    
    print("\n" + "=" * 70)
    print("Performance testing completed!")
    print("=" * 70)


if __name__ == '__main__':
    main()
