import torrent
import bencode
import sys
import socket
import os
import struct
import math
import hashlib

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
        self.got_pieces = []

    def init(self):
        self.sock.connect(self.addr)

        print('opened connection to', self.addr)
        self.file = self.sock.makefile('rwb')
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

    def recv(self):
        length, = struct.unpack('!I', self.file.read(4))
        print('recv', length)
        response = self.file.read(length)
        if len(response) != length:
            raise EOFError('read %d, expected %d' % (len(response), length))

        print('response', repr(response)[:80])
        type = response[0]
        payload = response[1:]

        if type == message_types['bitfield']:
            self.handle_bitfield(payload)
        elif type == message_types['have']:
            self.handle_have(payload)
        elif type == message_types['choke']:
            self.choked = True
        elif type == message_types['unchoke']:
            print('peer unchoked')
            self.choked = False
            self.queued_requests = 0
        elif type == message_types['piece']:
            self.handle_piece(payload)

    def handle_bitfield(self, payload):
        for i in range(len(self.have_pieces)):
            ch = i // 8
            bit = i % 8
            self.have_pieces[i] = (payload[ch] >> bit) & 1

    def handle_have(self, payload):
        id, = struct.unpack('!I', payload)
        self.have_pieces[id] = True

    def handle_piece(self, payload):
        piece, begin = struct.unpack('!II', payload[:8])
        self.got_pieces.append((piece, begin, payload[8:]))
        self.queued_requests -= 1

    def send_request(self, index, begin, length):
        self.queued_requests += 1
        print('send_request', index, begin, length)
        self.send(message_types['request'],
                  struct.pack('!III', index, begin, length))

    def send(self, id, payload):
        print('send %d %r' % (id, payload))
        self.file.write(struct.pack('!I', 1 + len(payload)) + bytes([id]))
        self.file.write(payload)
        self.file.flush()

REQUEST_SIZE = 8 * 1024

def mod(a, b):
    if a % b == 0:
        return b
    else:
        return a % b

class Downloader(object):
    def __init__(self, torrent):
        self.torrent = torrent

        self.left = torrent.length
        self.peer_id = os.urandom(20)
        self.port = 6882
        self.uploaded = 0
        self.downloaded = 0
        self.finished = False

        self.chunk_queue = []
        self.chunks_left = []
        self.data_left = 0
        self.data = bytearray(torrent.length)

    def setup_queue(self):
        for piece_i in range(len(self.torrent.pieces)):
            if piece_i == len(self.torrent.pieces) - 1:
                piece_length = mod(self.torrent.length, self.torrent.piece_length)
            else:
                piece_length = self.torrent.piece_length

            chunk_per_piece = int(math.ceil(piece_length / REQUEST_SIZE))
            self.chunks_left.append(piece_length)
            self.data_left += piece_length

            for chunk_i in range(chunk_per_piece):
                if chunk_i == chunk_per_piece - 1:
                    chunk_size = mod(piece_length, REQUEST_SIZE)
                else:
                    chunk_size = REQUEST_SIZE

                self.chunk_queue.append((piece_i, chunk_i, chunk_size))

        self.chunk_queue.reverse()
        print(self.chunk_queue)

    def add_data(self, piece_i, begin, data):
        self.chunks_left[piece_i] -= len(data)
        self.data_left -= len(data)

        print('downloaded %d %d, left %d' % (piece_i, begin, self.chunks_left[piece_i]))
        start = piece_i * self.torrent.piece_length + begin
        self.data[start:start + len(data)] = data

        if self.chunks_left[piece_i] == 0:
            self.verify(piece_i)

    def verify(self, piece_i):
        print('verify %d' % piece_i)

        lenght = self.torrent.piece_length
        piece_data = self.data[piece_i * lenght:(piece_i + 1) * lenght]
        digest = hashlib.sha1(piece_data).digest()

        if self.torrent.pieces[piece_i] != digest:
            raise ValueError('verification failed')

    def main(self):
        self.setup_queue()
        self.tracker_request()

        addr = self.tracker_response[0]
        self.peer_main(addr)

    def tracker_request(self):
        self.tracker_response = torrent.tracker_request(
            self.torrent.announce, self.torrent.info_hash,
            peer_id=self.peer_id, port=self.port, uploaded=self.uploaded,
            downloaded=self.downloaded, left=self.left)

    def peer_main(self, addr):
        peer = Peer(addr=addr, peer_id=self.peer_id, torrent=self.torrent)
        peer.init()

        while True:
            self.maybe_send_requests(peer)
            peer.recv()
            self.add_recv_data(peer)

    def add_recv_data(self, peer):
        for piece, begin, data in peer.got_pieces:
            self.add_data(piece, begin, data)

        peer.got_pieces = []

        if self.data_left == 0:
            if not self.finished:
                self.finished = True
                self.handle_finish()
                print('finished')

    def maybe_send_requests(self, peer):
        if peer.choked:
            return

        if not self.chunk_queue:
            return

        while peer.queued_requests < 10:
            piece_i, chunk_i, chunk_size = self.chunk_queue.pop()
            print('pop', piece_i, chunk_i, chunk_size)
            peer.send_request(piece_i, chunk_i * REQUEST_SIZE, chunk_size)

    def handle_finish(self):
        for i in range(len(self.torrent.pieces)):
            self.verify(i)

        print('final hash: %s' % hashlib.sha1(self.data).hexdigest())
        print('final size: %d' % len(self.data))
        assert self.torrent.length == len(self.data)

if __name__ == '__main__':
    v = bencode.Decoder(open(sys.argv[1], 'rb')).decode()
    t = torrent.Torrent(v)

    downloader = Downloader(t)
    downloader.main()
