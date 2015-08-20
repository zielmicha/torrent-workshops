import struct

protocol_header = b'\x13BitTorrent protocol'
header_reserved = b'\0\0\0\0\0\0\0\0'

message_types = {
    'bitfield': 5,
    'cancel': 8,
    'choke': 0,
    'have': 4,
    'interested': 2,
    'not interested': 3,
    'piece': 7,
    'request': 6,
    'unchoke': 1
}

class PeerBase(object):
    def send(self, id, payload):
        print('send %d %r' % (id, payload))
        self.file.write(struct.pack('!I', 1 + len(payload)) + bytes([id]))
        self.file.write(payload)
        self.file.flush()
