# Japanese Translator (KDE Plasma, PyQt6)

- Run: `./run.sh` (builds `.venv` on first run). Launchers: `./install-launchers.sh`.
- Tests: `QT_QPA_PLATFORM=offscreen PYTHONPATH=. .venv/bin/python -m unittest discover -s tests`
- Code map and design notes are in `GUIDE.md` ("For developers").
- Log file: `~/.local/state/ujt-kde/ujt.log`. Never put API keys in the repo (`~/.config/ujt-kde/keys.env`).
- The old Windows WPF app and COSMIC edition live in `##Archive##/UJT-legacy-materials-2026-10-12`.
