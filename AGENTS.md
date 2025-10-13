# UGTLive Agent Guidelines

## Build Commands
- **Debug build**: `dotnet build UGTLive.csproj`
- **Release build**: `dotnet build UGTLive.csproj -c Release`
- **Run debug**: `cd app && ugtlive_debug.exe`
- **Run release**: `cd app && ugtlive.exe`
- **No tests currently exist** - run manual testing via UI

## Code Style Guidelines

### Naming Conventions
- **Classes/Methods/Properties**: PascalCase
- **Private fields**: camelCase with underscore prefix (_fieldName)
- **Singletons**: Use "Instance" suffix

### Layout & Formatting
- **Indentation**: 4 spaces (no tabs)
- **Braces**: Allman style (braces on new lines)
- **Imports**: System namespaces first, grouped by namespace

### Properties & UI
- **Properties**: Use GetVariableName/SetVariableName pattern
- **UI Properties**: Direct Get/Set to GUI elements when possible
- **Avoid try/catch blocks** - check for null and log errors instead

### Error Handling
- Avoid try/catch blocks, check for null and write errors to console
- Use LogManager.Instance.LogError() for logging

## Cursor Rules (from .cursor/rules/)
- **translation-workflow.mdc**: Translation pipeline, API integration, OCR processing
- **ugtlive-project-guide.mdc**: Project structure, architecture, development guidelines
- **ui-ux-patterns.mdc**: Window management, UI design patterns, keyboard shortcuts

## Framework & Dependencies
- **Target**: .NET 8.0 Windows 10.0.22621.0+
- **UI**: WPF with Windows Forms integration
- **Key packages**: Microsoft.Windows.CsWinRT 2.0.6, NAudio 2.2.1