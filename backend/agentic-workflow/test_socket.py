"""
Direct Socket.IO test - bypasses MCP entirely to test proxy connection.
Save as test_socket.py and run: python test_socket.py
"""
import socketio
import json

sio = socketio.Client(logger=True, engineio_logger=True)

@sio.event
def connect():
    print("\n" + "="*50)
    print("✅ CONNECTED TO PROXY!")
    print("="*50 + "\n")
    
    # Send a create document command
    command = {
        "application": "photoshop",
        "action": "createDocument",
        "options": {
            "name": "Socket_Test_Doc",
            "width": 800,
            "height": 600,
            "resolution": 72,
            "fillColor": {"red": 100, "green": 150, "blue": 200},
            "colorMode": "RGB"
        }
    }
    
    print(f"📤 Sending command: {json.dumps(command, indent=2)}")
    
    sio.emit('command_packet', {
        'type': "command",
        'application': "photoshop",
        'command': command
    })
    print("📤 Command sent, waiting for response...")

@sio.event
def packet_response(data):
    print("\n" + "="*50)
    print("✅ RESPONSE RECEIVED!")
    print("="*50)
    print(f"📥 Data: {json.dumps(data, indent=2) if isinstance(data, dict) else data}")
    print("="*50 + "\n")
    sio.disconnect()

@sio.event
def disconnect():
    print("🔌 Disconnected from proxy")

@sio.event
def connect_error(error):
    print(f"\n❌ CONNECTION ERROR: {error}\n")

# Also listen for any other events
@sio.on('*')
def catch_all(event, data):
    print(f"📨 Received event '{event}': {data}")

if __name__ == "__main__":
    print("\n" + "="*50)
    print("Socket.IO Direct Test")
    print("="*50)
    print("\nConnecting to http://localhost:3001 via WebSocket...")
    print("(Make sure proxy is running and Photoshop plugin is connected)\n")
    
    try:
        sio.connect("http://localhost:3001", transports=['websocket'])
        sio.wait()
    except KeyboardInterrupt:
        print("\n👋 Interrupted")
        if sio.connected:
            sio.disconnect()
    except Exception as e:
        print(f"\n❌ Error: {e}")