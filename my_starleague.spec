# -*- mode: python ; coding: utf-8 -*-
block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('fonts/*.ttf', 'fonts'),
    ],
    hiddenimports=[
        'PyQt6', 'PyQt6.QtWidgets', 'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.sip',
        'sqlite3',
        'core.balance', 'core.builds', 'core.grade', 'core.growth_events',
        'core.match', 'core.player_data', 'core.season_events', 'core.tournament',
        'database.db', 'database.seed_data', 'database.slot_manager',
        'ui.bracket_screen', 'ui.final_result', 'ui.font_loader',
        'ui.history_screen', 'ui.main_menu', 'ui.match_prep', 'ui.match_screen',
        'ui.player_manager', 'ui.player_profile_dialog', 'ui.player_select',
        'ui.ranking_screen', 'ui.result_screen', 'ui.season_news_dialog',
        'ui.shop_screen', 'ui.simulation_screen', 'ui.slot_select_screen',
        'ui.styles', 'ui.team_setup', 'ui.widgets',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'pandas', 'scipy'],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='StarLeague',
    debug=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
)
