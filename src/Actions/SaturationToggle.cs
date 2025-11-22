namespace Loupedeck.FotoPlugin
{
    using System;

    public class SaturationToggle : PluginDynamicCommand
    {
        private Boolean _saturationToggled = false;
        private readonly String _imageResourcePathOn;
        private readonly String _imageResourcePathOff;

        public SaturationToggle() : base(displayName: "Saturation Switch", description: null, groupName: "Switches")
        {
            this._imageResourcePathOn = PluginResources.FindFile("saturationOn.png");
            this._imageResourcePathOff = PluginResources.FindFile("saturationOff.png");
        }

        protected override void RunCommand(String actionParameter)
        {
            this._saturationToggled = !this._saturationToggled;
            this.ActionImageChanged();
        }
        
        protected override BitmapImage GetCommandImage(String actionParameter, PluginImageSize imageSize)
        {
            var resourcePath = this._saturationToggled ? this._imageResourcePathOn : this._imageResourcePathOff;
            return PluginResources.ReadImage(resourcePath);
        }
    }
}