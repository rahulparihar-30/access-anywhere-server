import eventlet
eventlet.monkey_patch()
from flask import Flask, request, send_from_directory, jsonify,render_template,send_file,abort
from flask_socketio import SocketIO
import mimetypes
import os
import shutil
import threading
import qrcode
import ngrok
from pyngrok import ngrok, conf
import socket
conf.get_default().auth_token = "2vxeqX1nAr80j0IdyUBCGOnUzno_7EG85Q8wzACCWn3HrjXZV"


app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins='*')

# Base directory for all file operations
BASE_DIR = "C:\\Users\\Rahul\\"  # Change this to your desired base directory

# Ensure the base directory exists
os.makedirs(BASE_DIR, exist_ok=True)


def safe_path(sub_path):
    full_path = os.path.abspath(os.path.join(BASE_DIR, sub_path))
    if not full_path.startswith(BASE_DIR):
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
    ngrok_tunnel = ngrok.connect(3000, subdomain="organic-vaguely-snapper", bind_tls=True)
    public_url = ngrok_tunnel.public_url
    print(f" * ngrok tunnel \"{public_url}\" -> \"http://127.0.0.1:3000\"")

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
    if not file_path:
        abort(400, "Missing 'path' parameter.")

    try:
        # Construct full path safely
        full_path = safe_path(file_path)

        # Security check: Verify the file exists and is within BASE_DIR
        if not os.path.isfile(full_path):
            abort(404, "File not found")

        # Send the file
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


if __name__ == "__main__":
    # Start ngrok in a separate thread
    # ngrok_thread = threading.Thread(target=start_ngrok)
    # ngrok_thread.daemon = True
    # ngrok_thread.start()
    ip = get_local_ip()
    print(ip)
    make_qr(f"{ip}:3000")
    # Run Flask app
    socketio.run(app, host="0.0.0.0", port=3000, debug=True,use_reloader=False)
