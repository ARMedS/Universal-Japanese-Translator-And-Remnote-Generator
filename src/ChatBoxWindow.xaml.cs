using System;
using System.Collections.Generic;
using System.Windows;
using System.Windows.Controls; // For ToolTip
using System.Windows.Documents;
using System.Windows.Input;
using System.Windows.Media;

namespace UGTLive
{
    public partial class ChatBoxWindow : Window
    {
        public static ChatBoxWindow? Instance { get; private set; }

        public ChatBoxWindow()
        {
            InitializeComponent();
            Instance = this;
            this.DataContext = this;
            LoadWindowPlacement();
        }

        private void LoadWindowPlacement()
        {
            var (top, left, height, width) = ConfigManager.Instance.LoadWindowPlacement(
                this.GetType().Name, this.Top, this.Left, this.Height, this.Width);
            this.Top = top;
            this.Left = left;
            this.Height = height;
            this.Width = width;
        }

        private enum DisplayState
        {
            Japanese,
            English,
            Romaji
        }

        private class TextChunk
        {
            public string Japanese { get; set; } = "";
            public string English { get; set; } = "";
            public string Romaji { get; set; } = "";
            public DisplayState CurrentState { get; set; } = DisplayState.Japanese;
            public Run? InfoRun { get; set; }
            public bool FlashcardCreated { get; set; } = false;
        }

        private string _fullSentence = "";

        public void UpdateWithTextObjects(List<TextObject> textObjects, string fullSentence)
        {
            if (!Dispatcher.CheckAccess())
            {
                Dispatcher.Invoke(() => UpdateWithTextObjects(textObjects, fullSentence));
                return;
            }

            _fullSentence = fullSentence;

            Paragraph paragraph = new Paragraph();

            foreach (var textObject in textObjects)
            {
                if (!string.IsNullOrEmpty(textObject.Text))
                {
                    var chunk = new TextChunk
                    {
                        Japanese = textObject.Text,
                        English = textObject.TextTranslated,
                        Romaji = textObject.TextRomaji
                    };

                    Run japaneseRun = new Run(chunk.Japanese);
                    japaneseRun.Cursor = System.Windows.Input.Cursors.Hand;
                    japaneseRun.MouseLeftButtonDown += Run_MouseLeftButtonDown;

                    Run infoRun = new Run("")
                    {
                        Foreground = new SolidColorBrush(Colors.LightGray),
                        FontStyle = FontStyles.Italic
                    };

                    chunk.InfoRun = infoRun;
                    japaneseRun.Tag = chunk;

                    paragraph.Inlines.Add(japaneseRun);
                    paragraph.Inlines.Add(infoRun);
                    paragraph.Inlines.Add(new Run(" ")); // Add a space between chunks
                }
            }

            InteractiveTextDisplay.Document.Blocks.Clear();
            InteractiveTextDisplay.Document.Blocks.Add(paragraph);
            ChatScrollViewer.ScrollToBottom();
        }

        private void Run_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
        {
            if (sender is Run run && run.Tag is TextChunk chunk && chunk.InfoRun != null)
            {
                // --- Flashcard Logic ---
                if (!chunk.FlashcardCreated)
                {
                    Logic.Instance.GenerateFlashcardAsync(chunk.Japanese, chunk.English, chunk.Romaji, _fullSentence);
                    chunk.FlashcardCreated = true;
                }

                // --- Toggle Logic ---
                // Cycle through states
                chunk.CurrentState = (DisplayState)(((int)chunk.CurrentState + 1) % 3);

                switch (chunk.CurrentState)
                {
                    case DisplayState.Japanese:
                        chunk.InfoRun.Text = "";
                        break;
                    case DisplayState.English:
                        chunk.InfoRun.Text = $" ({chunk.English})";
                        break;
                    case DisplayState.Romaji:
                        chunk.InfoRun.Text = $" ({chunk.English} / {chunk.Romaji})";
                        break;
                }
            }
        }

        public void AppendToFlashcardOutput(string text)
        {
            if (!Dispatcher.CheckAccess())
            {
                Dispatcher.Invoke(() => AppendToFlashcardOutput(text));
                return;
            }

            // Clear the placeholder text if it's there
            var paragraph = FlashcardOutputDisplay.Document.Blocks.FirstBlock as Paragraph;
            if (paragraph != null)
            {
                var run = paragraph.Inlines.FirstInline as Run;
                if (run != null && run.Text == "Flashcard output will appear here...")
                {
                    FlashcardOutputDisplay.Document.Blocks.Clear();
                }
            }

            FlashcardOutputDisplay.AppendText(text + "\n\n");
            FlashcardOutputDisplay.ScrollToEnd();
        }

        private void ZoomInButton_Click(object sender, RoutedEventArgs e)
        {
            InteractiveTextDisplay.FontSize += 2;
            FlashcardOutputDisplay.FontSize += 2;
        }

        private void ZoomOutButton_Click(object sender, RoutedEventArgs e)
        {
            if (InteractiveTextDisplay.FontSize > 4)
            {
                InteractiveTextDisplay.FontSize -= 2;
            }
            if (FlashcardOutputDisplay.FontSize > 4)
            {
                FlashcardOutputDisplay.FontSize -= 2;
            }
        }

        private void Header_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
        {
            if (e.ChangedButton == MouseButton.Left)
            {
                this.DragMove();
            }
        }

        private void CloseButton_Click(object sender, RoutedEventArgs e)
        {
            this.Hide();
        }

        private async void ExportButton_Click(object sender, RoutedEventArgs e)
        {
            TextRange textRange = new TextRange(
                FlashcardOutputDisplay.Document.ContentStart,
                FlashcardOutputDisplay.Document.ContentEnd
            );

            System.Windows.Clipboard.SetText(textRange.Text);

            // Visual feedback
            var originalContent = ExportButton.Content;
            var originalBackground = ExportButton.Background;

            ExportButton.Content = "Copied!";
            ExportButton.Background = new SolidColorBrush(System.Windows.Media.Color.FromRgb(50, 200, 50)); // Light green

            await System.Threading.Tasks.Task.Delay(1500);

            ExportButton.Content = originalContent;
            ExportButton.Background = originalBackground;
        }

        private void Window_Closing(object sender, System.ComponentModel.CancelEventArgs e)
        {
            // Prevent the window from being disposed
            e.Cancel = true;
            this.Visibility = Visibility.Hidden;
            Console.WriteLine("ChatBox window hidden");
        }
    }
}
