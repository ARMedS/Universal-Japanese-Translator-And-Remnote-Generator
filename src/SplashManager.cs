using System;
using System.IO;
using System.Net.Http;
using System.Text.Json;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Media.Effects;
using System.Windows.Threading;

// Use explicit namespaces to avoid ambiguity
using WPFPoint = System.Windows.Point;
using WPFColor = System.Windows.Media.Color;
using WPFOrientation = System.Windows.Controls.Orientation;

namespace UGTLive
{
    public class SplashManager
    {
        private static SplashManager? _instance;
        public static SplashManager Instance => _instance ??= new SplashManager();

        private Window? _splashWindow;
        private TextBlock? _versionTextBlock;
        private TextBlock? _statusTextBlock;
        
        // Event to notify when splash screen is closed
        public event EventHandler? SplashClosed;
        
        public const double CurrentVersion = 0.28;

        public void ShowSplash()
        {
            System.Windows.Application.Current.Dispatcher.Invoke(() =>
            {
                _splashWindow = new Window
                {
                    Title = "Universal Game Translator Live",
                    Width = 550,
                    Height = 350,
                    WindowStyle = WindowStyle.None,
                    ResizeMode = ResizeMode.NoResize,
                    WindowStartupLocation = WindowStartupLocation.CenterScreen,
                    Background = new SolidColorBrush(Colors.White),
                    AllowsTransparency = true,
                    Topmost = true
                };

                // Create a border with drop shadow and rounded corners for visual appeal
                Border mainBorder = new Border
                {
                    CornerRadius = new CornerRadius(12),
                    BorderBrush = new SolidColorBrush(WPFColor.FromRgb(100, 149, 237)), // Cornflower blue
                    BorderThickness = new Thickness(2),
                    Padding = new Thickness(20),
                    Background = new LinearGradientBrush
                    {
                        StartPoint = new WPFPoint(0, 0),
                        EndPoint = new WPFPoint(1, 1),
                        GradientStops = new GradientStopCollection
                        {
                            new GradientStop(Colors.White, 0.0),
                            new GradientStop(WPFColor.FromRgb(240, 248, 255), 1.0) // AliceBlue
                        }
                    },
                    Effect = new DropShadowEffect
                    {
                        Color = Colors.Black,
                        Direction = 315,
                        ShadowDepth = 10,
                        BlurRadius = 15,
                        Opacity = 0.6
                    }
                };
                
                Grid grid = new Grid();
                grid.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) });
                grid.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
                grid.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });

                // App Icon with reflection effect
                StackPanel iconPanel = new StackPanel
                {
                    Orientation = WPFOrientation.Vertical,
                    HorizontalAlignment = System.Windows.HorizontalAlignment.Center,
                    VerticalAlignment = VerticalAlignment.Center
                };


                System.Uri iconUri = new System.Uri("pack://application:,,,/media/Icon1.ico", UriKind.RelativeOrAbsolute);

                IconBitmapDecoder decoder = new IconBitmapDecoder(
                    iconUri,
                    BitmapCreateOptions.None,
                    BitmapCacheOption.OnLoad);

                // grab the biggest slice (or pick an exact size)
                BitmapSource bigFrame = decoder.Frames
                    .OrderByDescending(f => f.PixelWidth)   // 256 × 256 first
                    .First();

                // Main icon
                System.Windows.Controls.Image appIcon = new System.Windows.Controls.Image
                {
                    Source = bigFrame,
                    Width = 180,
                    Height = 180,
                    VerticalAlignment = VerticalAlignment.Center,
                    HorizontalAlignment = System.Windows.HorizontalAlignment.Center,
                    Effect = new DropShadowEffect
                    {
                        Color = Colors.Black,
                        Direction = 320,
                        ShadowDepth = 3,
                        BlurRadius = 5,
                        Opacity = 0.4
                    }
                };
                iconPanel.Children.Add(appIcon);
                
                Grid.SetRow(iconPanel, 0);
                grid.Children.Add(iconPanel);

                // Version Text
                _versionTextBlock = new TextBlock
                {
                    Text = $"Universal Game Translator Live V{CurrentVersion} by Seth A. Robinson",
                    FontSize = 16,
                    FontWeight = FontWeights.SemiBold,
                    Margin = new Thickness(0, 10, 0, 10),
                    HorizontalAlignment = System.Windows.HorizontalAlignment.Center,
                    Foreground = new SolidColorBrush(WPFColor.FromRgb(30, 30, 110))
                };
                Grid.SetRow(_versionTextBlock, 1);
                grid.Children.Add(_versionTextBlock);

                // Status Text
                _statusTextBlock = new TextBlock
                {
                    Text = "Checking latest version...",
                    FontSize = 12,
                    FontStyle = FontStyles.Italic,
                    Margin = new Thickness(0, 0, 0, 10),
                    HorizontalAlignment = System.Windows.HorizontalAlignment.Center,
                    Foreground = new SolidColorBrush(WPFColor.FromRgb(90, 90, 90))
                };
                Grid.SetRow(_statusTextBlock, 2);
                grid.Children.Add(_statusTextBlock);

                // Set the grid as content of the border
                mainBorder.Child = grid;
                
                // Set the border as content of the window
                _splashWindow.Content = mainBorder;
                _splashWindow.Show();

                CloseSplashAfterDelay(0); //instantly close for our purposes
            });
        }





        private void CloseSplashAfterDelay(int delay)
        {
            Task.Delay(delay).ContinueWith(_ =>
            {
                CloseSplash();
            });
        }

        private void CloseSplash()
        {
            System.Windows.Application.Current.Dispatcher.Invoke(() =>
            {
                _splashWindow?.Close();
                _splashWindow = null;
                
                // Raise the SplashClosed event
                SplashClosed?.Invoke(this, EventArgs.Empty);
            });
        }
    }
}