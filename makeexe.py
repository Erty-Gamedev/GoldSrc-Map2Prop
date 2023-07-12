# -*- coding: utf-8 -*-
"""
Created on Wed May 24 17:22:48 2023

@author: Erty
"""

import PyInstaller.__main__

PyInstaller.__main__.run([
    'map2prop.py',
    '--onefile',
    '-c',
    '-i', 'm2p.ico',
    '-n', 'Map2Prop',
])
