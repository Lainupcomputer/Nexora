# Nexora Engine — Installation Guide

Nexora Engine is a 2D game engine for Python built on top of `pygame-ce`.

Nexora is designed to take advantage of Python 3.13's **free-threaded / No-GIL mode** for true parallel worker threads.

> **Important:** The installation described below uses a custom source build of `pygame-ce` because the standard PyPI Windows wheels may not provide a compatible `cp313t` build.

---

## 1. Requirements

### Windows

You need:

- Windows 10 or newer
- Git
- Python 3.13 Free-Threading
- Visual Studio 2022 Build Tools
- MSVC C/C++ compiler
- Windows SDK
- PowerShell or Command Prompt
- Internet connection

---

# 2. Install Python 3.13 Free-Threading

Nexora requires a Python build that supports free-threading.

Verify your Python installation:

```powershell
python --version
````

Then:

```powershell
python -c "import sys, sysconfig; print(sys.version); print('GIL:', sys._is_gil_enabled()); print('ABI:', sysconfig.get_config_var('SOABI'))"
```

A correct free-threaded installation should report an ABI similar to:

```text
cp313t-win_amd64
```

The GIL should be disabled when running with:

```powershell
python -Xgil=0
```

Verify:

```powershell
python -Xgil=0 -c "import sys; print('GIL:', sys._is_gil_enabled())"
```

Expected:

```text
GIL: False
```

---

# 3. Install Visual Studio Build Tools

`pygame-ce` must currently be compiled from source for the `cp313t` environment.

Install **Visual Studio 2022 Build Tools**.

During installation, select:

```text
Desktop development with C++
```

Make sure the following components are installed:

* MSVC C++ build tools
* Windows SDK
* C++ build tools

After installation, open:

```text
Developer Command Prompt for VS 2022
```

Use the **x64** environment.

Verify the compiler:

```cmd
where cl
```

You should see an x64 MSVC compiler path.

Then run:

```cmd
cl
```

The compiler should report an x64 target.

> **Important:** Use an x64 compiler. Do not build the extension with an x86 compiler when using 64-bit Python.

---

# 4. Clone Nexora Engine

Clone or download the Nexora Engine repository.

Example:

```powershell
cd "C:\Users\<username>\Desktop"
```

Then enter the project:

```powershell
cd "Nexora Engine"
```

The project should look similar to:

```text
Nexora Engine/
├── .venv/
├── examples/
├── nexora/
├── tests/
├── pyproject.toml
└── README.md
```

---

# 5. Create a Virtual Environment

Create the virtual environment:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

Your terminal should now look similar to:

```text
(.venv) PS C:\Users\<username>\Desktop\Nexora Engine>
```

Verify Python:

```powershell
python --version
```

Check the ABI:

```powershell
python -c "import sysconfig; print(sysconfig.get_config_var('SOABI'))"
```

Expected:

```text
cp313t-win_amd64
```

---

# 6. Install pygame-ce Build Dependencies

Activate the Nexora virtual environment first.

Then install the required build tools:

```powershell
python -m pip install --upgrade pip
python -m pip install setuptools wheel packaging
python -m pip install meson ninja meson-python cython
```

These packages are required to compile `pygame-ce` from source.

---

# 7. Clone pygame-ce

Move to the directory where you want to keep the pygame-ce source:

```powershell
cd "C:\Users\<username>\Desktop"
```

Clone the repository:

```powershell
git clone https://github.com/pygame-community/pygame-ce.git
```

Enter the source directory:

```powershell
cd pygame-ce
```

Verify the repository:

```powershell
git status
```

---

# 8. Compile pygame-ce for Python 3.13 Free-Threading

Make sure the Nexora virtual environment is still active.

From the `pygame-ce` source directory, run:

```powershell
python -m pip install .
```

This compiles pygame-ce against the currently active Python installation.

For a correct free-threaded Python installation, the resulting wheel should contain:

```text
cp313-cp313t-win_amd64
```

For example:

```text
pygame_ce-3.0.0.dev1-cp313-cp313t-win_amd64.whl
```

The important part is:

```text
cp313t-win_amd64
```

This indicates:

* Python 3.13
* Free-threading ABI
* Windows
* 64-bit AMD64

A successful installation should finish with something similar to:

```text
Successfully installed pygame-ce-3.0.0.dev1
```

---

# 9. Verify pygame-ce

Return to the Nexora project:

```powershell
cd "C:\Users\<username>\Desktop\Nexora Engine"
```

Run:

```powershell
python -Xgil=0 -c "import pygame, sys, sysconfig; print('pygame:', pygame.version.ver); print('GIL:', sys._is_gil_enabled()); print('ABI:', sysconfig.get_config_var('SOABI')); print('pygame:', pygame.__file__)"
```

Expected output should look similar to:

```text
pygame: 3.0.0.dev1
GIL: False
ABI: cp313t-win_amd64
pygame: C:\Users\<username>\Desktop\Nexora Engine\.venv\Lib\site-packages\pygame\__init__.py
```

---

# 10. Install Nexora Engine

Make sure you are in the Nexora Engine directory:

```powershell
cd "C:\Users\<username>\Desktop\Nexora Engine"
```

Activate the virtual environment if necessary:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install Nexora in editable mode:

```powershell
python -m pip install -e .
```

A successful installation should report:

```text
Successfully installed nexora-engine-0.1.0
```

---

# 11. Verify Nexora

Run:

```powershell
python -Xgil=0 -c "import nexora; print('Nexora:', nexora.__version__)"
```

Expected:

```text
Nexora: 0.1.0
```

---

# 12. Run the Hello World Example

Nexora should currently be launched with Python's free-threading mode enabled:

```powershell
python -Xgil=0 examples\hello_world.py
```

A Nexora window should open.

The Hello World example verifies:

* Nexora initialization
* Window creation
* Game loop
* Event handling
* Updating
* Rendering
* FPS tracking
* pygame integration
* No-GIL execution

Press:

```text
ESC
```

to close the application.

---

# 13. Test No-GIL Parallelism

Nexora uses free-threading to allow CPU-heavy tasks to execute in parallel.

Run the No-GIL stress test:

```powershell
cd tests
python -Xgil=0 test_nogil_stress.py
```

A successful test should show something similar to:

```text
GIL vor pygame: False
pygame: 3.0.0.dev1
GIL nach pygame: False

Worker: 8
Tasks pro Worker: 4
Tasks gesamt: 32

Alle Tasks abgeschlossen: True
GIL am Ende: False

No-GIL Stress-Test erfolgreich!
```

The exact execution time depends on the CPU.

The test verifies that:

1. Python starts without the GIL.
2. pygame can be loaded without enabling the GIL when started with `-Xgil=0`.
3. Multiple Python worker threads can execute CPU-heavy tasks.
4. pygame remains active in the main thread.
5. The GIL remains disabled.

---

# 14. Development Workflow

When opening a new terminal, activate the virtual environment:

```powershell
cd "C:\Users\<username>\Desktop\Nexora Engine"
.\.venv\Scripts\Activate.ps1
```

Run Nexora:

```powershell
python -Xgil=0 examples\hello_world.py
```

Run the No-GIL stress test:

```powershell
python -Xgil=0 tests\test_nogil_stress.py
```

Because Nexora is installed using editable mode:

```powershell
python -m pip install -e .
```

you normally do not need to reinstall Nexora after changing its Python source files.

---

# 15. Troubleshooting

## `pygame-ce` downloads a `.tar.gz`

If pip downloads a source archive instead of a wheel, this means that pip could not find a compatible pre-built wheel.

For the free-threaded Python environment, this is expected.

Build pygame-ce locally:

```powershell
cd "C:\Users\<username>\Desktop\pygame-ce"
python -m pip install .
```

---

## `cl` is not recognized

If you receive:

```text
'cl' is not recognized
```

you are probably using a normal PowerShell or Command Prompt without the Visual Studio compiler environment.

Open:

```text
Developer Command Prompt for VS 2022
```

using an x64 environment.

Then verify:

```cmd
where cl
```

---

## Wrong compiler architecture

Nexora uses 64-bit Python.

Check Python:

```powershell
python -c "import platform; print(platform.machine())"
```

Expected:

```text
AMD64
```

The MSVC compiler should also target x64.

---

## GIL becomes enabled

Check:

```powershell
python -Xgil=0 -c "import sys; print(sys._is_gil_enabled())"
```

Expected:

```text
False
```

Always use:

```powershell
python -Xgil=0
```

when running Nexora in the intended free-threaded configuration.

If a native extension enables the GIL, that extension may not yet be fully compatible with free-threaded Python.

Do **not** simply change a native module's GIL declaration to `Py_MOD_GIL_NOT_USED`. A module should only declare itself free-threading-safe after its native code has actually been verified to be safe.

---

# 16. Verified Configuration

The following configuration has been tested successfully with Nexora:

```text
Python:
3.13.0 experimental free-threading build

Architecture:
AMD64

Python ABI:
cp313t-win_amd64

pygame-ce:
3.0.0.dev1

Nexora Engine:
0.1.0

Compiler:
MSVC 2022

Compiler Architecture:
x64
```

The pygame-ce source build produced:

```text
pygame_ce-3.0.0.dev1-cp313-cp313t-win_amd64.whl
```

A No-GIL stress test successfully ran:

```text
8 workers
32 parallel tasks
GIL: False
pygame active in main thread
```

---

# 17. Nexora Threading Architecture

Nexora is designed around a main-thread / worker-thread architecture.

SDL and pygame operations that require the main thread remain on the main thread.

CPU-heavy operations can be distributed to worker threads.

Conceptually:

```text
                         NEXORA ENGINE
                              |
                +-------------+-------------+
                |                           |
           MAIN THREAD                WORKER THREADS
                |                           |
        +-------+-------+           +-------+-------+
        |       |       |           |       |       |
      pygame  Input  Render        AI    Physics  Tasks
      Events  Window  Audio       Logic  Pathfind  CPU
```

This allows Nexora to use Python 3.13 free-threading for real parallel execution while keeping SDL-related operations in the appropriate thread.

---

# 18. Important Notes

Nexora currently targets Python 3.13 free-threading.

Free-threaded Python is different from a standard CPython build. Native extensions must explicitly support the free-threaded ABI and must be safe for execution without the GIL.

Nexora therefore uses a custom source build of pygame-ce rather than assuming that a normal Python 3.13 wheel is sufficient.

Always test the environment with:

```powershell
python -Xgil=0
```

before developing or benchmarking Nexora's parallel systems.


## License

See the project's `LICENSE` file for licensing information.

````
