namespace Loupedeck.FotoPlugin
{
    using System;

    public class SaveAction : PluginDynamicCommand
    {
        public SaveAction() : base(displayName: "Save Action", description: null, groupName: "Utility")
        {
        }

        protected override void RunCommand(String actionParameter)
        {
        }
        
        protected override BitmapImage GetCommandImage(String actionParameter, PluginImageSize imageSize)
        {
            using (var bitmapBuilder = new BitmapBuilder(imageSize))
            {
                bitmapBuilder.SetBackgroundImage(PluginResources.ReadImage("save.png"));

                return bitmapBuilder.ToImage();
            }
        }
    }
}