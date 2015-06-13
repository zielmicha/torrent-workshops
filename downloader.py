import torrent
import bencode
import sys
import socket
import os
import struct
import bitarray

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

class Peer(object):
    def __init__(self, torrent, peer_id, addr):
        self.sock = socket.socket()
        self.addr = addr
        self.peer_id = peer_id
        self.torrent = torrent
        self.have_pieces = [False] * len(self.torrent.pieces)
        self.choked = True
        self.queued_requests = 0

    def init(self):
        self.sock.connect(self.addr)

        print('opened connection to', self.addr)
        self.file = self.sock.makefile('rwb', 0)
        self.file.write(protocol_header + header_reserved)
        self.file.write(self.torrent.info_hash)
        self.file.write(self.peer_id)
        self.file.flush()

        recv_header = self.file.read(20)
        if recv_header != protocol_header:
            raise ValueError('bad header: %r' % recv_header)

        extensions = self.file.read(8)
        print('extensions: %r' % extensions)

        other_hash = self.file.read(20)
        other_id = self.file.read(20)

        if other_hash != self.torrent.info_hash:
            raise ValueError()

        print('connected to %r' % other_id)

    def main(self):
        while True:
            self.maybe_send_requests()
            self.recv()

    def maybe_send_requests(self):
        if self.choked:
            return

        while self.queued_requests < 1:
            self.send_request(0, 0, 16 * 1024)

    def recv(self):
        length, = struct.unpack('!I', self.file.read(4))
        print('recv', length)
        response = self.file.read(length)
        if len(response) != length:
            print('response %r' % response)
            raise EOFError('read %d, expected %d' % (len(response), length))

        print('response', repr(response))
        type = response[0]
        payload = response[1:]

        if type == message_types['bitfield']:
            self.handle_bitfield(payload)
        elif type == message_types['have']:
            self.handle_have(payload)
        elif type == message_types['choke']:
            self.choked = True
        elif type == message_types['unchoke']:
            self.choked = False
            self.queued_requests = 0

    def handle_bitfield(self, payload):
        for i in range(len(self.have_pieces)):
            ch = i // 8
            bit = i % 8
            self.have_pieces[i] = (payload[ch] >> bit) & 1

    def handle_have(self, payload):
        id = struct.unpack('!I', payload)
        self.have_pieces[id] = True

    def send_request(self, index, begin, length):
        self.queued_requests += 1
        self.send(message_types['request'],
                  struct.pack('!III', index, begin, length))

    def send(self, id, payload):
        print('send %d %r' % (id, payload))
        self.file.write(struct.pack('!I', 1 + len(payload)) + bytes([id]))
        self.file.write(payload)

class Downloader(object):
    def __init__(self, torrent):
        self.torrent = torrent

        self.left = torrent.length
        self.peer_id = os.urandom(20)
        self.port = 6882
        self.uploaded = 0
        self.downloaded = 0

    def main(self):
        self.tracker_request()

        print(self.tracker_response)

    def tracker_request(self):
        self.tracker_response = torrent.tracker_request(
            self.torrent.announce, self.torrent.info_hash,
            peer_id=self.peer_id, port=self.port, uploaded=self.uploaded,
            downloaded=self.downloaded, left=self.left)

    def recv(self):
        length, = struct.unpack('!I', self.file.read(4))
        print('recv', length)
        response = self.file.read(length)
        if len(response) != length:
            print('response %r' % response)
            raise EOFError('read %d, expected %d' % (len(response), length))

        print('response', repr(response))
        type = response[0]
        payload = response[1:]

        if type == message_types['bitfield']:
            self.handle_bitfield(payload)
        elif type == message_types['have']:
            self.handle_have(payload)
        elif type == message_types['choke']:
            self.choked = False
        elif type == message_types['unchoke']:
            self.choked = True

    def handle_bitfield(self, payload):
        for i in range(len(self.have_pieces)):
            ch = i // 8
            bit = i % 8
            self.have_pieces[i] = (payload[ch] >> bit) & 1

    def handle_have(self, payload):
        id = struct.unpack('!I', payload)
        self.have_pieces[id] = True

    def send_request(self, index, begin, length):
        self.send(message_types['request'],
                  struct.pack('!III', index, begin, length))

    def send(self, id, payload):
        self.file.write(struct.pack('!I', 1 + len(payload)) + id)
        self.file.write(payload)

class Downloader(object):
    def __init__(self, torrent):
        self.torrent = torrent

        self.left = torrent.length
        self.peer_id = os.urandom(20)
        self.port = 6882
        self.uploaded = 0
        self.downloaded = 0

    def main(self):
        self.tracker_request()

        print(self.tracker_response)

    def tracker_request(self):
        self.tracker_response = torrent.tracker_request(
            self.torrent.announce, self.torrent.info_hash,
            peer_id=self.peer_id, port=self.port, uploaded=self.uploaded,
            downloaded=self.downloaded, left=self.left)

if __name__ == '__main__':
    import random
    import traceback

    v = bencode.Decoder(open(sys.argv[1], 'rb')).decode()
    t = torrent.Torrent(v)

    downloader = Downloader(t)
    downloader.main()

    random.shuffle(downloader.tracker_response)

    for peer in downloader.tracker_response:
        try:
            conn = Peer(addr=peer, peer_id=downloader.peer_id, torrent=t)
            conn.init()
            conn.main()
        except Exception:
            traceback.print_exc()
