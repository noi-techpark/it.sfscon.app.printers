import time
import os
import sys
import subprocess

TIMEOUT=10

os.system('cancel -a')
os.system('lpr /tmp/label.png')

start = time.time()

while True:
    os.system('lpstat | wc -l > /tmp/lpstat.txt')
    with open('/tmp/lpstat.txt') as f:
        l=int(f.read().strip())
    
    if l==0:
        break

    time.sleep(0.2)
    t = time.time() - start

    if t>TIMEOUT:
        sys.exit(-1)
        