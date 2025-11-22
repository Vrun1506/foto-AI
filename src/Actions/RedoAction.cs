namespace Loupedeck.FotoPlugin
{
    using System;

    public class RedoAction : PluginDynamicCommand
    {
        public RedoAction() : base(displayName: "Redo Action", description: null, groupName: "Utility")
        {
        }

        protected override void RunCommand(String actionParameter)
        {
        }
        
        protected override BitmapImage GetCommandImage(String actionParameter, PluginImageSize imageSize)
        {
            using (var bitmapBuilder = new BitmapBuilder(imageSize))
            {
                bitmapBuilder.SetBackgroundImage(PluginResources.ReadImage("redo.png"));

                return bitmapBuilder.ToImage();
            }
        }
    }
}