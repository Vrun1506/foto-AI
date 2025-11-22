using System;
using System.Net.WebSockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Loupedeck;

namespace HapticWsPlugin
{
    public class HapticWsPlugin : Plugin
    {
        private ClientWebSocket _webSocket;
        private CancellationTokenSource _cts;

        // Plugin works without a specific application
        public override Boolean HasNoApplication => true;

        // Called when plugin is loaded by Logi Plugin Service
        public override void Load()
        {
            // Register the haptic event
            this.PluginEvents.AddEvent(
                "hapticBurst",                  // event name (must match YAML)
                "Haptic Burst",                 // display name
                "Fires when a WebSocket notification is received"
            );

            _cts = new CancellationTokenSource();
            _ = Task.Run(() => RunWebSocketListenerAsync(_cts.Token));
        }

        // Called when plugin is unloaded (Options+ quits, plugin disabled, etc.)
        public override void Unload()
        {
            try
            {
                _cts?.Cancel();
                _webSocket?.Dispose();
            }
            catch
            {
                // ignore cleanup errors
            }
        }

        // Background WebSocket client
        private async Task RunWebSocketListenerAsync(CancellationToken token)
        {
            var uri = new Uri("ws://localhost:8080/notifications");

            while (!token.IsCancellationRequested)
            {
                try
                {
                    _webSocket?.Dispose();
                    _webSocket = new ClientWebSocket();

                    await _webSocket.ConnectAsync(uri, token);

                    var buffer = new byte[4096];

                    while (_webSocket.State == WebSocketState.Open && !token.IsCancellationRequested)
                    {
                        var result = await _webSocket.ReceiveAsync(buffer, token);

                        if (result.MessageType == WebSocketMessageType.Close)
                        {
                            await _webSocket.CloseAsync(
                                WebSocketCloseStatus.NormalClosure,
                                "Closing",
                                token
                            );
                            break;
                        }

                        var msg = Encoding.UTF8.GetString(buffer, 0, result.Count);

                        // Every time we get a message → vibrate
                        OnWebSocketNotification(msg);
                    }
                }
                catch (OperationCanceledException)
                {
                    // plugin is unloading
                    break;
                }
                catch (Exception)
                {
                    // Wait a bit and retry connection
                    await Task.Delay(2000, token);
                }
            }
        }

        private void OnWebSocketNotification(String message)
        {
            // You can parse/filter JSON here if you want
            this.PluginEvents.RaiseEvent("hapticBurst");
        }
    }
}
