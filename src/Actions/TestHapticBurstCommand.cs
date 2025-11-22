using System;
using System.Threading;
using System.Threading.Tasks;
using Loupedeck;

namespace HapticWsPlugin.Actions
{
    public class TestHapticBurstCommand : PluginDynamicCommand
    {
        public TestHapticBurstCommand()
            : base(
                displayName: "Test Haptic Burst",
                description: "Manual test of haptic burst",
                groupName: "Haptics"
            )
        {
        }

        protected override void RunCommand(String actionParameter)
        {
            // 3 short pulses
            _ = Task.Run(() =>
            {
                for (var i = 0; i < 20; i++)
                {
                    this.Plugin.PluginEvents.RaiseEvent("hapticBurst");
                    Thread.Sleep(250);
                }
            });
        }
    }
}