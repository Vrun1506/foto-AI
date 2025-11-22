namespace Loupedeck.FotoPlugin
{
    using System;

    public class ContrastToggle : PluginDynamicCommand
    {
        private Boolean _contrastToggled = false;
        private readonly String _imageResourcePathOn;
        private readonly String _imageResourcePathOff;

        private readonly String toggleId;

        public ContrastToggle() : base(displayName: "Contrast Switch", description: null, groupName: "Switches")
        {
            this._imageResourcePathOn = PluginResources.FindFile("contrastOn.png");
            this._imageResourcePathOff = PluginResources.FindFile("contrastOff.png");
            this.toggleId = "contrastToggle";
        }

        protected override void RunCommand(String actionParameter)
        {
            this._contrastToggled = !this._contrastToggled;
            this.ActionImageChanged();
        }
        
        protected override BitmapImage GetCommandImage(String actionParameter, PluginImageSize imageSize)
        {
            var resourcePath = this._contrastToggled ? this._imageResourcePathOn : this._imageResourcePathOff;
            return PluginResources.ReadImage(resourcePath);
        }
    }
}