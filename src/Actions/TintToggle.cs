namespace Loupedeck.FotoPlugin
{
    using System;

    public class TintToggle : PluginDynamicCommand
    {
        private Boolean _tintToggled = false;
        private readonly String _imageResourcePathOn;
        private readonly String _imageResourcePathOff;

        public TintToggle() : base(displayName: "Tint Switch", description: null, groupName: "Switches")
        {
            this._imageResourcePathOn = PluginResources.FindFile("tintOn.png");
            this._imageResourcePathOff = PluginResources.FindFile("tintOff.png");
        }

        protected override void RunCommand(String actionParameter)
        {
            this._tintToggled = !this._tintToggled;
            this.ActionImageChanged();
        }
        
        protected override BitmapImage GetCommandImage(String actionParameter, PluginImageSize imageSize)
        {
            var resourcePath = this._tintToggled ? this._imageResourcePathOn : this._imageResourcePathOff;
            return PluginResources.ReadImage(resourcePath);
        }
    }
}