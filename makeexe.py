"""
Programmatically call PyInstaller to build the executable
"""

import PyInstaller.__main__

PyInstaller.__main__.run([
    'map2prop.py',
    '--onefile',
    '-c',
    '-i', 'm2p.ico',
    '-n', 'Map2Prop',
    '--version-file', 'version_win.txt',
])
