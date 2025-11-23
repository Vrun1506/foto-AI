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


def apply_motion_blur(*, layer_id: int = None, angle: int = 0, distance: float = 30) -> str:
    """Apply motion blur to a layer."""
    if layer_id is None:
        return " Missing required: layer_id"
    
    print(f"🌀 Applying motion blur (angle={angle}, distance={distance}) to layer {layer_id}...")
    response = send_photoshop_command("applyMotionBlur", {
        "layerId": int(layer_id), "angle": int(angle), "distance": float(distance)
    })
    
    if response and response.get("status") == "SUCCESS":
        return f"Applied motion blur to layer {layer_id}"
    return f" Failed: {response.get('message', 'Unknown error') if response else 'No response'}"


def set_active_document(*, document_id: int = None) -> str:
    """Set the active document by ID."""
    if document_id is None:
        return " Missing required: document_id"
    
    print(f"📄 Setting active document {document_id}...")
    response = send_photoshop_command("setActiveDocument", {"documentId": int(document_id)})
    
    if response and response.get("status") == "SUCCESS":
        return f"Set active document {document_id}"
    return f" Failed: {response.get('message', 'Unknown error') if response else 'No response'}"


def create_gradient_layer_style(*, layer_id: int = None, angle: int = 0, type: str = "linear",
                                color_stops: list = None, opacity_stops: list = None) -> str:
    """Apply gradient to a layer."""
    if layer_id is None or not color_stops or not opacity_stops:
        return " Missing required: layer_id, color_stops, opacity_stops"
    
    print(f"🎨 Creating gradient layer style on layer {layer_id}...")
    response = send_photoshop_command("createGradientLayerStyle", {
        "layerId": int(layer_id), "angle": int(angle), "type": type,
        "colorStops": color_stops, "opacityStops": opacity_stops
    })
    
    if response and response.get("status") == "SUCCESS":
        return f"Created gradient on layer {layer_id}"
    return f" Failed: {response.get('message', 'Unknown error') if response else 'No response'}"


def duplicate_document(*, document_name: str = None) -> str:
    """Duplicate the current document."""
    if not document_name:
        return " Missing required: document_name"
    
    print(f"📋 Duplicating document as '{document_name}'...")
    response = send_photoshop_command("duplicateDocument", {"name": document_name})
    
    if response and response.get("status") == "SUCCESS":
        return f"Duplicated document as '{document_name}'"
    return f" Failed: {response.get('message', 'Unknown error') if response else 'No response'}"


def export_layers_as_png(*, layers_info: list = None) -> str:
    """Export layers as PNG files."""
    if not layers_info:
        return " Missing required: layers_info"
    
    print(f"📥 Exporting {len(layers_info)} layer(s) as PNG...")
    response = send_photoshop_command("exportLayersAsPng", {"layersInfo": layers_info})
    
    if response and response.get("status") == "SUCCESS":
        return f"Exported layers as PNG"
    return f" Failed: {response.get('message', 'Unknown error') if response else 'No response'}"


def group_layers(*, group_name: str = None, layer_ids: list = None) -> str:
    """Group multiple layers."""
    if not group_name or not layer_ids:
        return " Missing required: group_name, layer_ids"
    
    print(f"📂 Grouping {len(layer_ids)} layer(s) as '{group_name}'...")
    response = send_photoshop_command("groupLayers", {"groupName": group_name, "layerIds": layer_ids})
    
    if response and response.get("status") == "SUCCESS":
        return f"Grouped layers as '{group_name}'"
    return f" Failed: {response.get('message', 'Unknown error') if response else 'No response'}"


def place_image(*, layer_id: int = None, image_path: str = None) -> str:
    """Place an image on a layer."""
    if layer_id is None or not image_path:
        return " Missing required: layer_id, image_path"
    
    print(f"🖼️ Placing image '{image_path}' on layer {layer_id}...")
    response = send_photoshop_command("placeImage", {"layerId": int(layer_id), "imagePath": image_path})
    
    if response and response.get("status") == "SUCCESS":
        return f"Placed image on layer {layer_id}"
    return f" Failed: {response.get('message', 'Unknown error') if response else 'No response'}"


def harmonize_layer(*, layer_id: int = None, new_layer_name: str = None, rasterize_layer: bool = True) -> str:
    """Harmonize a layer with background."""
    if layer_id is None or not new_layer_name:
        return " Missing required: layer_id, new_layer_name"
    
    print(f"🎨 Harmonizing layer {layer_id}...")
    response = send_photoshop_command("harmonizeLayer", {
        "layerId": int(layer_id), "newLayerName": new_layer_name, "rasterizeLayer": rasterize_layer
    })
    
    if response and response.get("status") == "SUCCESS":
        return f"Harmonized layer {layer_id}"
    return f" Failed: {response.get('message', 'Unknown error') if response else 'No response'}"


def rename_layers(*, layer_data: list = None) -> str:
    """Rename one or more layers."""
    if not layer_data:
        return " Missing required: layer_data"
    
    print(f"✏️ Renaming {len(layer_data)} layer(s)...")
    response = send_photoshop_command("renameLayers", {"layerData": layer_data})
    
    if response and response.get("status") == "SUCCESS":
        return f"Renamed layers"
    return f" Failed: {response.get('message', 'Unknown error') if response else 'No response'}"


def scale_layer(*, layer_id: int = None, width: int = None, height: int = None,
                anchor_position: str = "MIDDLECENTER", interpolation_method: str = "AUTOMATIC") -> str:
    """Scale a layer."""
    if layer_id is None or width is None or height is None:
        return " Missing required: layer_id, width, height"
    
    print(f"📐 Scaling layer {layer_id} to {width}x{height}...")
    response = send_photoshop_command("scaleLayer", {
        "layerId": int(layer_id), "width": int(width), "height": int(height),
        "anchorPosition": anchor_position, "interpolationMethod": interpolation_method
    })
    
    if response and response.get("status") == "SUCCESS":
        return f"Scaled layer {layer_id}"
    return f" Failed: {response.get('message', 'Unknown error') if response else 'No response'}"


def rotate_layer(*, layer_id: int = None, angle: int = 0,
                 anchor_position: str = "MIDDLECENTER", interpolation_method: str = "AUTOMATIC") -> str:
    """Rotate a layer."""
    if layer_id is None:
        return " Missing required: layer_id"
    
    print(f"🔄 Rotating layer {layer_id} by {angle} degrees...")
    response = send_photoshop_command("rotateLayer", {
        "layerId": int(layer_id), "angle": int(angle),
        "anchorPosition": anchor_position, "interpolationMethod": interpolation_method
    })
    
    if response and response.get("status") == "SUCCESS":
        return f"Rotated layer {layer_id}"
    return f" Failed: {response.get('message', 'Unknown error') if response else 'No response'}"


def flip_layer(*, layer_id: int = None, axis: str = "HORIZONTAL") -> str:
    """Flip a layer."""
    if layer_id is None:
        return " Missing required: layer_id"
    
    print(f"🔀 Flipping layer {layer_id} on {axis} axis...")
    response = send_photoshop_command("flipLayer", {"layerId": int(layer_id), "axis": axis})
    
    if response and response.get("status") == "SUCCESS":
        return f"Flipped layer {layer_id}"
    return f" Failed: {response.get('message', 'Unknown error') if response else 'No response'}"


def set_layer_visibility(*, layer_id: int = None, visible: bool = True) -> str:
    """Set layer visibility."""
    if layer_id is None:
        return " Missing required: layer_id"
    
    print(f"👁️ Setting layer {layer_id} visibility to {visible}...")
    response = send_photoshop_command("setLayerVisibility", {"layerId": int(layer_id), "visible": visible})
    
    if response and response.get("status") == "SUCCESS":
        return f"Set layer {layer_id} visibility to {visible}"
    return f" Failed: {response.get('message', 'Unknown error') if response else 'No response'}"


def generative_fill(*, layer_name: str = None, prompt: str = None, layer_id: int = None, 
                    content_type: str = "none") -> str:
    """Generative fill with Firefly AI."""
    if not layer_name or not prompt or layer_id is None:
        return " Missing required: layer_name, prompt, layer_id"
    
    print(f"🤖 Generative fill: '{prompt}'...")
    response = send_photoshop_command("generativeFill", {
        "layerName": layer_name, "prompt": prompt, "layerId": int(layer_id), "contentType": content_type
    })
    
    if response and response.get("status") == "SUCCESS":
        return f"Generative fill applied on layer '{layer_name}'"
    return f" Failed: {response.get('message', 'Unknown error') if response else 'No response'}"


def move_layer(*, layer_id: int = None, position: str = None) -> str:
    """Move layer in layer stack."""
    if layer_id is None or not position:
        return " Missing required: layer_id, position"
    
    print(f"↔️ Moving layer {layer_id} to {position}...")
    response = send_photoshop_command("moveLayer", {"layerId": int(layer_id), "position": position})
    
    if response and response.get("status") == "SUCCESS":
        return f"Moved layer {layer_id}"
    return f" Failed: {response.get('message', 'Unknown error') if response else 'No response'}"


def get_document_info(**kwargs) -> str:
    """Get information about active document."""
    print("📋 Getting document info...")
    response = send_photoshop_command("getDocumentInfo", {})
    
    if response and response.get("status") == "SUCCESS":
        doc = response.get("document", {})
        return f"Document: {doc.get('name')} ({doc.get('width')}x{doc.get('height')})"
    return " Failed to get document info"


def crop_document(**kwargs) -> str:
    """Crop document to selection."""
    print("✂️ Cropping document...")
    response = send_photoshop_command("cropDocument", {})
    
    if response and response.get("status") == "SUCCESS":
        return f"Cropped document"
    return f" Failed: {response.get('message', 'Unknown error') if response else 'No response'}"


def paste_from_clipboard(*, layer_id: int = None, paste_in_place: bool = True) -> str:
    """Paste from clipboard to layer."""
    if layer_id is None:
        return " Missing required: layer_id"
    
    print(f"📋 Pasting from clipboard to layer {layer_id}...")
    response = send_photoshop_command("pasteFromClipboard", {
        "layerId": int(layer_id), "pasteInPlace": paste_in_place
    })
    
    if response and response.get("status") == "SUCCESS":
        return f"Pasted from clipboard to layer {layer_id}"
    return f" Failed: {response.get('message', 'Unknown error') if response else 'No response'}"


def rasterize_layer(*, layer_id: int = None) -> str:
    """Rasterize a layer."""
    if layer_id is None:
        return " Missing required: layer_id"
    
    print(f"📐 Rasterizing layer {layer_id}...")
    response = send_photoshop_command("rasterizeLayer", {"layerId": int(layer_id)})
    
    if response and response.get("status") == "SUCCESS":
        return f"Rasterized layer {layer_id}"
    return f" Failed: {response.get('message', 'Unknown error') if response else 'No response'}"


def open_photoshop_file(*, file_path: str = None) -> str:
    """Open a Photoshop file."""
    if not file_path:
        return " Missing required: file_path"
    
    print(f"📂 Opening file '{file_path}'...")
    response = send_photoshop_command("openFile", {"filePath": file_path})
    
    if response and response.get("status") == "SUCCESS":
        return f"Opened file '{file_path}'"
    return f" Failed: {response.get('message', 'Unknown error') if response else 'No response'}"


def cut_selection_to_clipboard(*, layer_id: int = None) -> str:
    """Cut selection to clipboard."""
    if layer_id is None:
        return " Missing required: layer_id"
    
    print(f"✂️ Cutting selection to clipboard from layer {layer_id}...")
    response = send_photoshop_command("cutSelectionToClipboard", {"layerId": int(layer_id)})
    
    if response and response.get("status") == "SUCCESS":
        return f"Cut selection to clipboard"
    return f" Failed: {response.get('message', 'Unknown error') if response else 'No response'}"


def copy_merged_selection_to_clipboard(**kwargs) -> str:
    """Copy merged selection to clipboard."""
    print("📋 Copying merged selection to clipboard...")
    response = send_photoshop_command("copyMergedSelectionToClipboard", {})
    
    if response and response.get("status") == "SUCCESS":
        return f"Copied merged selection to clipboard"
    return f" Failed: {response.get('message', 'Unknown error') if response else 'No response'}"


def copy_selection_to_clipboard(*, layer_id: int = None) -> str:
    """Copy selection to clipboard."""
    if layer_id is None:
        return " Missing required: layer_id"
    
    print(f"📋 Copying selection to clipboard from layer {layer_id}...")
    response = send_photoshop_command("copySelectionToClipboard", {"layerId": int(layer_id)})
    
    if response and response.get("status") == "SUCCESS":
        return f"Copied selection to clipboard"
    return f" Failed: {response.get('message', 'Unknown error') if response else 'No response'}"


def select_subject(*, layer_id: int = None) -> str:
    """Auto-select subject in layer."""
    if layer_id is None:
        return " Missing required: layer_id"
    
    print(f"✨ Selecting subject in layer {layer_id}...")
    response = send_photoshop_command("selectSubject", {"layerId": int(layer_id)})
    
    if response and response.get("status") == "SUCCESS":
        return f"Selected subject in layer {layer_id}"
    return f" Failed: {response.get('message', 'Unknown error') if response else 'No response'}"


def select_sky(*, layer_id: int = None) -> str:
    """Auto-select sky in layer."""
    if layer_id is None:
        return " Missing required: layer_id"
    
    print(f"☁️ Selecting sky in layer {layer_id}...")
    response = send_photoshop_command("selectSky", {"layerId": int(layer_id)})
    
    if response and response.get("status") == "SUCCESS":
        return f"Selected sky in layer {layer_id}"
    return f" Failed: {response.get('message', 'Unknown error') if response else 'No response'}"


def get_layer_bounds(*, layer_id: int = None) -> str:
    """Get layer bounds."""
    if layer_id is None:
        return " Missing required: layer_id"
    
    print(f"📏 Getting bounds for layer {layer_id}...")
    response = send_photoshop_command("getLayerBounds", {"layerId": int(layer_id)})
    
    if response and response.get("status") == "SUCCESS":
        bounds = response.get("bounds", {})
        return f"Layer bounds: top={bounds.get('top')}, left={bounds.get('left')}, bottom={bounds.get('bottom')}, right={bounds.get('right')}"
    return f" Failed: {response.get('message', 'Unknown error') if response else 'No response'}"


def remove_background(*, layer_id: int = None) -> str:
    """Remove background from layer."""
    if layer_id is None:
        return " Missing required: layer_id"
    
    print(f"🎨 Removing background from layer {layer_id}...")
    response = send_photoshop_command("removeBackground", {"layerId": int(layer_id)})
    
    if response and response.get("status") == "SUCCESS":
        return f"Removed background from layer {layer_id}"
    return f" Failed: {response.get('message', 'Unknown error') if response else 'No response'}"


def create_multi_line_text_layer(*, layer_name: str = None, text: str = None, font_size: int = 24,
                                 postscript_font_name: str = "ArialMT", opacity: int = 100,
                                 blend_mode: str = "NORMAL", text_color: dict = None,
                                 position: dict = None, bounds: dict = None,
                                 justification: str = "LEFT") -> str:
    """Create a multi-line text layer."""
    if not layer_name or not text:
        return " Missing required: layer_name, text"
    
    text_color = text_color or {"red": 255, "green": 255, "blue": 255}
    position = position or {"x": 100, "y": 100}
    bounds = bounds or {"top": 0, "left": 0, "bottom": 250, "right": 300}
    
    print(f"📝 Creating multi-line text layer '{layer_name}'...")
    response = send_photoshop_command("createMultiLineTextLayer", {
        "layerName": layer_name, "contents": text, "fontSize": font_size,
        "fontName": postscript_font_name, "opacity": opacity, "position": position,
        "textColor": text_color, "blendMode": blend_mode, "bounds": bounds,
        "justification": justification
    })
    
    if response and response.get("status") == "SUCCESS":
        return f"Created multi-line text layer '{layer_name}'"
    return f" Failed: {response.get('message', 'Unknown error') if response else 'No response'}"


def edit_text_layer(*, layer_id: int = None, text: str = None, font_size: int = None,
                    postscript_font_name: str = None, text_color: dict = None) -> str:
    """Edit text layer content."""
    if layer_id is None:
        return " Missing required: layer_id"
    
    print(f"✏️ Editing text layer {layer_id}...")
    response = send_photoshop_command("editTextLayer", {
        "layerId": int(layer_id), "contents": text, "fontSize": font_size,
        "fontName": postscript_font_name, "textColor": text_color
    })
    
    if response and response.get("status") == "SUCCESS":
        return f"Edited text layer {layer_id}"
    return f" Failed: {response.get('message', 'Unknown error') if response else 'No response'}"


def translate_layer(*, layer_id: int = None, x_offset: int = 0, y_offset: int = 0) -> str:
    """Translate/move layer by offset."""
    if layer_id is None:
        return " Missing required: layer_id"
    
    print(f"↔️ Translating layer {layer_id} by ({x_offset}, {y_offset})...")
    response = send_photoshop_command("translateLayer", {
        "layerId": int(layer_id), "xOffset": int(x_offset), "yOffset": int(y_offset)
    })
    
    if response and response.get("status") == "SUCCESS":
        return f"Translated layer {layer_id}"
    return f" Failed: {response.get('message', 'Unknown error') if response else 'No response'}"


def remove_layer_mask(*, layer_id: int = None) -> str:
    """Remove layer mask."""
    if layer_id is None:
        return " Missing required: layer_id"
    
    print(f"🎭 Removing layer mask from {layer_id}...")
    response = send_photoshop_command("removeLayerMask", {"layerId": int(layer_id)})
    
    if response and response.get("status") == "SUCCESS":
        return f"Removed layer mask"
    return f" Failed: {response.get('message', 'Unknown error') if response else 'No response'}"


def add_layer_mask_from_selection(*, layer_id: int = None) -> str:
    """Add layer mask from selection."""
    if layer_id is None:
        return " Missing required: layer_id"
    
    print(f"🎭 Adding layer mask from selection to layer {layer_id}...")
    response = send_photoshop_command("addLayerMask", {"layerId": int(layer_id)})
    
    if response and response.get("status") == "SUCCESS":
        return f"Added layer mask"
    return f" Failed: {response.get('message', 'Unknown error') if response else 'No response'}"


def set_layer_properties(*, layer_id: int = None, blend_mode: str = "NORMAL",
                         layer_opacity: int = 100, fill_opacity: int = 100,
                         is_clipping_mask: bool = False) -> str:
    """Set layer properties."""
    if layer_id is None:
        return " Missing required: layer_id"
    
    print(f"⚙️ Setting layer {layer_id} properties...")
    response = send_photoshop_command("setLayerProperties", {
        "layerId": int(layer_id), "blendMode": blend_mode, "layerOpacity": layer_opacity,
        "fillOpacity": fill_opacity, "isClippingMask": is_clipping_mask
    })
    
    if response and response.get("status") == "SUCCESS":
        return f"Set layer properties"
    return f" Failed: {response.get('message', 'Unknown error') if response else 'No response'}"


def delete_selection(*, layer_id: int = None) -> str:
    """Delete selection content."""
    if layer_id is None:
        return " Missing required: layer_id"
    
    print(f"🗑️ Deleting selection from layer {layer_id}...")
    response = send_photoshop_command("deleteSelection", {"layerId": int(layer_id)})
    
    if response and response.get("status") == "SUCCESS":
        return f"Deleted selection"
    return f" Failed: {response.get('message', 'Unknown error') if response else 'No response'}"


def invert_selection(**kwargs) -> str:
    """Invert current selection."""
    print("🔄 Inverting selection...")
    response = send_photoshop_command("invertSelection", {})
    
    if response and response.get("status") == "SUCCESS":
        return f"Inverted selection"
    return f" Failed: {response.get('message', 'Unknown error') if response else 'No response'}"


def clear_selection(**kwargs) -> str:
    """Clear/deselect current selection."""
    print("🔄 Clearing selection...")
    response = send_photoshop_command("selectRectangle", {
        "feather": 0, "antiAlias": True, "bounds": {"top": 0, "left": 0, "bottom": 0, "right": 0}
    })
    
    if response and response.get("status") == "SUCCESS":
        return f"Cleared selection"
    return f" Failed: {response.get('message', 'Unknown error') if response else 'No response'}"


def select_polygon(*, layer_id: int = None, feather: int = 0, anti_alias: bool = True,
                   points: list = None) -> str:
    """Create polygon selection."""
    if layer_id is None or not points:
        return " Missing required: layer_id, points"
    
    print(f"⬟ Creating polygon selection...")
    response = send_photoshop_command("selectPolygon", {
        "layerId": int(layer_id), "feather": feather, "antiAlias": anti_alias, "points": points
    })
    
    if response and response.get("status") == "SUCCESS":
        return f"Created polygon selection"
    return f" Failed: {response.get('message', 'Unknown error') if response else 'No response'}"


def select_ellipse(*, layer_id: int = None, feather: int = 0, anti_alias: bool = True,
                   top: int = 0, left: int = 0, bottom: int = 100, right: int = 100) -> str:
    """Create elliptical selection."""
    if layer_id is None:
        return " Missing required: layer_id"
    
    print(f"⭕ Creating elliptical selection...")
    response = send_photoshop_command("selectEllipse", {
        "layerId": int(layer_id), "feather": feather, "antiAlias": anti_alias,
        "bounds": {"top": top, "left": left, "bottom": bottom, "right": right}
    })
    
    if response and response.get("status") == "SUCCESS":
        return f"Created elliptical selection"
    return f" Failed: {response.get('message', 'Unknown error') if response else 'No response'}"


def align_content(*, layer_id: int = None, alignment_mode: str = None) -> str:
    """Align content to selection."""
    if layer_id is None or not alignment_mode:
        return " Missing required: layer_id, alignment_mode"
    
    print(f"⬚ Aligning content with mode {alignment_mode}...")
    response = send_photoshop_command("alignContent", {
        "layerId": int(layer_id), "alignmentMode": alignment_mode
    })
    
    if response and response.get("status") == "SUCCESS":
        return f"Aligned content"
    return f" Failed: {response.get('message', 'Unknown error') if response else 'No response'}"


def add_drop_shadow_layer_style(*, layer_id: int = None, blend_mode: str = "MULTIPLY",
                                color: dict = None, opacity: int = 35, angle: int = 160,
                                distance: int = 3, spread: int = 0, size: int = 7) -> str:
    """Add drop shadow layer style."""
    if layer_id is None:
        return " Missing required: layer_id"
    
    color = color or {"red": 0, "green": 0, "blue": 0}
    print(f"💧 Adding drop shadow to layer {layer_id}...")
    response = send_photoshop_command("addDropShadowLayerStyle", {
        "layerId": int(layer_id), "blendMode": blend_mode, "color": color,
        "opacity": opacity, "angle": angle, "distance": distance, "spread": spread, "size": size
    })
    
    if response and response.get("status") == "SUCCESS":
        return f"Added drop shadow"
    return f" Failed: {response.get('message', 'Unknown error') if response else 'No response'}"


def duplicate_layer(*, layer_to_duplicate_id: int = None, duplicate_layer_name: str = None) -> str:
    """Duplicate a layer."""
    if layer_to_duplicate_id is None or not duplicate_layer_name:
        return " Missing required: layer_to_duplicate_id, duplicate_layer_name"
    
    print(f"📋 Duplicating layer {layer_to_duplicate_id}...")
    response = send_photoshop_command("duplicateLayer", {
        "sourceLayerId": int(layer_to_duplicate_id), "duplicateLayerName": duplicate_layer_name
    })
    
    if response and response.get("status") == "SUCCESS":
        return f"Duplicated layer as '{duplicate_layer_name}'"
    return f" Failed: {response.get('message', 'Unknown error') if response else 'No response'}"


def flatten_all_layers(*, layer_name: str = None) -> str:
    """Flatten all layers."""
    if not layer_name:
        return " Missing required: layer_name"
    
    print(f"📐 Flattening all layers into '{layer_name}'...")
    response = send_photoshop_command("flattenAllLayers", {"layerName": layer_name})
    
    if response and response.get("status") == "SUCCESS":
        return f"Flattened layers"
    return f" Failed: {response.get('message', 'Unknown error') if response else 'No response'}"


def add_color_balance_adjustment_layer(*, layer_id: int = None, highlights: list = None,
                                       midtones: list = None, shadows: list = None) -> str:
    """Add color balance adjustment layer."""
    if layer_id is None:
        return " Missing required: layer_id"
    
    highlights = highlights or [0, 0, 0]
    midtones = midtones or [0, 0, 0]
    shadows = shadows or [0, 0, 0]
    
    print(f"🎨 Adding color balance adjustment to layer {layer_id}...")
    response = send_photoshop_command("addColorBalanceAdjustmentLayer", {
        "layerId": int(layer_id), "highlights": highlights, "midtones": midtones, "shadows": shadows
    })
    
    if response and response.get("status") == "SUCCESS":
        return f"Added color balance adjustment"
    return f" Failed: {response.get('message', 'Unknown error') if response else 'No response'}"


def add_brightness_contrast_adjustment_layer(*, layer_id: int = None, brightness: int = 0,
                                             contrast: int = 0) -> str:
    """Add brightness/contrast adjustment layer."""
    if layer_id is None:
        return " Missing required: layer_id"
    
    print(f"💡 Adding brightness/contrast adjustment to layer {layer_id}...")
    response = send_photoshop_command("addBrightnessContrastAdjustmentLayer", {
        "layerId": int(layer_id), "brightness": brightness, "contrast": contrast
    })
    
    if response and response.get("status") == "SUCCESS":
        return f"Added brightness/contrast adjustment"
    return f" Failed: {response.get('message', 'Unknown error') if response else 'No response'}"


def add_stroke_layer_style(*, layer_id: int = None, size: int = 2, color: dict = None,
                           opacity: int = 100, position: str = "CENTER", 
                           blend_mode: str = "NORMAL") -> str:
    """Add stroke layer style."""
    if layer_id is None:
        return " Missing required: layer_id"
    
    color = color or {"red": 0, "green": 0, "blue": 0}
    print(f"🎨 Adding stroke to layer {layer_id}...")
    response = send_photoshop_command("addStrokeLayerStyle", {
        "layerId": int(layer_id), "size": size, "color": color, "opacity": opacity,
        "position": position, "blendMode": blend_mode
    })
    
    if response and response.get("status") == "SUCCESS":
        return f"Added stroke"
    return f" Failed: {response.get('message', 'Unknown error') if response else 'No response'}"


def add_vibrance_adjustment_layer(*, layer_id: int = None, vibrance: int = 0,
                                  saturation: int = 0) -> str:
    """Add vibrance adjustment layer."""
    if layer_id is None:
        return " Missing required: layer_id"
    
    print(f"🌈 Adding vibrance adjustment to layer {layer_id}...")
    response = send_photoshop_command("addAdjustmentLayerVibrance", {
        "layerId": int(layer_id), "saturation": saturation, "vibrance": vibrance
    })
    
    if response and response.get("status") == "SUCCESS":
        return f"Added vibrance adjustment"
    return f" Failed: {response.get('message', 'Unknown error') if response else 'No response'}"


def add_black_and_white_adjustment_layer(*, layer_id: int = None, colors: dict = None,
                                         tint: bool = False, tint_color: dict = None) -> str:
    """Add black & white adjustment layer."""
    if layer_id is None:
        return " Missing required: layer_id"
    
    colors = colors or {"blue": 20, "cyan": 60, "green": 40, "magenta": 80, "red": 40, "yellow": 60}
    tint_color = tint_color or {"red": 225, "green": 211, "blue": 179}
    
    print(f"⬜ Adding black & white adjustment to layer {layer_id}...")
    response = send_photoshop_command("addAdjustmentLayerBlackAndWhite", {
        "layerId": int(layer_id), "colors": colors, "tint": tint, "tintColor": tint_color
    })
    
    if response and response.get("status") == "SUCCESS":
        return f"Added black & white adjustment"
    return f" Failed: {response.get('message', 'Unknown error') if response else 'No response'}"


def get_document_image(**kwargs) -> str:
    """Get image of current document."""
    print("📸 Getting document image...")
    response = send_photoshop_command("getDocumentImage", {})
    
    if response and response.get("status") == "SUCCESS":
        return f"Document image retrieved"
    return f" Failed: {response.get('message', 'Unknown error') if response else 'No response'}"


def get_layer_image(*, layer_id: int = None) -> str:
    """Get image of a specific layer."""
    if layer_id is None:
        return " Missing required: layer_id"
    
    print(f"📸 Getting image of layer {layer_id}...")
    response = send_photoshop_command("getLayerImage", {"layerId": int(layer_id)})
    
    if response and response.get("status") == "SUCCESS":
        return f"Layer image retrieved"
    return f" Failed: {response.get('message', 'Unknown error') if response else 'No response'}"


# ==========================================
# 4. AGENT TOOL DEFINITIONS
# ==========================================
tools = [
    # Document management
    ServerTool(name="create_document", description="Create a new Photoshop document", inputs=[
        StringProperty(title="document_name", description="Name of the document"),
        IntegerProperty(title="width", description="Width in pixels"),
        IntegerProperty(title="height", description="Height in pixels"),
        IntegerProperty(title="resolution", description="Resolution in PPI (default: 72)")
    ]),
    ServerTool(name="get_documents", description="List all open Photoshop documents", inputs=[]),
    ServerTool(name="get_document_info", description="Get info about the active document", inputs=[]),
    ServerTool(name="set_active_document", description="Set active document by ID", inputs=[
        IntegerProperty(title="document_id", description="Document ID to activate")
    ]),
    ServerTool(name="duplicate_document", description="Duplicate current document", inputs=[
        StringProperty(title="document_name", description="Name for duplicated document")
    ]),
    ServerTool(name="save_document", description="Save the document", inputs=[
        StringProperty(title="file_path", description="Full path to save"),
        StringProperty(title="file_type", description="File type: PSD, PNG, or JPG")
    ]),
    ServerTool(name="open_photoshop_file", description="Open a Photoshop file", inputs=[
        StringProperty(title="file_path", description="Path to file to open")
    ]),
    ServerTool(name="crop_document", description="Crop document to selection", inputs=[]),
    
    # Layer management
    ServerTool(name="get_layers", description="Get layers in the active document", inputs=[]),
    ServerTool(name="create_text_layer", description="Create single-line text layer", inputs=[
        StringProperty(title="layer_name", description="Name for the layer"),
        StringProperty(title="text", description="Text content"),
        IntegerProperty(title="font_size", description="Font size (default: 24)")
    ]),
    ServerTool(name="create_multi_line_text_layer", description="Create multi-line text layer", inputs=[
        StringProperty(title="layer_name", description="Layer name"),
        StringProperty(title="text", description="Text content"),
        IntegerProperty(title="font_size", description="Font size")
    ]),
    ServerTool(name="edit_text_layer", description="Edit text layer content", inputs=[
        IntegerProperty(title="layer_id", description="Layer ID"),
        StringProperty(title="text", description="New text")
    ]),
    ServerTool(name="create_pixel_layer", description="Create a new pixel layer", inputs=[
        StringProperty(title="layer_name", description="Name for the layer"),
        IntegerProperty(title="opacity", description="Layer opacity 0-100 (default: 100)")
    ]),
    ServerTool(name="delete_layer", description="Delete a layer by ID", inputs=[
        IntegerProperty(title="layer_id", description="ID of the layer to delete")
    ]),
    ServerTool(name="duplicate_layer", description="Duplicate a layer", inputs=[
        IntegerProperty(title="layer_to_duplicate_id", description="Layer ID to duplicate"),
        StringProperty(title="duplicate_layer_name", description="Name for duplicated layer")
    ]),
    ServerTool(name="rename_layers", description="Rename layers", inputs=[
        StringProperty(title="layer_data", description="Layer data for renaming")
    ]),
    ServerTool(name="group_layers", description="Group multiple layers", inputs=[
        StringProperty(title="group_name", description="Name for group"),
        StringProperty(title="layer_ids", description="Layer IDs to group")
    ]),
    ServerTool(name="flatten_all_layers", description="Flatten all layers", inputs=[
        StringProperty(title="layer_name", description="Name for flattened layer")
    ]),
    ServerTool(name="set_layer_visibility", description="Set layer visibility", inputs=[
        IntegerProperty(title="layer_id", description="Layer ID"),
        StringProperty(title="visible", description="true/false for visibility")
    ]),
    ServerTool(name="set_layer_properties", description="Set layer blend mode and opacity", inputs=[
        IntegerProperty(title="layer_id", description="Layer ID"),
        StringProperty(title="blend_mode", description="Blend mode (e.g., NORMAL, MULTIPLY)")
    ]),
    ServerTool(name="get_layer_bounds", description="Get layer bounds", inputs=[
        IntegerProperty(title="layer_id", description="Layer ID")
    ]),
    
    # Selection tools
    ServerTool(name="select_rectangle", description="Create rectangular selection", inputs=[
        IntegerProperty(title="layer_id", description="Layer ID"),
        IntegerProperty(title="top", description="Top position"),
        IntegerProperty(title="left", description="Left position"),
        IntegerProperty(title="bottom", description="Bottom position"),
        IntegerProperty(title="right", description="Right position")
    ]),
    ServerTool(name="select_ellipse", description="Create elliptical selection", inputs=[
        IntegerProperty(title="layer_id", description="Layer ID")
    ]),
    ServerTool(name="select_polygon", description="Create polygon selection", inputs=[
        IntegerProperty(title="layer_id", description="Layer ID")
    ]),
    ServerTool(name="select_subject", description="Auto-select subject in layer", inputs=[
        IntegerProperty(title="layer_id", description="Layer ID")
    ]),
    ServerTool(name="select_sky", description="Auto-select sky in layer", inputs=[
        IntegerProperty(title="layer_id", description="Layer ID")
    ]),
    ServerTool(name="invert_selection", description="Invert current selection", inputs=[]),
    ServerTool(name="clear_selection", description="Clear/deselect selection", inputs=[]),
    ServerTool(name="copy_selection_to_clipboard", description="Copy selection to clipboard", inputs=[
        IntegerProperty(title="layer_id", description="Layer ID")
    ]),
    ServerTool(name="cut_selection_to_clipboard", description="Cut selection to clipboard", inputs=[
        IntegerProperty(title="layer_id", description="Layer ID")
    ]),
    ServerTool(name="copy_merged_selection_to_clipboard", description="Copy merged selection", inputs=[]),
    ServerTool(name="paste_from_clipboard", description="Paste from clipboard", inputs=[
        IntegerProperty(title="layer_id", description="Layer ID")
    ]),
    ServerTool(name="delete_selection", description="Delete selection content", inputs=[
        IntegerProperty(title="layer_id", description="Layer ID")
    ]),
    ServerTool(name="fill_selection", description="Fill selection with color", inputs=[
        IntegerProperty(title="layer_id", description="Layer ID"),
        IntegerProperty(title="opacity", description="Fill opacity 0-100")
    ]),
    ServerTool(name="align_content", description="Align content to selection", inputs=[
        IntegerProperty(title="layer_id", description="Layer ID"),
        StringProperty(title="alignment_mode", description="Alignment mode")
    ]),
    
    # Image/layer manipulation
    ServerTool(name="place_image", description="Place image on layer", inputs=[
        IntegerProperty(title="layer_id", description="Layer ID"),
        StringProperty(title="image_path", description="Path to image file")
    ]),
    ServerTool(name="scale_layer", description="Scale a layer", inputs=[
        IntegerProperty(title="layer_id", description="Layer ID"),
        IntegerProperty(title="width", description="Width"),
        IntegerProperty(title="height", description="Height")
    ]),
    ServerTool(name="rotate_layer", description="Rotate a layer", inputs=[
        IntegerProperty(title="layer_id", description="Layer ID"),
        IntegerProperty(title="angle", description="Angle in degrees")
    ]),
    ServerTool(name="flip_layer", description="Flip a layer", inputs=[
        IntegerProperty(title="layer_id", description="Layer ID"),
        StringProperty(title="axis", description="HORIZONTAL or VERTICAL")
    ]),
    ServerTool(name="translate_layer", description="Move layer by offset", inputs=[
        IntegerProperty(title="layer_id", description="Layer ID"),
        IntegerProperty(title="x_offset", description="X offset"),
        IntegerProperty(title="y_offset", description="Y offset")
    ]),
    ServerTool(name="move_layer", description="Move layer in stack", inputs=[
        IntegerProperty(title="layer_id", description="Layer ID"),
        StringProperty(title="position", description="Position to move to")
    ]),
    ServerTool(name="rasterize_layer", description="Rasterize/flatten layer", inputs=[
        IntegerProperty(title="layer_id", description="Layer ID")
    ]),
    ServerTool(name="remove_background", description="Remove background", inputs=[
        IntegerProperty(title="layer_id", description="Layer ID")
    ]),
    ServerTool(name="harmonize_layer", description="Harmonize layer", inputs=[
        IntegerProperty(title="layer_id", description="Layer ID"),
        StringProperty(title="new_layer_name", description="Name for result")
    ]),
    
    # Image generation and effects
    ServerTool(name="generate_image", description="Generate image with Firefly AI", inputs=[
        StringProperty(title="layer_name", description="Name for new layer"),
        StringProperty(title="prompt", description="Description to generate")
    ]),
    ServerTool(name="generative_fill", description="Generative fill with Firefly", inputs=[
        StringProperty(title="layer_name", description="Layer name"),
        StringProperty(title="prompt", description="Fill prompt"),
        IntegerProperty(title="layer_id", description="Layer ID")
    ]),
    
    # Filters and effects
    ServerTool(name="apply_gaussian_blur", description="Apply Gaussian blur", inputs=[
        IntegerProperty(title="layer_id", description="Layer ID"),
        IntegerProperty(title="radius", description="Blur radius")
    ]),
    ServerTool(name="apply_motion_blur", description="Apply motion blur", inputs=[
        IntegerProperty(title="layer_id", description="Layer ID"),
        IntegerProperty(title="angle", description="Angle"),
        IntegerProperty(title="distance", description="Distance")
    ]),
    
    # Layer styles and adjustments
    ServerTool(name="add_drop_shadow_layer_style", description="Add drop shadow", inputs=[
        IntegerProperty(title="layer_id", description="Layer ID")
    ]),
    ServerTool(name="add_stroke_layer_style", description="Add stroke effect", inputs=[
        IntegerProperty(title="layer_id", description="Layer ID"),
        IntegerProperty(title="size", description="Stroke size")
    ]),
    ServerTool(name="add_color_balance_adjustment_layer", description="Color balance adjustment", inputs=[
        IntegerProperty(title="layer_id", description="Layer ID")
    ]),
    ServerTool(name="add_brightness_contrast_adjustment_layer", description="Brightness/contrast adjustment", inputs=[
        IntegerProperty(title="layer_id", description="Layer ID"),
        IntegerProperty(title="brightness", description="Brightness value"),
        IntegerProperty(title="contrast", description="Contrast value")
    ]),
    ServerTool(name="add_vibrance_adjustment_layer", description="Vibrance and saturation adjustment", inputs=[
        IntegerProperty(title="layer_id", description="Layer ID"),
        IntegerProperty(title="vibrance", description="Vibrance value (-100 to 100)"),
        IntegerProperty(title="saturation", description="Saturation value (-100 to 100)")
    ]),
    ServerTool(name="add_black_and_white_adjustment_layer", description="Black and white adjustment", inputs=[
        IntegerProperty(title="layer_id", description="Layer ID")
    ]),
    ServerTool(name="create_gradient_layer_style", description="Create gradient", inputs=[
        IntegerProperty(title="layer_id", description="Layer ID"),
        IntegerProperty(title="angle", description="Gradient angle")
    ]),
    
    # Layer masks
    ServerTool(name="add_layer_mask_from_selection", description="Add layer mask", inputs=[
        IntegerProperty(title="layer_id", description="Layer ID")
    ]),
    ServerTool(name="remove_layer_mask", description="Remove layer mask", inputs=[
        IntegerProperty(title="layer_id", description="Layer ID")
    ]),
    
    # Export and output
    ServerTool(name="export_layers_as_png", description="Export layers as PNG", inputs=[
        StringProperty(title="layers_info", description="Layer info to export")
    ]),
    ServerTool(name="get_document_image", description="Get document image", inputs=[]),
    ServerTool(name="get_layer_image", description="Get layer image", inputs=[
        IntegerProperty(title="layer_id", description="Layer ID")
    ])
]


# ==========================================
# 5. AGENT CONFIGURATION
# ==========================================
llm_config = OpenAiConfig(name="GPT-5.1", model_id="gpt-5.1")

agent_spec = Agent(
    name="Photoshop Controller",
    system_prompt="""You are a Photoshop automation assistant. You control Adobe Photoshop through tools.

CRITICAL TOOL SELECTION RULES FOR COLOR ADJUSTMENTS:

**SATURATION ADJUSTMENTS:**
- "increase/decrease saturation" = use add_vibrance_adjustment_layer with saturation parameter
  * Example: user says "increase saturation by 50%" → call add_vibrance_adjustment_layer(layer_id=X, saturation=50, vibrance=0)
  * Example: user says "decrease saturation by 30%" → call add_vibrance_adjustment_layer(layer_id=X, saturation=-30, vibrance=0)

**VIBRANCE ADJUSTMENTS:**
- "increase/decrease vibrance" = use add_vibrance_adjustment_layer with vibrance parameter
  * Example: user says "increase vibrance" → call add_vibrance_adjustment_layer(layer_id=X, vibrance=50, saturation=0)

**OTHER COLOR ADJUSTMENTS:**
- "adjust color balance" / "shift colors in shadows/midtones/highlights" = add_color_balance_adjustment_layer
- "brighten/darken" = add_brightness_contrast_adjustment_layer
- "black and white conversion" = add_black_and_white_adjustment_layer
- "gradient overlay" = create_gradient_layer_style
- "border/outline effect" = add_stroke_layer_style
- "shadow effect" = add_drop_shadow_layer_style

TEXT OPERATIONS:
- Single line text = create_text_layer
- Multiple lines/paragraphs = create_multi_line_text_layer
- Editing existing text = edit_text_layer

SELECTION OPERATIONS:
- "select subject" = select_subject (AI-powered subject selection)
- "select sky" = select_sky (AI-powered sky selection)
- "select area" = select_rectangle, select_ellipse, or select_polygon based on shape

LAYER OPERATIONS:
- Always get layer IDs using get_layers BEFORE operating on specific layers
- Use duplicate_layer to copy layers
- Use delete_selection to remove pixels
- Use remove_background for background removal
- Use generative_fill for AI-powered content fill within selection
- Use generate_image for AI-powered image generation on new layer

BEST PRACTICES:
1. Always list layers first to understand document structure
2. Provide meaningful layer names when creating layers
3. Clear selections after operations using clear_selection
4. Save document after major edits
5. For saturation requests: ALWAYS use add_vibrance_adjustment_layer with saturation parameter, NOT color_balance

Available tools: create_document, get_documents, get_document_info, set_active_document, duplicate_document, save_document, open_photoshop_file, crop_document, get_layers, create_text_layer, create_multi_line_text_layer, edit_text_layer, create_pixel_layer, delete_layer, duplicate_layer, rename_layers, group_layers, flatten_all_layers, set_layer_visibility, set_layer_properties, get_layer_bounds, select_rectangle, select_ellipse, select_polygon, select_subject, select_sky, invert_selection, clear_selection, copy_selection_to_clipboard, cut_selection_to_clipboard, copy_merged_selection_to_clipboard, paste_from_clipboard, delete_selection, fill_selection, align_content, place_image, scale_layer, rotate_layer, flip_layer, translate_layer, move_layer, rasterize_layer, remove_background, harmonize_layer, generate_image, generative_fill, apply_gaussian_blur, apply_motion_blur, add_drop_shadow_layer_style, add_stroke_layer_style, add_color_balance_adjustment_layer, add_brightness_contrast_adjustment_layer, add_vibrance_adjustment_layer, add_black_and_white_adjustment_layer, create_gradient_layer_style, add_layer_mask_from_selection, remove_layer_mask, export_layers_as_png, get_document_image, get_layer_image""",
    llm_config=llm_config,
    tools=tools
)


# ==========================================
# 6. MAIN
# ==========================================
def main():
    tool_registry = {
        # Document management
        "create_document": create_document,
        "get_documents": get_documents,
        "get_document_info": get_document_info,
        "set_active_document": set_active_document,
        "duplicate_document": duplicate_document,
        "save_document": save_document,
        "open_photoshop_file": open_photoshop_file,
        "crop_document": crop_document,
        
        # Layer management
        "get_layers": get_layers,
        "create_text_layer": create_text_layer,
        "create_multi_line_text_layer": create_multi_line_text_layer,
        "edit_text_layer": edit_text_layer,
        "create_pixel_layer": create_pixel_layer,
        "delete_layer": delete_layer,
        "duplicate_layer": duplicate_layer,
        "rename_layers": rename_layers,
        "group_layers": group_layers,
        "flatten_all_layers": flatten_all_layers,
        "set_layer_visibility": set_layer_visibility,
        "set_layer_properties": set_layer_properties,
        "get_layer_bounds": get_layer_bounds,
        
        # Selection tools
        "select_rectangle": select_rectangle,
        "select_ellipse": select_ellipse,
        "select_polygon": select_polygon,
        "select_subject": select_subject,
        "select_sky": select_sky,
        "invert_selection": invert_selection,
        "clear_selection": clear_selection,
        "copy_selection_to_clipboard": copy_selection_to_clipboard,
        "cut_selection_to_clipboard": cut_selection_to_clipboard,
        "copy_merged_selection_to_clipboard": copy_merged_selection_to_clipboard,
        "paste_from_clipboard": paste_from_clipboard,
        "delete_selection": delete_selection,
        "fill_selection": fill_selection,
        "align_content": align_content,
        
        # Image/layer manipulation
        "place_image": place_image,
        "scale_layer": scale_layer,
        "rotate_layer": rotate_layer,
        "flip_layer": flip_layer,
        "translate_layer": translate_layer,
        "move_layer": move_layer,
        "rasterize_layer": rasterize_layer,
        "remove_background": remove_background,
        "harmonize_layer": harmonize_layer,
        
        # Image generation and effects
        "generate_image": generate_image,
        "generative_fill": generative_fill,
        
        # Filters and effects
        "apply_gaussian_blur": apply_gaussian_blur,
        "apply_motion_blur": apply_motion_blur,
        
        # Layer styles and adjustments
        "add_drop_shadow_layer_style": add_drop_shadow_layer_style,
        "add_stroke_layer_style": add_stroke_layer_style,
        "add_color_balance_adjustment_layer": add_color_balance_adjustment_layer,
        "add_brightness_contrast_adjustment_layer": add_brightness_contrast_adjustment_layer,
        "add_vibrance_adjustment_layer": add_vibrance_adjustment_layer,
        "add_black_and_white_adjustment_layer": add_black_and_white_adjustment_layer,
        "create_gradient_layer_style": create_gradient_layer_style,
        
        # Layer masks
        "add_layer_mask_from_selection": add_layer_mask_from_selection,
        "remove_layer_mask": remove_layer_mask,
        
        # Export and output
        "export_layers_as_png": export_layers_as_png,
        "get_document_image": get_document_image,
        "get_layer_image": get_layer_image,
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