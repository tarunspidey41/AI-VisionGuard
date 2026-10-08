AI VisionGuard - Python 3.14 note

This build is intended for Windows + regular CPython 3.14 (x64).
Do NOT create the environment with Python 3.14t/free-threaded.

Why?
The YOLO stack includes native packages such as PyTorch and Polars. Regular
CPython 3.14 has compatible Windows wheels. If a free-threaded 3.14t
interpreter is used, pip may fail to find a matching Polars runtime wheel and
fall back to compiling Rust code with Cargo, producing errors such as:

  Failed to build polars-runtime-32
  maturin failed
  Cargo build finished with exit code 101

Recommended commands:

  py -0p
  py -3.14 -m venv .venv
  .venv\Scripts\activate
  python --version
  python -m pip install --upgrade pip
  python -m pip install --only-binary=:all: -r requirements.txt
  python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

The included start_windows.bat performs these checks automatically.

If your machine has both Python 3.14 and Python 3.14t, the command
"py -3.14" intentionally selects regular CPython 3.14.
