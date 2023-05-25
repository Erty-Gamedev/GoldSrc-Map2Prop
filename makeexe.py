# -*- coding: utf-8 -*-
"""
Created on Wed May 24 17:22:48 2023

@author: Erty
"""

import PyInstaller.__main__

PyInstaller.__main__.run([
    'obj2goldsmd.py',
    '--onefile',
    '-c',
    '-i', 'o2gs.ico',
    '-n', 'Obj2GoldSmd',
])
