# Persistent Assistant v3 – Development Plan

## ✅ Phase 0: Foundation Setup
| Step | Description |
|------|-------------|
| 0.1  | ✅ Define root project directory layout (`C:\_Repos\PersistentAssistant`) |
| 0.2  | ✅ Initialize new Git repository |
| 0.3  | ✅ Create `.venv`, requirements, and `.gitignore` |
| 0.4  | ✅ Lock initial Python + PyQt6 environment |

## ✅ Phase 1: MVP Interface Foundations
| Step  | Description |
|-------|-------------|
| 1.1   | ✅ Create `main.py` with minimal startup logic |
| 1.2   | ✅ Create `main_window.py` with tabbed layout |
| 1.3   | ✅ Create `input_tab.py` with editable multi-line textbox |
| 1.4   | ✅ Create `prompt_tab.py` with editable prompt + copy button |
| 1.5   | ✅ Create `chat_tab.py` with embedded ChatGPT browser pane |
| 1.6   | ✅ Create `response_tab.py` with clipboard paste + log button |
| 1.7   | ✅ Implement autosave on paste and logging to YAML |
| 1.8   | ✅ Add visual confirmation of logging (status bar or dialog) |
| 1.9   | ✅ Add full file headers for all Python source files |
| 1.10  | ✅ Create `prompt_formatter.py` and wire into Format Prompt button |
| 1.11  | ✅ Simulate AI response by copying prompt to response tab |
| 1.12  | 🔜 Add "Copy All as YAML" button to log input, prompt, and response |