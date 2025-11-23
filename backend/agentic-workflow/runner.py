"""
Agent runner for processing images with user prompts.
Exposes a simple run_agent() function that can be called from server.py
"""
import sys
import os
from pathlib import Path

# Add mcp directory to path so we can import socket_client
mcp_path = str(Path(__file__).parent.parent.parent / "adb-mcp" / "mcp")
if mcp_path not in sys.path:
    sys.path.insert(0, mcp_path)

# Import agent functions
from agent import (
    send_photoshop_command, agent_spec, tools,
    # Document management
    create_document, get_documents, get_document_info, set_active_document,
    duplicate_document, save_document, open_photoshop_file, crop_document,
    # Layer management
    get_layers, create_text_layer, create_multi_line_text_layer, edit_text_layer,
    create_pixel_layer, delete_layer, duplicate_layer, rename_layers, group_layers,
    flatten_all_layers, set_layer_visibility, set_layer_properties, get_layer_bounds,
    # Selection tools
    select_rectangle, select_ellipse, select_polygon, select_subject, select_sky,
    invert_selection, clear_selection, copy_selection_to_clipboard, cut_selection_to_clipboard,
    copy_merged_selection_to_clipboard, paste_from_clipboard, delete_selection, fill_selection,
    align_content,
    # Image/layer manipulation
    place_image, scale_layer, rotate_layer, flip_layer, translate_layer, move_layer,
    rasterize_layer, remove_background, harmonize_layer,
    # Image generation and effects
    generate_image, generative_fill,
    # Filters and effects
    apply_gaussian_blur, apply_motion_blur,
    # Layer styles and adjustments
    add_drop_shadow_layer_style, add_stroke_layer_style, add_color_balance_adjustment_layer,
    add_brightness_contrast_adjustment_layer, add_vibrance_adjustment_layer,
    add_black_and_white_adjustment_layer, create_gradient_layer_style,
    # Layer masks
    add_layer_mask_from_selection, remove_layer_mask,
    # Export and output
    export_layers_as_png, get_document_image, get_layer_image
)
from pyagentspec.agent import Agent
from pyagentspec.llms import OpenAiConfig
from wayflowcore.agentspec import AgentSpecLoader


def run_agent(image_path: str, user_prompt: str) -> dict:
    """
    Run the Photoshop agent to process an image based on a user prompt.
    
    Args:
        image_path: Full path to the uploaded image file
        user_prompt: User's instruction/prompt for the agent
    
    Returns:
        dict with keys:
        - status: 'success' or 'error'
        - message: Result message or error details
        - result: Agent's response (if successful)
    """
    try:
        print(f"\n{'='*60}")
        print(f"🤖 Processing image with agent")
        print(f"{'='*60}")
        print(f"Image: {image_path}")
        print(f"Prompt: {user_prompt}\n")
        
        # Test connection to Photoshop
        print("🔍 Testing connection to Photoshop...")
        try:
            response = send_photoshop_command("getDocuments", {})
            if response and response.get("status") != "SUCCESS":
                return {
                    "status": "error",
                    "message": "Failed to connect to Photoshop. Ensure proxy and plugin are running.",
                    "result": None
                }
            print("✅ Connected to Photoshop\n")
        except Exception as e:
            return {
                "status": "error",
                "message": f"Connection error: {str(e)}",
                "result": None
            }
        
        # Build tool registry - must include ALL tools defined in agent_spec
        print("📦 Building tool registry...")
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
        
        # Load agent
        print("🚀 Loading agent...\n")
        loader = AgentSpecLoader(tool_registry=tool_registry)
        runtime_agent = loader.load_component(agent_spec)
        conversation = runtime_agent.start_conversation()
        
        # Build the prompt to include image path and user request
        full_prompt = f"""User uploaded an image at: {image_path}

User's request: {user_prompt}

Please:
1. Open the image file or create a new document with it
2. Apply any edits or transformations as requested
3. Save the result

Start by checking what documents are open, then proceed with the user's request."""
        
        # Run agent with the prompt
        print(f"📨 Sending prompt to agent...\n")
        conversation.append_user_message(full_prompt)
        print("⏳ Agent is thinking...\n")
        conversation.execute()
        
        # Get agent response
        agent_response = conversation.get_last_message().content
        print(f"✅ Agent response:\n{agent_response}\n")
        
        return {
            "status": "success",
            "message": "Image processed successfully",
            "result": agent_response
        }
    
    except Exception as e:
        print(f"❌ Error running agent: {str(e)}\n")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "message": f"Agent execution error: {str(e)}",
            "result": None
        }


def process_image_with_agent(image_path: str, prompt: str) -> dict:
    """
    Simplified wrapper for processing an image with the agent.
    
    Args:
        image_path: Path to uploaded image
        prompt: User's processing instructions
    
    Returns:
        dict with processing result
    """
    return run_agent(image_path, prompt)
