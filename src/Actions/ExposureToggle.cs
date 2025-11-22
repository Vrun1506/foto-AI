namespace Loupedeck.FotoPlugin
{
    using System;

    public class ExposureToggle : PluginDynamicCommand
    {
        private Boolean _exposureToggled = false;
        private readonly String _imageResourcePathOn;
        private readonly String _imageResourcePathOff;

        public ExposureToggle() : base(displayName: "Exposure Switch", description: null, groupName: "Switches")
        {
            this._imageResourcePathOn = PluginResources.FindFile("exposureOn.png");
            this._imageResourcePathOff = PluginResources.FindFile("exposureOff.png");
        }

        protected override void RunCommand(String actionParameter)
        {
            this._exposureToggled = !this._exposureToggled;
            this.ActionImageChanged();
        }
        
        protected override BitmapImage GetCommandImage(String actionParameter, PluginImageSize imageSize)
        {
            var resourcePath = this._exposureToggled ? this._imageResourcePathOn : this._imageResourcePathOff;
            return PluginResources.ReadImage(resourcePath);
        }
    }
}