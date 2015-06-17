import sys
import struct

file = sys.stdin.buffer
print('read:', file.read(1 + 0x13 + 8), file=sys.stderr)
print('info hash:', file.read(20), file=sys.stderr)
print('peer id:', file.read(20), file=sys.stderr)

chunks = []

while True:
    d = file.read(4)
    if not d:
        break
    length, = struct.unpack('!I', d)
    data = file.read(length)
    if data[0] == 0x7:
        # piece
        i, j = struct.unpack('!II', data[1:9])
        chunks.append((i, j, data[9:]))

chunks.sort()
for i, j, bin in chunks:
    sys.stdout.buffer.write(bin)
sys.stdout.buffer.flush()
