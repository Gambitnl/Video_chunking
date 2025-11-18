import os
from pathlib import Path

# Common Google Drive locations
paths = [
    r'C:\Users\Gambit\Google Drive',
    r'G:\My Drive',
    r'G:',
    Path.home() / 'Google Drive',
]

for p in paths:
    if os.path.exists(p):
        print(p)
        break
else:
    print('NotFound')
