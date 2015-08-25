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
        self.file.write(struct.pack('!I', 1 + len(payload)) + bytes([id]))
        self.file.write(payload)
        self.file.flush()

    def do_recv(self):
        length, = struct.unpack('!I', self.file.read(4))
        print('recv', length)
        response = self.file.read(length)
        if len(response) != length:
            raise EOFError('read %d, expected %d' % (len(response), length))

        print('response', repr(response)[:80])
        type = response[0]
        payload = response[1:]

        return type, payload
