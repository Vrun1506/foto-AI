namespace Loupedeck.FotoPlugin
{
    using System;

    public class HighlightToggle : PluginDynamicCommand
    {
        private Boolean _highlightToggled = false;
        private readonly String _imageResourcePathOn;
        private readonly String _imageResourcePathOff;

        public HighlightToggle() : base(displayName: "Highlight Switch", description: null, groupName: "Switches")
        {
            this._imageResourcePathOn = PluginResources.FindFile("highlightOn.png");
            this._imageResourcePathOff = PluginResources.FindFile("highlightOff.png");
        }

        protected override void RunCommand(String actionParameter)
        {
            this._highlightToggled = !this._highlightToggled;
            this.ActionImageChanged();
        }
        
        protected override BitmapImage GetCommandImage(String actionParameter, PluginImageSize imageSize)
        {
            var resourcePath = this._highlightToggled ? this._imageResourcePathOn : this._imageResourcePathOff;
            return PluginResources.ReadImage(resourcePath);
        }
    }
}