# Keystroke Visualizer

A modern, customizable Python application to visualize real-time keyboard inputs. Built with **PyQt6** for the UI and **pynput** for global key detection, designed with a Windows 11-style dark theme.

## Features

* **Real-time Visualization**: Keys light up instantly as you press them.
* **Full Keyboard Support**: Includes standard ANSI layout, Function keys, Navigation cluster, and Numpad.
* **Custom Templates**: Create focused views showing only specific keys (e.g., WASD for gaming).
* **Drag & Drop Layouts**: In custom template mode, drag keys to arrange them exactly how you want.
* **Key Aliasing**: Rename keys in custom templates (e.g., map "Z" to "JUMP").
* **Always on Top**: Option to keep the overlay above other windows.
* **Persistence**: Automatically saves your window position, custom templates, and settings.

## Prerequisites

* **Python 3.10+**
* **uv** (Recommended for dependency management) or `pip`.

## Installation

1. **Initialize the project**:

    ```powershell
    # Create project directory if you haven't already
    mkdir key-visual
    cd key-visual

    # Initialize with uv
    uv init
    ```

2. **Install Dependencies**:

    ```powershell
    uv add PyQt6 pynput
    ```

## Usage

1. **Run the Application**:

    ```powershell
    uv run app.py
    ```

2. **Menus**:
    * **Settings**: Toggle "Always on Top".
    * **View**: Switch between "Full Keyboard" and your custom templates.
    * **View -> Add Custom Template...**: Create a new layout.

3. **Creating a Custom Layout**:
    * Click **View -> Add Custom Template...**.
    * Enter a name (e.g., "Gaming Mode").
    * Enter keys to include, separated by commas. You can rename keys using `=`.
        * *Example*: `W, A, S, D, SPACE, Z=JUMP, X=ATTACK`
    * The view will switch to your new template.
    * **Drag** the keys to arrange them on the canvas. The window size adjusts automatically.

## Project Structure

* `app.py`: Main application entry point and logic.
* `user_settings.json`: Stores user preferences and custom layouts (generated automatically).

## License

MIT
