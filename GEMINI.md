# UGTLive Project Overview

This document provides a high-level overview of the Universal Game Translator Live (UGTLive) project, its architecture, and development conventions.

## Project Purpose

UGTLive is a Windows application designed for real-time translation of on-screen text, primarily aimed at video games. It works by capturing a user-selected portion of the screen, performing Optical Character Recognition (OCR) to extract text, and then sending that text to a Large Language Model (LLM) for translation. The translated text is then displayed as an overlay on the screen.

## Architecture

The project follows a client-server architecture:

*   **Frontend (C# WPF):** The main user interface is a .NET 8 WPF application. It is responsible for:
    *   Providing the user interface for settings and controls.
    *   Capturing the screen.
    *   Displaying the translated text in an overlay window.
    *   Communicating with the backend OCR server and the selected translation service.

*   **Backend (Python):** A local Python server handles the OCR process.
    *   It uses the `EasyOCR` library to extract text from the images sent by the C# client.
    *   It communicates with the C# client over a TCP socket.

*   **Translation Services:** The application supports multiple translation backends, abstracted through the `ITranslationService` interface. This allows for easy extension with new translation services. The currently supported services are:
    *   Gemini
    *   ChatGPT
    *   Ollama
    *   Google Translate

## Building and Running

### Prerequisites

*   Visual Studio 2022 with .NET 8 SDK.
*   Miniconda or Anaconda.

### Build Process

The C# application can be built using the .NET CLI:

```sh
dotnet build UGTLive.csproj
```

The `BuildAndRun.bat` script automates the build and run process for a debug build.

### Running the Application

1.  **Set up the Python environment:** Run the `app\webserver\SetupServerCondaEnvNVidia.bat` script to create a Conda environment with the required Python dependencies. This only needs to be done once.
2.  **Start the OCR server:** Run the `app\webserver\RunServer.bat` script. This will start the Python server that listens for OCR requests from the C# application.
3.  **Run the main application:** Execute the `ugtlive_debug.exe` (for debug builds) or `ugtlive.exe` (for release builds) from the `app` directory.

## Development Conventions

*   **C#:** The C# code follows standard .NET coding conventions. It makes extensive use of `async/await` for non-blocking I/O operations. The application logic is primarily orchestrated by the singleton `Logic` class.
*   **Python:** The Python server is a standard socket server. It uses the `logging` module for logging and is designed to be simple and efficient.
*   **Configuration:** Application settings, including API keys for translation services, are managed by the `ConfigManager` class and stored in text files within the `app` directory (e.g., `gemini_config.txt`).
*   **Extensibility:** The use of the `ITranslationService` interface and the `TranslationServiceFactory` makes it straightforward to add support for new translation services.
