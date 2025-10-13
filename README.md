Universal Game Translator Live (UGTLive) - Modified Version 

This is a modified version of Seth Robinson's original UGTLive project (original:
https://github.com/sethrobinson/ugtlive). The core focus remains real-time translation for visual novels and
games, but major changes have been implemented to replace traditional OCR-based text extraction with direct API
calls to visual Large Language Models (LLMs). This eliminates OCR dependencies (Windows OCR and EasyOCR Python
server) and simplifies the workflow: images are sent directly to LLMs for text recognition and translation in one
step. Flashcard generation is retained and integrated with the new LLM-based output. Audio processing features
(listen/transcription) have been completely removed to streamline for visual translation only. 


Tips:

• Use vision-capable models (e.g., google/gemini-2.5-flash-preview via OpenRouter) 

## Settings Window

Opens at Height=1200, Width=500. Sections:

• Translation Service: Provider selection and API key. Defaults to OpenRouter.
• Prompt Template: LLM instructions for visual translation.
• Flashcard Generation: Template editing (e.g., for Anki JSON output).
• Language: Source/target (swap button). Defaults: ja-en.
• Context: Max sentences (3 default), min size (20 chars).
• Block Detection: Scale (5.0), settle time (0.5s), max settle (1.0s).
• ChatBox: Font, size, colors, history size. Minimum text size (2 chars).

## License

MIT License. See LICENSE.md /LICENSE.md.

## Credits

• Original creator: Seth Robinson (@sethrobinson on GitHub).
• Modifications: Shift to API-driven visual LLM translation, flashcard focus, removal of local OCR/audio. Built
upon Seth's foundation for streamlined visual novel support.