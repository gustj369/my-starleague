# -*- mode: python ; coding: utf-8 -*-
# 빌드 명령: pyinstaller my_starleague.spec
# PyQt6 플러그인 전체 수집 필수 (--collect-all PyQt6)
block_cipher = None

from PyInstaller.utils.hooks import collect_all

pyqt6_datas, pyqt6_binaries, pyqt6_hiddenimports = collect_all('PyQt6')

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=pyqt6_binaries,
    datas=pyqt6_datas + [
        ('fonts/*.ttf', 'fonts'),
        ('../image/*.png', 'image'),   # 선수 이미지 16장 번들
    ],
    hiddenimports=pyqt6_hiddenimports + [
        'sqlite3',
        'core.balance', 'core.builds', 'core.grade', 'core.growth_events',
        'core.match', 'core.player_data', 'core.season_events', 'core.tournament',
        'database.db', 'database.seed_data', 'database.slot_manager',
        'ui.bracket_screen', 'ui.final_result', 'ui.font_loader',
        'ui.history_screen', 'ui.main_menu', 'ui.match_prep', 'ui.match_screen',
        'ui.onboarding_dialog', 'ui.player_manager', 'ui.player_profile_dialog',
        'ui.player_select', 'ui.ranking_screen', 'ui.result_screen',
        'ui.season_news_dialog', 'ui.shop_screen', 'ui.simulation_screen',
        'ui.slot_select_screen', 'ui.styles', 'ui.team_setup', 'ui.widgets',
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
    name='LegendLeague',
    debug=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,      # GUI 전용, 콘솔창 없음
)
