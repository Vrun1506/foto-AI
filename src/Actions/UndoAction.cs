namespace Loupedeck.FotoPlugin
{
    using System;

    public class UndoAction : PluginDynamicCommand
    {
        public UndoAction() : base(displayName: "Undo Action", description: null, groupName: "Utility")
        {
        }

        protected override void RunCommand(String actionParameter)
        {
        }
        
        protected override BitmapImage GetCommandImage(String actionParameter, PluginImageSize imageSize)
        {
            using (var bitmapBuilder = new BitmapBuilder(imageSize))
            {
                bitmapBuilder.SetBackgroundImage(PluginResources.ReadImage("undo.png"));

                return bitmapBuilder.ToImage();
            }
        }
    }
}