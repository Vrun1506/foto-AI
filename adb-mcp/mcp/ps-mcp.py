# MIT License
#
# Copyright (c) 2025 Mike Chambers
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from mcp.server.fastmcp import FastMCP, Image
from core import init, sendCommand, createCommand
from fonts import list_all_fonts_postscript
import numpy as np
import base64
import socket_client
import sys
import os
import traceback
import time
import asyncio

FONT_LIMIT = 1000

mcp_name = "Adobe Photoshop MCP Server"
mcp = FastMCP(mcp_name, log_level="ERROR")

APPLICATION = "photoshop"
PROXY_URL = 'http://localhost:3001'
PROXY_TIMEOUT = 20

socket_client.configure(
    app=APPLICATION, 
    url=PROXY_URL,
    timeout=PROXY_TIMEOUT
)

init(APPLICATION, socket_client)

@mcp.tool()
def set_active_document(document_id:int):
    """Sets the document with the specified ID to the active document in Photoshop"""
    command = createCommand("setActiveDocument", {"documentId":document_id})
    return sendCommand(command)

@mcp.tool()
def get_documents():
    """Returns information on the documents currently open in Photoshop"""
    command = createCommand("getDocuments", {})
    return sendCommand(command)

@mcp.tool()
def create_gradient_layer_style(layer_id: int, angle: int, type:str, color_stops: list, opacity_stops: list):
    """Applies gradient to active selection or entire layer if no selection exists."""
    command = createCommand("createGradientLayerStyle", {
        "layerId":layer_id, "angle":angle, "colorStops":color_stops,
        "type":type, "opacityStops":opacity_stops
    })
    return sendCommand(command)

@mcp.tool()
def duplicate_document(document_name: str):
    """Duplicates the current Photoshop Document into a new file"""
    command = createCommand("duplicateDocument", {"name":document_name})
    return sendCommand(command)

@mcp.tool()
def create_document(document_name: str, width: int, height:int, resolution:int, fill_color:dict = {"red":0, "green":0, "blue":0}, color_mode:str = "RGB"):
    """Creates a new Photoshop Document"""
    command = createCommand("createDocument", {
        "name":document_name, "width":width, "height":height,
        "resolution":resolution, "fillColor":fill_color, "colorMode":color_mode
    })
    return sendCommand(command)

@mcp.tool()
def export_layers_as_png(layers_info: list[dict[str, str|int]]):
    """Exports multiple layers from the Photoshop document as PNG files."""
    command = createCommand("exportLayersAsPng", {"layersInfo":layers_info})
    return sendCommand(command)

@mcp.tool()
def save_document_as(file_path: str, file_type: str = "PSD"):
    """Saves the current Photoshop document to the specified location and format."""
    command = createCommand("saveDocumentAs", {"filePath":file_path, "fileType":file_type})
    return sendCommand(command)

@mcp.tool()
def save_document():
    """Saves the current Photoshop Document"""
    command = createCommand("saveDocument", {})
    return sendCommand(command)

@mcp.tool()
def group_layers(group_name: str, layer_ids: list[int]) -> list:
    """Creates a new layer group from the specified layers in Photoshop."""
    command = createCommand("groupLayers", {"groupName":group_name, "layerIds":layer_ids})
    return sendCommand(command)

@mcp.tool()
def get_layer_image(layer_id: int):
    """Returns a jpeg of the specified layer's content as an MCP Image object."""
    command = createCommand("getLayerImage", {"layerId":layer_id})
    response = sendCommand(command)
    if response.get('status') == 'SUCCESS' and 'response' in response:
        image_data = response['response']
        data_url = image_data.get('dataUrl')
        if data_url and data_url.startswith("data:image/jpeg;base64,"):
            base64_data = data_url.split(",", 1)[1]
            jpeg_bytes = base64.b64decode(base64_data)
            return Image(data=jpeg_bytes, format="jpeg")
    return response

@mcp.tool()
def get_document_image():
    """Returns a jpeg of the current visible Photoshop document as an MCP Image object."""
    command = createCommand("getDocumentImage", {})
    response = sendCommand(command)
    if response.get('status') == 'SUCCESS' and 'response' in response:
        image_data = response['response']
        data_url = image_data.get('dataUrl')
        if data_url and data_url.startswith("data:image/jpeg;base64,"):
            base64_data = data_url.split(",", 1)[1]
            jpeg_bytes = base64.b64decode(base64_data)
            return Image(data=jpeg_bytes, format="jpeg")
    return response

@mcp.tool()
def save_document_image_as_png(file_path: str):
    """Capture the Photoshop document and save as PNG file"""
    command = createCommand("getDocumentImage", {})
    response = sendCommand(command)
    if response.get('format') == 'raw' and 'rawDataBase64' in response:
        try:
            raw_bytes = base64.b64decode(response['rawDataBase64'])
            width, height, components = response['width'], response['height'], response['components']
            pixel_array = np.frombuffer(raw_bytes, dtype=np.uint8)
            image_array = pixel_array.reshape((height, width, components))
            mode = 'RGBA' if components == 4 else 'RGB'
            image = Image.fromarray(image_array, mode)
            image.save(file_path, 'PNG')
            return {'status': 'success', 'file_path': file_path, 'width': width, 'height': height, 'size_bytes': os.path.getsize(file_path)}
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    return {'status': 'error', 'error': 'No raw image data received'}

@mcp.tool()
def get_layers() -> list:
    """Returns a nested list of dicts that contain layer info and the order they are arranged in."""
    command = createCommand("getLayers", {})
    return sendCommand(command)

@mcp.tool()
def place_image(layer_id: int, image_path: str):
    """Places the image at the specified path on the existing pixel layer."""
    command = createCommand("placeImage", {"layerId":layer_id, "imagePath":image_path})
    return sendCommand(command)

@mcp.tool()
def harmonize_layer(layer_id:int, new_layer_name:str, rasterize_layer:bool = True):
    """Harmonizes the selected layer with the background layers."""
    command = createCommand("harmonizeLayer", {"layerId":layer_id, "newLayerName":new_layer_name, "rasterizeLayer":rasterize_layer})
    return sendCommand(command)

@mcp.tool()
def rename_layers(layer_data: list[dict]):
    """Renames one or more layers"""
    command = createCommand("renameLayers", {"layerData":layer_data})
    return sendCommand(command)

@mcp.tool()
def scale_layer(layer_id:int, width:int, height:int, anchor_position:str, interpolation_method:str = "AUTOMATIC"):
    """Scales the layer with the specified ID."""
    command = createCommand("scaleLayer", {"layerId":layer_id, "width":width, "height":height, "anchorPosition":anchor_position, "interpolationMethod":interpolation_method})
    return sendCommand(command)

@mcp.tool()
def rotate_layer(layer_id:int, angle:int, anchor_position:str, interpolation_method:str = "AUTOMATIC"):
    """Rotates the layer with the specified ID."""
    command = createCommand("rotateLayer", {"layerId":layer_id, "angle":angle, "anchorPosition":anchor_position, "interpolationMethod":interpolation_method})
    return sendCommand(command)

@mcp.tool()
def flip_layer(layer_id:int, axis:str):
    """Flips the layer with the specified ID on the specified axis."""
    command = createCommand("flipLayer", {"layerId":layer_id, "axis":axis})
    return sendCommand(command)

@mcp.tool()
def delete_layer(layer_id:int):
    """Deletes the layer with the specified ID"""
    command = createCommand("deleteLayer", {"layerId":layer_id})
    return sendCommand(command)

@mcp.tool()
def set_layer_visibility(layer_id:int, visible:bool):
    """Sets the visibility of the layer with the specified ID"""
    command = createCommand("setLayerVisibility", {"layerId":layer_id, "visible":visible})
    return sendCommand(command)

@mcp.tool()
def generate_image(layer_name:str, prompt:str, content_type:str = "none"):
    """Uses Adobe Firefly Generative AI to generate an image on a new layer."""
    command = createCommand("generateImage", {"layerName":layer_name, "prompt":prompt, "contentType":content_type})
    return sendCommand(command)

@mcp.tool()
def generative_fill(layer_name: str, prompt: str, layer_id: int, content_type: str = "none"):
    """Uses Adobe Firefly Generative AI to perform generative fill within the current selection."""
    command = createCommand("generativeFill", {"layerName":layer_name, "prompt":prompt, "layerId":layer_id, "contentType":content_type})
    return sendCommand(command)

@mcp.tool()
def move_layer(layer_id:int, position:str):
    """Moves the layer within the layer stack based on the specified position"""
    command = createCommand("moveLayer", {"layerId":layer_id, "position":position})
    return sendCommand(command)

@mcp.tool()
def get_document_info():
    """Retrieves information about the currently active document."""
    command = createCommand("getDocumentInfo", {})
    return sendCommand(command)

@mcp.tool()
def crop_document():
    """Crops the document to the active selection."""
    command = createCommand("cropDocument", {})
    return sendCommand(command)

@mcp.tool()
def paste_from_clipboard(layer_id: int, paste_in_place: bool = True):
    """Pastes the current clipboard contents onto the specified layer."""
    command = createCommand("pasteFromClipboard", {"layerId":layer_id, "pasteInPlace":paste_in_place})
    return sendCommand(command)

@mcp.tool()
def rasterize_layer(layer_id: int):
    """Converts the specified layer into a rasterized (flat) image."""
    command = createCommand("rasterizeLayer", {"layerId":layer_id})
    return sendCommand(command)

@mcp.tool()
def open_photoshop_file(file_path: str):
    """Opens the specified Photoshop-compatible file within Photoshop."""
    command = createCommand("openFile", {"filePath":file_path})
    return sendCommand(command)

@mcp.tool()
def cut_selection_to_clipboard(layer_id: int):
    """Copies and removes (cuts) the selected pixels from the specified layer to clipboard."""
    command = createCommand("cutSelectionToClipboard", {"layerId":layer_id})
    return sendCommand(command)

@mcp.tool()
def copy_merged_selection_to_clipboard():
    """Copies the selected pixels from all visible layers to the clipboard."""
    command = createCommand("copyMergedSelectionToClipboard", {})
    return sendCommand(command)

@mcp.tool()
def copy_selection_to_clipboard(layer_id: int):
    """Copies the selected pixels from the specified layer to the clipboard."""
    command = createCommand("copySelectionToClipboard", {"layerId":layer_id})
    return sendCommand(command)

@mcp.tool()
def select_subject(layer_id: int):
    """Automatically selects the subject in the specified layer."""
    command = createCommand("selectSubject", {"layerId":layer_id})
    return sendCommand(command)

@mcp.tool()
def select_sky(layer_id: int):
    """Automatically selects the sky in the specified layer."""
    command = createCommand("selectSky", {"layerId":layer_id})
    return sendCommand(command)

@mcp.tool()
def get_layer_bounds(layer_id: int):
    """Returns the pixel bounds for the layer with the specified ID"""
    command = createCommand("getLayerBounds", {"layerId":layer_id})
    return sendCommand(command)

@mcp.tool()
def remove_background(layer_id:int):
    """Automatically removes the background of the image in the layer."""
    command = createCommand("removeBackground", {"layerId":layer_id})
    return sendCommand(command)

@mcp.tool()
def create_pixel_layer(layer_name:str, fill_neutral:bool, opacity:int = 100, blend_mode:str = "NORMAL"):
    """Creates a new pixel layer with the specified ID"""
    command = createCommand("createPixelLayer", {"layerName":layer_name, "opacity":opacity, "fillNeutral":fill_neutral, "blendMode":blend_mode})
    return sendCommand(command)

@mcp.tool()
def create_multi_line_text_layer(layer_name:str, text:str, font_size:int, postscript_font_name:str, opacity:int = 100, blend_mode:str = "NORMAL", text_color:dict = {"red":255, "green":255, "blue":255}, position:dict = {"x": 100, "y":100}, bounds:dict = {"top": 0, "left": 0, "bottom": 250, "right": 300}, justification:str = "LEFT"):
    """Creates a new multi-line text layer."""
    command = createCommand("createMultiLineTextLayer", {"layerName":layer_name, "contents":text, "fontSize": font_size, "opacity":opacity, "position":position, "fontName":postscript_font_name, "textColor":text_color, "blendMode":blend_mode, "bounds":bounds, "justification":justification})
    return sendCommand(command)

@mcp.tool()
def create_single_line_text_layer(layer_name:str, text:str, font_size:int, postscript_font_name:str, opacity:int = 100, blend_mode:str = "NORMAL", text_color:dict = {"red":255, "green":255, "blue":255}, position:dict = {"x": 100, "y":100}):
    """Create a new single line text layer."""
    command = createCommand("createSingleLineTextLayer", {"layerName":layer_name, "contents":text, "fontSize": font_size, "opacity":opacity, "position":position, "fontName":postscript_font_name, "textColor":text_color, "blendMode":blend_mode})
    return sendCommand(command)

@mcp.tool()
def edit_text_layer(layer_id:int, text:str = None, font_size:int = None, postscript_font_name:str = None, text_color:dict = None):
    """Edits the text content of an existing text layer."""
    command = createCommand("editTextLayer", {"layerId":layer_id, "contents":text, "fontSize": font_size, "fontName":postscript_font_name, "textColor":text_color})
    return sendCommand(command)

@mcp.tool()
def translate_layer(layer_id: int, x_offset:int = 0, y_offset:int = 0):
    """Moves the layer on the X and Y axis by the specified number of pixels."""
    command = createCommand("translateLayer", {"layerId":layer_id, "xOffset":x_offset, "yOffset":y_offset})
    return sendCommand(command)

@mcp.tool()
def remove_layer_mask(layer_id: int):
    """Removes the layer mask from the specified layer."""
    command = createCommand("removeLayerMask", {"layerId":layer_id})
    return sendCommand(command)

@mcp.tool()
def add_layer_mask_from_selection(layer_id: int):
    """Creates a layer mask on the specified layer defined by the active selection."""
    command = createCommand("addLayerMask", {"layerId":layer_id})
    return sendCommand(command)

@mcp.tool()
def set_layer_properties(layer_id: int, blend_mode: str = "NORMAL", layer_opacity: int = 100, fill_opacity: int = 100, is_clipping_mask: bool = False):
    """Sets the blend mode and opacity properties on the layer."""
    command = createCommand("setLayerProperties", {"layerId":layer_id, "blendMode":blend_mode, "layerOpacity":layer_opacity, "fillOpacity":fill_opacity, "isClippingMask":is_clipping_mask})
    return sendCommand(command)

@mcp.tool()
def fill_selection(layer_id: int, color:dict = {"red":255, "green":0, "blue":0}, blend_mode:str = "NORMAL", opacity:int = 100):
    """Fills the selection on the pixel layer."""
    command = createCommand("fillSelection", {"layerId":layer_id, "color":color, "blendMode":blend_mode, "opacity":opacity})
    return sendCommand(command)

@mcp.tool()
def delete_selection(layer_id: int):
    """Removes the pixels within the selection on the pixel layer."""
    command = createCommand("deleteSelection", {"layerId":layer_id})
    return sendCommand(command)

@mcp.tool()
def invert_selection():
    """Inverts the current selection in the Photoshop document"""
    command = createCommand("invertSelection", {})
    return sendCommand(command)

@mcp.tool()
def clear_selection():
    """Clears / deselects the current selection"""
    command = createCommand("selectRectangle", {"feather":0, "antiAlias":True, "bounds":{"top": 0, "left": 0, "bottom": 0, "right": 0}})
    return sendCommand(command)

@mcp.tool()
def select_rectangle(layer_id:int, feather:int = 0, anti_alias:bool = True, bounds:dict = {"top": 0, "left": 0, "bottom": 100, "right": 100}):
    """Creates a rectangular selection and selects the specified layer"""
    command = createCommand("selectRectangle", {"layerId":layer_id, "feather":feather, "antiAlias":anti_alias, "bounds":bounds})
    return sendCommand(command)

@mcp.tool()
def select_polygon(layer_id:int, feather:int = 0, anti_alias:bool = True, points:list[dict[str, int]] = [{"x": 50, "y": 10}, {"x": 100, "y": 90}, {"x": 10, "y": 40}]):
    """Creates an n-sided polygon selection and selects the specified layer"""
    command = createCommand("selectPolygon", {"layerId":layer_id, "feather":feather, "antiAlias":anti_alias, "points":points})
    return sendCommand(command)

@mcp.tool()
def select_ellipse(layer_id:int, feather:int = 0, anti_alias:bool = True, bounds:dict = {"top": 0, "left": 0, "bottom": 100, "right": 100}):
    """Creates an elliptical selection and selects the specified layer"""
    command = createCommand("selectEllipse", {"layerId":layer_id, "feather":feather, "antiAlias":anti_alias, "bounds":bounds})
    return sendCommand(command)

@mcp.tool()
def align_content(layer_id: int, alignment_mode:str):
    """Aligns content on layer to the current selection."""
    command = createCommand("alignContent", {"layerId":layer_id, "alignmentMode":alignment_mode})
    return sendCommand(command)

@mcp.tool()
def add_drop_shadow_layer_style(layer_id: int, blend_mode:str = "MULTIPLY", color:dict = {"red":0, "green":0, "blue":0}, opacity:int = 35, angle:int = 160, distance:int = 3, spread:int = 0, size:int = 7):
    """Adds a drop shadow layer style to the layer."""
    command = createCommand("addDropShadowLayerStyle", {"layerId":layer_id, "blendMode":blend_mode, "color":color, "opacity":opacity, "angle":angle, "distance":distance, "spread":spread, "size":size})
    return sendCommand(command)

@mcp.tool()
def duplicate_layer(layer_to_duplicate_id:int, duplicate_layer_name:str):
    """Duplicates the layer specified by ID, creating a new layer above it."""
    command = createCommand("duplicateLayer", {"sourceLayerId":layer_to_duplicate_id, "duplicateLayerName":duplicate_layer_name})
    return sendCommand(command)

@mcp.tool()
def flatten_all_layers(layer_name:str):
    """Flatten all layers in the document into a single layer."""
    command = createCommand("flattenAllLayers", {"layerName":layer_name})
    return sendCommand(command)

@mcp.tool()
def add_color_balance_adjustment_layer(layer_id: int, highlights:list = [0,0,0], midtones:list = [0,0,0], shadows:list = [0,0,0]):
    """Adds an adjustment layer to adjust color balance"""
    command = createCommand("addColorBalanceAdjustmentLayer", {"layerId":layer_id, "highlights":highlights, "midtones":midtones, "shadows":shadows})
    return sendCommand(command)

@mcp.tool()
def add_brightness_contrast_adjustment_layer(layer_id: int, brightness:int = 0, contrast:int = 0):
    """Adds an adjustment layer to adjust brightness and contrast"""
    command = createCommand("addBrightnessContrastAdjustmentLayer", {"layerId":layer_id, "brightness":brightness, "contrast":contrast})
    return sendCommand(command)

@mcp.tool()
def add_stroke_layer_style(layer_id: int, size: int = 2, color: dict = {"red": 0, "green": 0, "blue": 0}, opacity: int = 100, position: str = "CENTER", blend_mode: str = "NORMAL"):
    """Adds a stroke layer style to the layer."""
    command = createCommand("addStrokeLayerStyle", {"layerId":layer_id, "size":size, "color":color, "opacity":opacity, "position":position, "blendMode":blend_mode})
    return sendCommand(command)

@mcp.tool()
def add_vibrance_adjustment_layer(layer_id: int, vibrance:int = 0, saturation:int = 0):
    """Adds an adjustment layer to adjust vibrance and saturation"""
    command = createCommand("addAdjustmentLayerVibrance", {"layerId":layer_id, "saturation":saturation, "vibrance":vibrance})
    return sendCommand(command)

@mcp.tool()
def add_black_and_white_adjustment_layer(layer_id: int, colors: dict = {"blue": 20, "cyan": 60, "green": 40, "magenta": 80, "red": 40, "yellow": 60}, tint: bool = False, tint_color: dict = {"red": 225, "green": 211, "blue": 179}):
    """Adds a Black & White adjustment layer to the specified layer."""
    command = createCommand("addAdjustmentLayerBlackAndWhite", {"layerId":layer_id, "colors":colors, "tint":tint, "tintColor":tint_color})
    return sendCommand(command)

@mcp.tool()
def apply_gaussian_blur(layer_id: int, radius: float = 2.5):
    """Applies a Gaussian Blur to the layer."""
    command = createCommand("applyGaussianBlur", {"layerId":layer_id, "radius":radius})
    return sendCommand(command)

@mcp.tool()
def apply_motion_blur(layer_id: int, angle: int = 0, distance: float = 30):
    """Applies a Motion Blur to the layer."""
    command = createCommand("applyMotionBlur", {"layerId":layer_id, "angle":angle, "distance":distance})
    return sendCommand(command)

@mcp.resource("config://get_instructions")
def get_instructions() -> str:
    """Read this first! Returns information and instructions on how to use Photoshop and this API"""
    return f"""
    You are a photoshop expert who is creative and loves to help other people learn to use Photoshop and create.

    Rules to follow:
    1. Think deeply about how to solve the task
    2. Always check your work
    3. You can view the current visible photoshop file by calling get_document_image
    4. Pay attention to font size (dont make it too big)
    5. Always use alignment (align_content()) to position your text.
    6. Read the info for the API calls to make sure you understand the requirements and arguments
    7. When you make a selection, clear it once you no longer need it

    alignment_modes: {", ".join(alignment_modes)}
    justification_modes: {", ".join(justification_modes)}
    blend_modes: {", ".join(blend_modes)}
    anchor_positions: {", ".join(anchor_positions)}
    interpolation_methods: {", ".join(interpolation_methods)}
    fonts: {", ".join(font_names[:FONT_LIMIT])}
    """

font_names = list_all_fonts_postscript()

interpolation_methods = ["AUTOMATIC", "BICUBIC", "BICUBICSHARPER", "BICUBICSMOOTHER", "BILINEAR", "NEARESTNEIGHBOR"]
anchor_positions = ["BOTTOMCENTER", "BOTTOMLEFT", "BOTTOMRIGHT", "MIDDLECENTER", "MIDDLELEFT", "MIDDLERIGHT", "TOPCENTER", "TOPLEFT", "TOPRIGHT"]
justification_modes = ["CENTER", "CENTERJUSTIFIED", "FULLYJUSTIFIED", "LEFT", "LEFTJUSTIFIED", "RIGHT", "RIGHTJUSTIFIED"]
alignment_modes = ["LEFT", "CENTER_HORIZONTAL", "RIGHT", "TOP", "CENTER_VERTICAL", "BOTTOM"]
blend_modes = ["COLOR", "COLORBURN", "COLORDODGE", "DARKEN", "DARKERCOLOR", "DIFFERENCE", "DISSOLVE", "DIVIDE", "EXCLUSION", "HARDLIGHT", "HARDMIX", "HUE", "LIGHTEN", "LIGHTERCOLOR", "LINEARBURN", "LINEARDODGE", "LINEARLIGHT", "LUMINOSITY", "MULTIPLY", "NORMAL", "OVERLAY", "PASSTHROUGH", "PINLIGHT", "SATURATION", "SCREEN", "SOFTLIGHT", "SUBTRACT", "VIVIDLIGHT"]


# ============== FIXED SERVER STARTUP CODE ==============

def _start_mcp_server(mcp_obj):
    """
    Starts the MCP server with proper debugging and multiple fallback methods.
    """
    print(f"LOGGER : Starting MCP server...", file=sys.stderr)
    print(f"LOGGER : MCP object type: {type(mcp_obj)}", file=sys.stderr)
    
    # Log all available methods for debugging
    methods = [m for m in dir(mcp_obj) if not m.startswith('_')]
    print(f"LOGGER : Available methods: {methods}", file=sys.stderr)
    
    try:
        # Method 1: Try run() - most common for FastMCP
        if hasattr(mcp_obj, 'run'):
            print("LOGGER : Attempting mcp.run()...", file=sys.stderr)
            result = mcp_obj.run()
            # If run() returns a coroutine, we need to await it
            if asyncio.iscoroutine(result):
                print("LOGGER : run() returned coroutine, using asyncio.run()...", file=sys.stderr)
                asyncio.run(result)
            print("LOGGER : mcp.run() completed", file=sys.stderr)
            return
    except Exception as e:
        print(f"LOGGER : mcp.run() failed: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
    
    try:
        # Method 2: Try run_stdio() - some versions use this
        if hasattr(mcp_obj, 'run_stdio'):
            print("LOGGER : Attempting mcp.run_stdio()...", file=sys.stderr)
            result = mcp_obj.run_stdio()
            if asyncio.iscoroutine(result):
                asyncio.run(result)
            print("LOGGER : mcp.run_stdio() completed", file=sys.stderr)
            return
    except Exception as e:
        print(f"LOGGER : mcp.run_stdio() failed: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
    
    try:
        # Method 3: Try using the underlying server directly
        if hasattr(mcp_obj, 'server'):
            print("LOGGER : Found mcp.server, checking for run methods...", file=sys.stderr)
            server = mcp_obj.server
            if hasattr(server, 'run'):
                result = server.run()
                if asyncio.iscoroutine(result):
                    asyncio.run(result)
                return
    except Exception as e:
        print(f"LOGGER : server.run() failed: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
    
    try:
        # Method 4: Try async context manager pattern
        print("LOGGER : Attempting async context manager pattern...", file=sys.stderr)
        async def run_server():
            async with mcp_obj:
                # Keep running indefinitely
                while True:
                    await asyncio.sleep(1)
        asyncio.run(run_server())
        return
    except Exception as e:
        print(f"LOGGER : Async context manager failed: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
    
    try:
        # Method 5: Try mcp.run with transport="stdio" argument
        if hasattr(mcp_obj, 'run'):
            print("LOGGER : Attempting mcp.run(transport='stdio')...", file=sys.stderr)
            result = mcp_obj.run(transport="stdio")
            if asyncio.iscoroutine(result):
                asyncio.run(result)
            return
    except TypeError:
        # run() doesn't accept transport argument
        pass
    except Exception as e:
        print(f"LOGGER : mcp.run(transport='stdio') failed: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
    
    # If nothing worked, log and exit with error
    print("LOGGER : ERROR - No working server start method found!", file=sys.stderr)
    print("LOGGER : Please try one of the following:", file=sys.stderr)
    print("LOGGER :   1. Install fastmcp: pip install fastmcp", file=sys.stderr)
    print("LOGGER :   2. Run with CLI: fastmcp run server.py:mcp", file=sys.stderr)
    print("LOGGER :   3. Update mcp package: pip install --upgrade mcp", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    try:
        _start_mcp_server(mcp)
    except KeyboardInterrupt:
        print("LOGGER : Server stopped by user", file=sys.stderr)
    except NameError as e:
        print(f"LOGGER : 'mcp' variable not found: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"LOGGER : Unexpected error: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)