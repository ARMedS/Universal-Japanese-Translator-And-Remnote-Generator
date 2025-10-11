# CRUSH.md – UGTLive Dev Quick Reference

## Build/Run
- dotnet build UGTLive.csproj
- BuildAndRun.bat (debug) / BuildAndRunRelease.bat (release)
- dotnet clean UGTLive.csproj

## Lint/Format/Analyze
- dotnet format whitespace
- dotnet format analyzers --severity info
- dotnet build -warnaserror

## Tests
- dotnet test
- dotnet test --filter "FullyQualifiedName~Namespace.ClassName.MethodName"  # single test
- dotnet test --filter "TestCategory=Unit"

## Code Style
- Imports: System.* first, then others; remove unused usings
- Formatting: 4-space indent, Allman braces, blank lines between visual elements
- Types: prefer explicit types over var (except obvious); nullable annotations where applicable
- Naming: PascalCase (classes/methods/properties/events), camelCase with leading _ for privates, interfaces start with I, singletons use Instance
- Properties: use GetX/SetX; bind directly to GUI elements when possible
- Error handling: avoid try/catch; check for null; log via LogManager.Instance.LogError; no secret values in logs
- Concurrency/UI: prefer async/await; use Dispatcher for UI updates; dispose bitmaps promptly
- Architecture: group functions into managers (ConfigManager, WindowsOCRManager, BlockDetectionManager); use factory for translators

## Cursor/Copilot Rules
- .cursor/rules/translation-workflow.mdc – end-to-end translation pipeline
- .cursor/rules/ugtlive-project-guide.mdc – project structure and versioning
- .cursor/rules/ui-ux-patterns.mdc – window patterns and shortcuts
- No Copilot rules detected (.github/copilot-instructions.md absent)

## Version Bump Checklist
- src/SplashManager.cs → update CurrentVersion
- media/latest_version_checker.json → update latest_version to match
