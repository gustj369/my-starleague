"""cx_Freeze setup for 마이 스타리그"""
from cx_Freeze import setup, Executable

build_exe_options = {
    "packages": ["PyQt6", "sqlite3", "core", "database", "ui"],
    "excludes": ["tkinter", "matplotlib", "numpy", "pandas"],
    "include_files": [("fonts/", "fonts/")],
    "silent_level": 1,
}

setup(
    name="StarLeague",
    version="1.0",
    options={"build_exe": build_exe_options},
    executables=[
        Executable(
            script="main.py",
            base="gui",
            target_name="StarLeague.exe",
        )
    ],
)
