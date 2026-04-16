from cx_Freeze import setup, Executable

build_exe_options = {
    "packages": ["PyQt6", "sqlite3", "core", "database", "ui"],
    "excludes": ["tkinter", "matplotlib", "numpy", "pandas"],
    "include_files": [("fonts/", "fonts/")],
    "silent_level": 0,
}

setup(
    name="StarLeague_debug",
    version="1.0",
    options={"build_exe": build_exe_options},
    executables=[
        Executable(
            script="main.py",
            base=None,  # 콘솔 모드로 에러 보기
            target_name="StarLeague_debug.exe",
        )
    ],
)
