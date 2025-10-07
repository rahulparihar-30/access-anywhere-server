import eventlet
eventlet.monkey_patch()
from flask import Flask, request, send_from_directory, jsonify, render_template, send_file, abort, Response, stream_with_context
from flask_socketio import SocketIO
from werkzeug.utils import secure_filename
import mimetypes
import os
import shutil
import threading
import qrcode
import ngrok
from pyngrok import ngrok, conf as ngrok_conf
import socket
import tempfile
import uuid
import logging
from concurrent.futures import ThreadPoolExecutor
import file_transfer_utils as ftu
import config

# Configure ngrok
ngrok_conf.get_default().auth_token = config.NGROK_AUTH_TOKEN

# Configure logging
if config.ENABLE_LOGGING:
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL),
        format=config.LOG_FORMAT,
        filename=config.LOG_FILE
    )
    logger = logging.getLogger(__name__)
else:
    logger = logging.getLogger(__name__)
    logger.addHandler(logging.NullHandler())


app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins=config.CORS_ALLOWED_ORIGINS)
app.config['MAX_CONTENT_LENGTH'] = config.MAX_CONTENT_LENGTH

# Use configuration values
BASE_DIR = config.BASE_DIR
CHUNK_SIZE = config.CHUNK_SIZE
COMPRESSION_LEVEL = config.COMPRESSION_LEVEL
MAX_PARALLEL_CHUNKS = config.MAX_PARALLEL_CHUNKS
TEMP_DIR = config.TEMP_DIR

# Thread pool for parallel processing
executor = ThreadPoolExecutor(max_workers=config.THREAD_POOL_SIZE)

# Print configuration on startup
if config.DEBUG:
    config.print_config()


def safe_path(sub_path):
    full_path = os.path.abspath(os.path.join(BASE_DIR, sub_path))
    if not full_path.startswith(BASE_DIR):
        logger.warning(f"Path traversal attempt blocked: {sub_path}")
        raise ValueError("Access denied: path outside of base directory")
    return full_path

def make_qr(public_url):
    qr = qrcode.make(public_url)
    os.makedirs("static", exist_ok=True)
    qr.save("static/qr_code.png")  # Save QR code image

# Start ngrok to expose the Flask app to the internet
def start_ngrok():
    ngrok.kill()
    # Open a tunnel using your reserved static subdomain
    ngrok_tunnel = ngrok.connect(config.PORT, subdomain=config.NGROK_SUBDOMAIN, bind_tls=True)
    public_url = ngrok_tunnel.public_url
    logger.info(f"Ngrok tunnel established: {public_url}")
    print(f" * ngrok tunnel \"{public_url}\" -> \"http://127.0.0.1:{config.PORT}\"")

    # Generate QR code with ngrok URL
    make_qr(public_url)
    return public_url


# Socket.IO event to broadcast file updates
@socketio.on('file_update')
def handle_file_update(data):
    socketio.emit('file_update', {'files': data})

@app.route("/",methods=["GET"])
def home():
    return render_template("index.html")

# List files and folders
@app.route("/list", methods=["GET"])
def list_files():
    try:
        path = safe_path(request.args.get("path", ""))
        if not os.path.exists(path):
            print(path)
            return jsonify({"error": "Path not found"}), 404
        items = []
        for item in os.listdir(path):
            full_path = os.path.join(path, item)
            items.append({
                "name": item,
                "is_file": os.path.isfile(full_path),
                "is_dir": os.path.isdir(full_path)
            })
        return jsonify(items)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/home", methods=["GET"])
def home_directory():
    try:
        path = BASE_DIR  # Always use the base directory
        items = []
        for item in os.listdir(path):
            full_path = os.path.join(path, item)
            items.append({
                "name": item,
                "is_file": os.path.isfile(full_path),
                "is_dir": os.path.isdir(full_path)
            })
        return jsonify(items)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# Download a file
@app.route('/download', methods=['GET'])
def download_file():
    file_path = request.args.get('path')  # Get path from query param
    compress = request.args.get('compress', 'false').lower() == 'true'
    
    if not file_path:
        abort(400, "Missing 'path' parameter.")

    try:
        # Construct full path safely
        full_path = safe_path(file_path)

        # Security check: Verify the file exists and is within BASE_DIR
        if not os.path.isfile(full_path):
            abort(404, "File not found")

        # If compression is requested and the file should be compressed
        if compress and ftu.should_compress_file(full_path):
            # Create a temporary compressed file
            temp_compressed = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}.gz")
            try:
                ftu.compress_file(full_path, temp_compressed, COMPRESSION_LEVEL)
                
                # Send compressed file
                response = send_file(
                    temp_compressed,
                    mimetype='application/gzip',
                    as_attachment=True,
                    download_name=f"{os.path.basename(full_path)}.gz"
                )
                
                # Clean up temp file after sending
                @response.call_on_close
                def cleanup():
                    try:
                        os.remove(temp_compressed)
                    except:
                        pass
                
                return response
            except Exception as e:
                # Clean up on error
                if os.path.exists(temp_compressed):
                    os.remove(temp_compressed)
                raise e
        else:
            # Send the file normally
            mime_type, _ = mimetypes.guess_type(full_path)
            return send_file(
                full_path,
                mimetype=mime_type or 'application/octet-stream',
                as_attachment=True,
                download_name=os.path.basename(full_path)
            )
    except ValueError as e:
        abort(403, str(e))  # Path traversal attempt
    except Exception as e:
        abort(500, f"Internal Server Error: {str(e)}")
# Get file information for optimized download
@app.route('/file/info', methods=['GET'])
def get_file_info():
    """Get file information including chunk details for parallel download"""
    file_path = request.args.get('path')
    
    if not file_path:
        return jsonify({"error": "Missing 'path' parameter"}), 400
    
    try:
        full_path = safe_path(file_path)
        
        if not os.path.isfile(full_path):
            return jsonify({"error": "File not found"}), 404
        
        # Get file info
        file_info = ftu.get_file_info(full_path, CHUNK_SIZE)
        
        # Determine if compression is recommended
        should_compress = ftu.should_compress_file(full_path)
        compression_ratio = ftu.estimate_compression_ratio(full_path) if should_compress else 1.0
        
        file_info['should_compress'] = should_compress
        file_info['estimated_compression_ratio'] = compression_ratio
        file_info['recommended_chunk_size'] = CHUNK_SIZE
        file_info['max_parallel_chunks'] = MAX_PARALLEL_CHUNKS
        
        logger.info(f"File info requested: {file_path} ({file_info['file_size']} bytes, {file_info['total_chunks']} chunks)")
        
        return jsonify(file_info)
    
    except ValueError as e:
        logger.warning(f"File info request denied: {file_path}")
        return jsonify({"error": str(e)}), 403
    except Exception as e:
        logger.error(f"Error getting file info for {file_path}: {e}")
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Download a specific chunk of a file
@app.route('/download/chunk', methods=['GET'])
def download_chunk():
    """Download a specific chunk of a file with optional compression"""
    file_path = request.args.get('path')
    chunk_id = request.args.get('chunk_id', type=int)
    compress = request.args.get('compress', 'true').lower() == 'true'
    
    if not file_path or chunk_id is None:
        return jsonify({"error": "Missing required parameters"}), 400
    
    try:
        full_path = safe_path(file_path)
        
        if not os.path.isfile(full_path):
            return jsonify({"error": "File not found"}), 404
        
        # Read the chunk
        chunk_data, metadata = ftu.read_file_chunk(
            full_path, 
            chunk_id, 
            CHUNK_SIZE, 
            compress=compress
        )
        
        # Create response with chunk data
        response = Response(chunk_data, mimetype='application/octet-stream')
        
        # Add metadata to headers
        response.headers['X-Chunk-Id'] = str(metadata.chunk_id)
        response.headers['X-Chunk-Hash'] = metadata.chunk_hash
        response.headers['X-Chunk-Size'] = str(metadata.chunk_size)
        response.headers['X-Total-Chunks'] = str(metadata.total_chunks)
        response.headers['X-Compressed'] = str(compress)
        
        return response
    
    except ValueError as e:
        return jsonify({"error": str(e)}), 403
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Initialize upload session
@app.route('/upload/init', methods=['POST'])
def init_upload():
    """Initialize a new upload session for chunked upload"""
    data = request.json
    
    filename = data.get('filename')
    total_chunks = data.get('total_chunks')
    destination_path = data.get('path', '')
    compressed = data.get('compressed', True)
    
    if not filename or total_chunks is None:
        return jsonify({"error": "Missing required parameters"}), 400
    
    try:
        # Create unique session ID
        session_id = str(uuid.uuid4())
        
        # Validate destination path
        dest_path = safe_path(destination_path)
        if not os.path.exists(dest_path):
            os.makedirs(dest_path, exist_ok=True)
        
        # Create upload session
        session = ftu.upload_manager.create_session(
            session_id, 
            filename, 
            total_chunks, 
            compressed
        )
        
        logger.info(f"Upload session initialized: {session_id} for {filename} ({total_chunks} chunks, compressed={compressed})")
        
        return jsonify({
            "session_id": session_id,
            "status": "initialized",
            "filename": filename,
            "total_chunks": total_chunks,
            "max_parallel_chunks": MAX_PARALLEL_CHUNKS
        })
    
    except ValueError as e:
        logger.warning(f"Upload init denied: {destination_path}")
        return jsonify({"error": str(e)}), 403
    except Exception as e:
        logger.error(f"Error initializing upload for {filename}: {e}")
        return jsonify({"error": str(e)}), 500


# Upload a chunk
@app.route('/upload/chunk', methods=['POST'])
def upload_chunk():
    """Upload a single chunk of a file"""
    session_id = request.form.get('session_id')
    chunk_id = request.form.get('chunk_id', type=int)
    chunk_hash = request.form.get('chunk_hash')
    
    if not session_id or chunk_id is None:
        return jsonify({"error": "Missing required parameters"}), 400
    
    if 'chunk_data' not in request.files:
        return jsonify({"error": "Missing chunk data"}), 400
    
    try:
        # Get upload session
        session = ftu.upload_manager.get_session(session_id)
        if not session:
            return jsonify({"error": "Invalid session ID"}), 404
        
        # Read chunk data
        chunk_file = request.files['chunk_data']
        chunk_data = chunk_file.read()
        
        # Verify chunk integrity if hash is provided
        if chunk_hash and not ftu.verify_chunk_integrity(chunk_data, chunk_hash):
            return jsonify({"error": "Chunk integrity verification failed"}), 400
        
        # Add chunk to session
        success = ftu.upload_manager.add_chunk(session_id, chunk_id, chunk_data)
        
        if not success:
            return jsonify({"error": "Failed to add chunk"}), 500
        
        # Check if upload is complete
        is_complete = session.is_complete()
        missing_chunks = session.get_missing_chunks() if not is_complete else []
        
        return jsonify({
            "status": "chunk_received",
            "chunk_id": chunk_id,
            "received_chunks": len(session.received_chunks),
            "total_chunks": session.total_chunks,
            "is_complete": is_complete,
            "missing_chunks": missing_chunks
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Finalize upload
@app.route('/upload/finalize', methods=['POST'])
def finalize_upload():
    """Finalize upload by reassembling chunks"""
    data = request.json
    session_id = data.get('session_id')
    destination_path = data.get('path', '')
    
    if not session_id:
        return jsonify({"error": "Missing session_id"}), 400
    
    try:
        # Get upload session
        session = ftu.upload_manager.get_session(session_id)
        if not session:
            logger.warning(f"Upload finalize failed: invalid session {session_id}")
            return jsonify({"error": "Invalid session ID"}), 404
        
        # Check if all chunks are received
        if not session.is_complete():
            missing_chunks = session.get_missing_chunks()
            logger.warning(f"Upload incomplete for session {session_id}: missing {len(missing_chunks)} chunks")
            return jsonify({
                "error": "Upload incomplete",
                "missing_chunks": missing_chunks
            }), 400
        
        # Validate destination path
        dest_dir = safe_path(destination_path)
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir, exist_ok=True)
        
        output_path = os.path.join(dest_dir, session.filename)
        
        # Reassemble chunks
        file_size = ftu.reassemble_chunks(
            session.chunk_data,
            output_path,
            decompress=session.compressed
        )
        
        logger.info(f"Upload completed: {session.filename} ({file_size} bytes) - session {session_id}")
        
        # Clean up session
        ftu.upload_manager.remove_session(session_id)
        
        # Emit file update event
        socketio.emit('file_update', {'path': destination_path})
        
        return jsonify({
            "status": "completed",
            "filename": session.filename,
            "file_size": file_size,
            "path": output_path
        })
    
    except ValueError as e:
        logger.warning(f"Upload finalize denied for session {session_id}")
        return jsonify({"error": str(e)}), 403
    except Exception as e:
        logger.error(f"Error finalizing upload for session {session_id}: {e}")
        # Clean up session on error
        ftu.upload_manager.remove_session(session_id)
        return jsonify({"error": str(e)}), 500


# Get upload session status
@app.route('/upload/status', methods=['GET'])
def upload_status():
    """Get the status of an upload session"""
    session_id = request.args.get('session_id')
    
    if not session_id:
        return jsonify({"error": "Missing session_id"}), 400
    
    try:
        session = ftu.upload_manager.get_session(session_id)
        if not session:
            return jsonify({"error": "Session not found"}), 404
        
        return jsonify({
            "session_id": session_id,
            "filename": session.filename,
            "total_chunks": session.total_chunks,
            "received_chunks": len(session.received_chunks),
            "is_complete": session.is_complete(),
            "missing_chunks": session.get_missing_chunks()
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Cancel upload session
@app.route('/upload/cancel', methods=['POST'])
def cancel_upload():
    """Cancel an upload session"""
    data = request.json
    session_id = data.get('session_id')
    
    if not session_id:
        return jsonify({"error": "Missing session_id"}), 400
    
    try:
        ftu.upload_manager.remove_session(session_id)
        return jsonify({"status": "cancelled"})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Delete a file or folder
@app.route("/delete", methods=["POST"])
def delete():
    try:
        path = safe_path(request.json.get("path"))
        if os.path.isfile(path):
            os.remove(path)
        elif os.path.isdir(path):
            shutil.rmtree(path)
        else:
            return jsonify({"error": "Invalid path"}), 400
        return jsonify({"status": "deleted"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# Rename a file or folder
@app.route("/rename", methods=["POST"])
def rename():
    try:
        old_path = safe_path(request.json.get("old_path"))
        new_name = request.json.get("new_name")
        new_path = os.path.join(os.path.dirname(old_path), new_name)
        new_path = safe_path(os.path.relpath(new_path, BASE_DIR))
        os.rename(old_path, new_path)
        return jsonify({"status": "renamed"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# Create a new folder
@app.route("/mkdir", methods=["POST"])
def make_folder():
    try:
        path = safe_path(request.json.get("path"))
        os.makedirs(path, exist_ok=True)
        return jsonify({"status": "folder created"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip


def cleanup_expired_sessions():
    """Periodic cleanup of expired upload sessions"""
    import time
    while True:
        time.sleep(config.SESSION_CLEANUP_INTERVAL)
        try:
            before_count = len(ftu.upload_manager.sessions)
            ftu.upload_manager.cleanup_expired_sessions()
            after_count = len(ftu.upload_manager.sessions)
            cleaned = before_count - after_count
            if cleaned > 0:
                logger.info(f"Cleaned up {cleaned} expired upload sessions")
        except Exception as e:
            logger.error(f"Error cleaning up sessions: {e}")


if __name__ == "__main__":
    # Start ngrok in a separate thread
    # ngrok_thread = threading.Thread(target=start_ngrok)
    # ngrok_thread.daemon = True
    # ngrok_thread.start()
    
    # Start cleanup thread for expired upload sessions
    cleanup_thread = threading.Thread(target=cleanup_expired_sessions)
    cleanup_thread.daemon = True
    cleanup_thread.start()
    
    ip = get_local_ip()
    print(ip)
    make_qr(f"{ip}:3000")
    # Run Flask app
    socketio.run(app, host="0.0.0.0", port=3000, debug=True, use_reloader=False)
