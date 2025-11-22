namespace Loupedeck.FotoPlugin
{
    using System;

    public class TemperatureToggle : PluginDynamicCommand
    {
        private Boolean _tempToggled = false;
        private readonly String _imageResourcePathOn;
        private readonly String _imageResourcePathOff;

        public TemperatureToggle() : base(displayName: "Temperature Switch", description: null, groupName: "Switches")
        {
            this._imageResourcePathOn = PluginResources.FindFile("temperatureOn.png");
            this._imageResourcePathOff = PluginResources.FindFile("temperatureOff.png");
        }

        protected override void RunCommand(String actionParameter)
        {
            this._tempToggled = !this._tempToggled;
            this.ActionImageChanged();
        }
        
        protected override BitmapImage GetCommandImage(String actionParameter, PluginImageSize imageSize)
        {
            var resourcePath = this._tempToggled ? this._imageResourcePathOn : this._imageResourcePathOff;
            return PluginResources.ReadImage(resourcePath);
        }
    }
}