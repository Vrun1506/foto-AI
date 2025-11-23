from flask import Flask, request, jsonify
from flask_cors import CORS
import oci
import os
from dotenv import load_dotenv
from io import BytesIO
import base64
import re
import sys
from pathlib import Path

load_dotenv()

# Add agentic-workflow to path so we can import runner
workflow_path = str(Path(__file__).parent.parent / "agentic-workflow")
if workflow_path not in sys.path:
    sys.path.insert(0, workflow_path)

try:
    from runner import run_agent
    AGENT_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import agent runner: {e}")
    AGENT_AVAILABLE = False

load_dotenv()

# Configuration
BUCKET_NAME = os.getenv("OCI_BUCKET_NAME")
NAMESPACE = os.getenv("OCI_NAMESPACE")  # Add this to your .env
REGION = os.getenv("OCI_REGION")

config = {
    "user": os.getenv("OCI_USER_OCID"),
    "fingerprint": os.getenv("OCI_FINGERPRINT"),
    "tenancy": os.getenv("OCI_TENANCY_OCID"),
    "region": os.getenv("OCI_REGION"),
    "key_file": os.getenv("OCI_KEY_FILE")
}

app = Flask(__name__)
# Allow localhost origins (any port) for development (Vite / local frontends).
# This restricts CORS to localhost and 127.0.0.1 while allowing any port.
localhost_regex = r"^https?://(localhost|127\.0\.0\.1|\[::1\])(:\d+)?$"
CORS(app, resources={r"/*": {"origins": localhost_regex}}, supports_credentials=True)

# Initialize OCI Object Storage client
object_storage_client = oci.object_storage.ObjectStorageClient(config)

# Get namespace if not provided in env
if not NAMESPACE:
    NAMESPACE = object_storage_client.get_namespace().data


@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "service": "OCI Object Storage API"}), 200


@app.route("/upload", methods=["POST"])
def upload_file():
    try:
        # Check for file
        file = request.files.get("file")
        if not file or file.filename == "":
            return jsonify({"error": "No file provided"}), 400

        # Get prompt text
        prompt = request.form.get("prompt", "")

        # Optional: custom object name
        object_name = request.form.get("object_name", file.filename)

        # Reset file stream pointer
        file.stream.seek(0)

        # Upload file to OCI Object Storage
        object_storage_client.put_object(
            namespace_name=NAMESPACE,
            bucket_name=BUCKET_NAME,
            object_name=object_name,
            put_object_body=file.stream,  # Pass stream directly
            content_type=file.mimetype or "application/octet-stream"
        )

        return jsonify({
            "message": "File uploaded successfully",
            "object_name": object_name,
            "prompt": prompt,
            "bucket": BUCKET_NAME
        }), 200

    except oci.exceptions.ServiceError as e:
        return jsonify({"error": f"OCI Service Error: {str(e)}"}), e.status
    except Exception as e:
        return jsonify({"error": f"Unexpected Error: {str(e)}"}), 500


@app.route("/process", methods=["POST"])
def process_image():
    """
    Process an uploaded image with the Photoshop agent.
    Expects JSON body with:
    - object_name: Name of file in OCI bucket (e.g., image.jpg)
    - prompt: User's processing instructions
    """
    if not AGENT_AVAILABLE:
        return jsonify({"error": "Agent processing not available. Photoshop plugin or dependencies may not be configured."}), 503
    
    try:
        # Parse request
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400
        
        object_name = data.get("object_name")
        prompt = data.get("prompt", "")
        
        if not object_name:
            return jsonify({"error": "Missing required field: object_name"}), 400
        
        if not prompt:
            return jsonify({"error": "Missing required field: prompt"}), 400
        
        print(f"\n📥 Processing request: object={object_name}, prompt={prompt}\n")
        
        # Download file from OCI to temporary location
        try:
            obj = object_storage_client.get_object(
                namespace_name=NAMESPACE,
                bucket_name=BUCKET_NAME,
                object_name=object_name
            )
            file_data = obj.data.content
        except oci.exceptions.ServiceError as e:
            if e.status == 404:
                return jsonify({"error": f"File not found in bucket: {object_name}"}), 404
            return jsonify({"error": f"Failed to retrieve file: {str(e)}"}), 500
        
        # Save file temporarily for agent processing
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=Path(object_name).suffix, delete=False) as tmp:
            tmp.write(file_data)
            tmp_path = tmp.name
        
        try:
            # Run agent with the file
            print(f"🤖 Running agent with {tmp_path}...\n")
            result = run_agent(tmp_path, prompt)
            
            # Clean up temp file
            try:
                os.unlink(tmp_path)
            except:
                pass
            
            return jsonify(result), 200 if result["status"] == "success" else 400
        
        except Exception as e:
            # Clean up temp file on error
            try:
                os.unlink(tmp_path)
            except:
                pass
            
            print(f"❌ Agent error: {str(e)}\n")
            return jsonify({
                "status": "error",
                "message": f"Agent processing failed: {str(e)}",
                "result": None
            }), 500

    except Exception as e:
        print(f"❌ Process endpoint error: {str(e)}\n")
        return jsonify({"error": f"Processing error: {str(e)}"}), 500


@app.route('/download/<path:object_name>', methods=['GET'])
def download_file(object_name):
    try:
        obj = object_storage_client.get_object(
            namespace_name=NAMESPACE,
            bucket_name=BUCKET_NAME,
            object_name=object_name
        )

        file_data = obj.data.content
        encoded = base64.b64encode(file_data).decode('utf-8')

        return jsonify({
            "object_name": object_name,
            "content_type": obj.headers.get('Content-Type', 'application/octet-stream'),
            "size": len(file_data),
            "data": encoded
        }), 200

    except oci.exceptions.ServiceError as e:
        if e.status == 404:
            return jsonify({"error": "File not found"}), 404
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/list', methods=['GET'])
def list_objects():
    try:
        limit = request.args.get('limit', 100, type=int)
        prefix = request.args.get('prefix', '')

        objects = object_storage_client.list_objects(
            namespace_name=NAMESPACE,
            bucket_name=BUCKET_NAME,
            prefix=prefix,
            limit=limit
        )

        object_list = [{
            "name": obj.name,
            "size": obj.size,
            "time_created": obj.time_created.isoformat() if obj.time_created else None,
            "md5": obj.md5
        } for obj in objects.data.objects]

        return jsonify({
            "bucket": BUCKET_NAME,
            "objects": object_list,
            "count": len(object_list)
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/delete/<path:object_name>', methods=['DELETE'])
def delete_file(object_name):
    try:
        object_storage_client.delete_object(
            namespace_name=NAMESPACE,
            bucket_name=BUCKET_NAME,
            object_name=object_name
        )
        return jsonify({"message": "File deleted successfully", "object_name": object_name}), 200

    except oci.exceptions.ServiceError as e:
        if e.status == 404:
            return jsonify({"error": "File not found"}), 404
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/metadata/<path:object_name>', methods=['GET'])
def get_metadata(object_name):
    try:
        head_obj = object_storage_client.head_object(
            namespace_name=NAMESPACE,
            bucket_name=BUCKET_NAME,
            object_name=object_name
        )

        return jsonify({
            "object_name": object_name,
            "content_type": head_obj.headers.get('Content-Type'),
            "content_length": head_obj.headers.get('Content-Length'),
            "etag": head_obj.headers.get('ETag'),
            "last_modified": head_obj.headers.get('Last-Modified')
        }), 200

    except oci.exceptions.ServiceError as e:
        if e.status == 404:
            return jsonify({"error": "File not found"}), 404
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Internal server error"}), 500


if __name__ == '__main__':
    required_vars = ['OCI_BUCKET_NAME', 'OCI_REGION', 'OCI_USER_OCID',
                     'OCI_FINGERPRINT', 'OCI_TENANCY_OCID', 'OCI_KEY_FILE']
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
        exit(1)

    print(f"Starting Flask API...")
    print(f"Bucket: {BUCKET_NAME}")
    print(f"Region: {REGION}")
    print(f"Namespace: {NAMESPACE}")

    app.run(debug=True, host='0.0.0.0', port=5001)
