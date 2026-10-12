# Universal Japanese Translator and RemNote Generator

**Read Japanese games and visual novels as you play, and turn what you meet into flashcards, without leaving the game.**

Put a see-through frame over the text you cannot read. Press one key. Seconds later
you have the Japanese split into clickable words with their meanings, and, when you
want them, ready-made [RemNote](https://www.remnote.com) flashcards.

![The capture frame sitting over a visual novel](media/kde-capture-frame.png)

![The Reader: clickable words, meanings and a generated flashcard](media/kde-reader.png)

## What it does for you

1. **Frame the text.** Drag the frame over the dialogue box, a menu or a name plate.
2. **Press Capture** (Shift+S). Only the area inside the frame is sent to a vision AI model.
3. **Read.** The Reader shows the sentence as clickable words. Click a word for its
   meaning, click again for the romaji.
4. **Learn.** The first click on a word also writes a flashcard: meaning, kanji
   breakdown with radicals, and a memory hook. **Export** copies them all for RemNote.

## Why it is pleasant to use

- **It stays out of the way.** The inside of the frame is *click-through*, so you keep
  pressing the game's own buttons right through it. The border and the whole toolbar
  fade down to almost invisible, and **Hide** leaves just a Capture button.
- **No OCR to install.** Pictures go straight to a vision-capable model through
  [OpenRouter](https://openrouter.ai), so there is no OCR engine, local server or
  language pack to set up. Bring an API key and go.
- **Fast and exact.** The capture takes about 15 ms and is pixel-exact on any monitor,
  and the interface never freezes while the model thinks.
- **Snip anything.** Drag a box around any other part of the screen, such as a button
  off to one side, and just that area goes through the same translation flow.
- **Learn as you read.** Flashcards come from the words you actually clicked, in the
  context of the game you are playing.
- **Easy to diagnose.** Everything it does is written to a rotating log file, with a
  Log window and a Copy-all button.

## Get started

It is a Linux app for **KDE Plasma on X11**. Full instructions, the button-by-button
guide, keyboard shortcuts and troubleshooting are in the guide:

**[Read the guide](GUIDE.md)**

```bash
./run.sh                # first run builds a .venv
./install-launchers.sh   # adds "Japanese Translator" to the Super menu
```

Add your OpenRouter key in Settings and you are ready.

## The original Windows app

This project began as a modified version of Seth Robinson's
[UGTLive](https://github.com/sethrobinson/ugtlive) for Windows: real-time game
translation, changed to send images straight to vision LLMs instead of using OCR and
with flashcard generation added. That WPF/C# app is no longer in the working tree (it remains in the git history);
the Linux KDE edition above is the actively developed one.

## License and credits

MIT License. See [LICENSE.md](LICENSE.md).

- Original UGTLive creator: Seth A. Robinson ([@sethrobinson](https://github.com/sethrobinson)).
- This fork: API-driven visual LLM translation, flashcard focus, and the Linux KDE rewrite.
