#!/usr/bin/env python3
import os
import sys

# Bu dosyanın bulunduğu dizini bul
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_DIR)

# Python path'e ekle
sys.path.insert(0, SCRIPT_DIR)

print(f"Çalışma dizini: {SCRIPT_DIR}")
print(f"Python path: {sys.path[0]}")

# Şimdi app.py'yi import et
exec(open(os.path.join(SCRIPT_DIR, 'app.py')).read())
