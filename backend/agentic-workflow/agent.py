"""
Photoshop Agent using direct Socket.IO connection to proxy.
Clean, simple architecture for LLM-powered Photoshop control.

Architecture:
  Frontend → This Backend (LLM) → Socket.IO → Proxy → Photoshop
"""
import socketio
import json
import os
import sys
import threading
from queue import Queue
from dotenv import load_dotenv

# --- Oracle / Open Agent Spec Imports ---
from pyagentspec.llms import OpenAiConfig
from pyagentspec.agent import Agent
from pyagentspec.tools import ServerTool
from pyagentspec.property import IntegerProperty, StringProperty, ObjectProperty, BooleanProperty
from wayflowcore.agentspec import AgentSpecLoader

load_dotenv()

# ==========================================
# 1. CONFIGURATION
# ==========================================
PROXY_URL = "http://localhost:3001"
PROXY_TIMEOUT = 30


# ==========================================
# 2. SOCKET.IO CLIENT
# ==========================================
def send_photoshop_command(action: str, options: dict, timeout: int = PROXY_TIMEOUT) -> dict:
    """Send command to Photoshop via Socket.IO proxy."""
    sio = socketio.Client(logger=False)
    response_queue = Queue()
    error = [None]
    
    @sio.event
    def connect():
        sio.emit('command_packet', {
            'type': "command",
            'application': "photoshop",
            'command': {"application": "photoshop", "action": action, "options": options}
        })
    
    @sio.event
    def packet_response(data):
        response_queue.put(data)
        sio.disconnect()
    
    @sio.event
    def disconnect():
        if response_queue.empty():
            response_queue.put(None)
    
    @sio.event
    def connect_error(e):
        error[0] = e
        response_queue.put(None)
    
    def run():
        try:
            sio.connect(PROXY_URL, transports=['websocket'])
            sio.wait()
        except Exception as e:
            error[0] = e
            if response_queue.empty():
                response_queue.put(None)
    
    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    
    try:
        response = response_queue.get(timeout=timeout)
        if error[0]:
            raise ConnectionError(f"Proxy connection failed: {error[0]}")
        if response is None:
            raise TimeoutError("No response from Photoshop")
        return response
    finally:
        if sio.connected:
            sio.disconnect()
        thread.join(timeout=1)


# ==========================================
# 3. PHOTOSHOP TOOL FUNCTIONS
# ==========================================

def create_document(*, document_name: str = None, width: int = None, height: int = None,
                    resolution: int = 72, fill_color: dict = None, color_mode: str = "RGB") -> str:
    """Create a new Photoshop document."""
    if not document_name or not width or not height:
        return " Missing required: document_name, width, height"
    
    fill_color = fill_color or {"red": 255, "green": 255, "blue": 255}
    print(f"🎨 Creating '{document_name}' ({width}x{height})...")
    
    response = send_photoshop_command("createDocument", {
        "name": document_name, "width": int(width), "height": int(height),
        "resolution": int(resolution), "fillColor": fill_color, "colorMode": color_mode
    })
    
    if response and response.get("status") == "SUCCESS":
        doc = response.get("document", {})
        return f"Created document '{doc.get('name')}' (ID: {doc.get('id')})"
    return f" Failed: {response.get('message', 'Unknown error') if response else 'No response'}"


def get_documents(**kwargs) -> str:
    """List all open Photoshop documents."""
    print("📋 Getting documents...")
    response = send_photoshop_command("getDocuments", {})
    
    if response and response.get("status") == "SUCCESS":
        docs = response.get("documents", [])
        if docs:
            return "Open documents:\n" + "\n".join([f"  - {d.get('name')} (ID: {d.get('id')})" for d in docs])
        return "No documents open"
    return " Failed to get documents"


def get_layers(**kwargs) -> str:
    """Get layers in the active document."""
    print("📋 Getting layers...")
    response = send_photoshop_command("getLayers", {})
    
    if response and response.get("status") == "SUCCESS":
        layers = response.get("layers", [])
        if layers:
            return "Layers:\n" + "\n".join([f"  - {l.get('name')} ({l.get('type')})" for l in layers])
        return "No layers found"
    return " Failed to get layers"


def create_text_layer(*, layer_name: str = None, text: str = None, font_size: int = 24,
                      font_name: str = "ArialMT", text_color: dict = None,
                      position: dict = None) -> str:
    """Create a text layer."""
    if not layer_name or not text:
        return " Missing required: layer_name, text"
    
    text_color = text_color or {"red": 255, "green": 255, "blue": 255}
    position = position or {"x": 100, "y": 100}
    print(f"📝 Creating text layer '{layer_name}'...")
    
    response = send_photoshop_command("createSingleLineTextLayer", {
        "layerName": layer_name, "contents": text, "fontSize": font_size,
        "fontName": font_name, "textColor": text_color, "position": position,
        "opacity": 100, "blendMode": "NORMAL"
    })
    
    if response and response.get("status") == "SUCCESS":
        return f"Created text layer '{layer_name}'"
    return f" Failed: {response.get('message', 'Unknown error') if response else 'No response'}"


def create_pixel_layer(*, layer_name: str = None, opacity: int = 100, 
                       blend_mode: str = "NORMAL") -> str:
    """Create a new pixel layer."""
    if not layer_name:
        return " Missing required: layer_name"
    
    print(f"🖼️ Creating pixel layer '{layer_name}'...")
    response = send_photoshop_command("createPixelLayer", {
        "layerName": layer_name, "opacity": opacity, 
        "blendMode": blend_mode, "fillNeutral": False
    })
    
    if response and response.get("status") == "SUCCESS":
        return f"Created pixel layer '{layer_name}'"
    return f" Failed: {response.get('message', 'Unknown error') if response else 'No response'}"


def delete_layer(*, layer_id: int = None) -> str:
    """Delete a layer by ID."""
    if layer_id is None:
        return " Missing required: layer_id"
    
    print(f"🗑️ Deleting layer {layer_id}...")
    response = send_photoshop_command("deleteLayer", {"layerId": int(layer_id)})
    
    if response and response.get("status") == "SUCCESS":
        return f"Deleted layer {layer_id}"
    return f" Failed: {response.get('message', 'Unknown error') if response else 'No response'}"


def fill_selection(*, layer_id: int = None, color: dict = None, opacity: int = 100) -> str:
    """Fill the current selection with a color."""
    if layer_id is None:
        return " Missing required: layer_id"
    
    color = color or {"red": 255, "green": 0, "blue": 0}
    print(f"🎨 Filling selection on layer {layer_id}...")
    
    response = send_photoshop_command("fillSelection", {
        "layerId": int(layer_id), "color": color, "opacity": opacity, "blendMode": "NORMAL"
    })
    
    if response and response.get("status") == "SUCCESS":
        return f"Filled selection on layer {layer_id}"
    return f" Failed: {response.get('message', 'Unknown error') if response else 'No response'}"


def select_rectangle(*, layer_id: int = None, top: int = 0, left: int = 0, 
                     bottom: int = 100, right: int = 100) -> str:
    """Create a rectangular selection."""
    if layer_id is None:
        return " Missing required: layer_id"
    
    print(f"⬜ Creating selection ({left},{top}) to ({right},{bottom})...")
    response = send_photoshop_command("selectRectangle", {
        "layerId": int(layer_id), "feather": 0, "antiAlias": True,
        "bounds": {"top": top, "left": left, "bottom": bottom, "right": right}
    })
    
    if response and response.get("status") == "SUCCESS":
        return f"Created rectangular selection"
    return f" Failed: {response.get('message', 'Unknown error') if response else 'No response'}"


def save_document(*, file_path: str = None, file_type: str = "PSD") -> str:
    """Save the document to a file."""
    if not file_path:
        return " Missing required: file_path"
    
    print(f"💾 Saving to {file_path}...")
    response = send_photoshop_command("saveDocumentAs", {
        "filePath": file_path, "fileType": file_type
    })
    
    if response and response.get("status") == "SUCCESS":
        return f"Saved to {file_path}"
    return f" Failed: {response.get('message', 'Unknown error') if response else 'No response'}"


def generate_image(*, layer_name: str = None, prompt: str = None, 
                   content_type: str = "none") -> str:
    """Generate an image using Adobe Firefly AI."""
    if not layer_name or not prompt:
        return " Missing required: layer_name, prompt"
    
    print(f"🤖 Generating image: '{prompt}'...")
    response = send_photoshop_command("generateImage", {
        "layerName": layer_name, "prompt": prompt, "contentType": content_type
    })
    
    if response and response.get("status") == "SUCCESS":
        return f"Generated image on layer '{layer_name}'"
    return f" Failed: {response.get('message', 'Unknown error') if response else 'No response'}"


def apply_gaussian_blur(*, layer_id: int = None, radius: float = 5.0) -> str:
    """Apply Gaussian blur to a layer."""
    if layer_id is None:
        return " Missing required: layer_id"
    
    print(f"🌫️ Applying blur (radius={radius}) to layer {layer_id}...")
    response = send_photoshop_command("applyGaussianBlur", {
        "layerId": int(layer_id), "radius": float(radius)
    })
    
    if response and response.get("status") == "SUCCESS":
        return f"Applied Gaussian blur to layer {layer_id}"
    return f" Failed: {response.get('message', 'Unknown error') if response else 'No response'}"


# ==========================================
# 4. AGENT TOOL DEFINITIONS
# ==========================================
tools = [
    ServerTool(name="create_document", description="Create a new Photoshop document", inputs=[
        StringProperty(title="document_name", description="Name of the document"),
        IntegerProperty(title="width", description="Width in pixels"),
        IntegerProperty(title="height", description="Height in pixels"),
        IntegerProperty(title="resolution", description="Resolution in PPI (default: 72)")
    ]),
    ServerTool(name="get_documents", description="List all open Photoshop documents", inputs=[]),
    ServerTool(name="get_layers", description="Get layers in the active document", inputs=[]),
    ServerTool(name="create_text_layer", description="Create a text layer", inputs=[
        StringProperty(title="layer_name", description="Name for the layer"),
        StringProperty(title="text", description="Text content"),
        IntegerProperty(title="font_size", description="Font size (default: 24)")
    ]),
    ServerTool(name="create_pixel_layer", description="Create a new pixel layer", inputs=[
        StringProperty(title="layer_name", description="Name for the layer"),
        IntegerProperty(title="opacity", description="Layer opacity 0-100 (default: 100)")
    ]),
    ServerTool(name="delete_layer", description="Delete a layer by its ID", inputs=[
        IntegerProperty(title="layer_id", description="ID of the layer to delete")
    ]),
    ServerTool(name="select_rectangle", description="Create a rectangular selection", inputs=[
        IntegerProperty(title="layer_id", description="Layer ID"),
        IntegerProperty(title="top", description="Top position"),
        IntegerProperty(title="left", description="Left position"),
        IntegerProperty(title="bottom", description="Bottom position"),
        IntegerProperty(title="right", description="Right position")
    ]),
    ServerTool(name="fill_selection", description="Fill selection with a color", inputs=[
        IntegerProperty(title="layer_id", description="Layer ID"),
        IntegerProperty(title="opacity", description="Fill opacity 0-100")
    ]),
    ServerTool(name="save_document", description="Save the document", inputs=[
        StringProperty(title="file_path", description="Full path to save (e.g., /Users/me/doc.psd)"),
        StringProperty(title="file_type", description="File type: PSD, PNG, or JPG")
    ]),
    ServerTool(name="generate_image", description="Generate image with Adobe Firefly AI", inputs=[
        StringProperty(title="layer_name", description="Name for the new layer"),
        StringProperty(title="prompt", description="Description of image to generate")
    ]),
    ServerTool(name="apply_gaussian_blur", description="Apply blur effect to a layer", inputs=[
        IntegerProperty(title="layer_id", description="Layer ID to blur"),
        IntegerProperty(title="radius", description="Blur radius (default: 5)")
    ])
]


# ==========================================
# 5. AGENT CONFIGURATION
# ==========================================
llm_config = OpenAiConfig(name="GPT-4.1", model_id="gpt-4.1")

agent_spec = Agent(
    name="Photoshop Controller",
    system_prompt="""You are a Photoshop automation assistant. You control Adobe Photoshop through tools.

Available tools:
- create_document: Create new documents (requires document_name, width, height)
- get_documents: List open documents
- get_layers: List layers in active document  
- create_text_layer: Add text (requires layer_name, text)
- create_pixel_layer: Add empty layer (requires layer_name)
- delete_layer: Remove a layer (requires layer_id)
- select_rectangle: Make rectangular selection (requires layer_id, coordinates)
- fill_selection: Fill selection with color (requires layer_id)
- save_document: Save file (requires file_path)
- generate_image: AI image generation (requires layer_name, prompt)
- apply_gaussian_blur: Blur effect (requires layer_id)

Always get layer IDs using get_layers before operating on specific layers.""",
    llm_config=llm_config,
    tools=tools
)


# ==========================================
# 6. MAIN
# ==========================================
def main():
    tool_registry = {
        "create_document": create_document,
        "get_documents": get_documents,
        "get_layers": get_layers,
        "create_text_layer": create_text_layer,
        "create_pixel_layer": create_pixel_layer,
        "delete_layer": delete_layer,
        "select_rectangle": select_rectangle,
        "fill_selection": fill_selection,
        "save_document": save_document,
        "generate_image": generate_image,
        "apply_gaussian_blur": apply_gaussian_blur,
    }
    
    print("=" * 60)
    print("🎨 Photoshop Agent")
    print("=" * 60)
    
    # Test connection
    print("\n🔍 Testing connection...")
    try:
        response = send_photoshop_command("getDocuments", {})
        print("Connected to Photoshop!\n")
    except Exception as e:
        print(f" Connection failed: {e}")
        print("Make sure proxy is running and Photoshop plugin is connected.\n")
        return
    
    # Load agent
    loader = AgentSpecLoader(tool_registry=tool_registry)
    runtime_agent = loader.load_component(agent_spec)
    conversation = runtime_agent.start_conversation()
    
    print("Ready! Type commands or 'quit' to exit.\n")
    
    while True:
        try:
            user_input = input("You: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
            
            conversation.append_user_message(user_input)
            print("\n... thinking ...\n")
            conversation.execute()
            print(f"Agent: {conversation.get_last_message().content}\n")
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f" Error: {e}\n")


if __name__ == "__main__":
    main()