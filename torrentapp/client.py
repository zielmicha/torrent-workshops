from django.conf import settings

import torrent
import bencode

import struct
import requests
import socket
import threading
import time

from binascii import hexlify

from protocol import protocol_header, header_reserved, message_types, PeerBase


class Uploader(PeerBase):
    def __init__(self, socket, addr):
        self.socket = socket
        self.addr = addr
        self.socket.settimeout(10)
        self.file = self.socket.makefile('rwb')
        self.info_hash = None

    def run(self):
        try:
            self.run0()
            self.socket.close()
        except Exception as exc:
            self.log('Error: %r' % exc)
            if not isinstance(exc, socket.timeout):
                raise

    def close(self):
        self.file.close()

    def run0(self):
        if not self.init():
            return
        self.send_have()
        self.loop()

    def loop(self):
        while True:
            if not self.recv():
                return

    def recv(self):
        type, payload = self.do_recv()

        if type == message_types['request']:
            return self.handle_request(payload)
        # elif type == message_types['interested']:
        #     self.send(message_types['unchoke'], b'')
        elif type in (message_types['choke'], message_types['unchoke'],
                      message_types['interested'], message_types['not interested'],
                      message_types['have']):
            pass
        elif type == message_types['bitfield']:
            pass
        else:
            self.log('invalid frame type %d' % type)
            self.close()

        return True

    def handle_request(self, payload):
        index, begin, length = struct.unpack('!III', payload)

        if length > 64 * 1024 or length <= 0:
            self.log('invalid length %d', length)
            return self.close()

        if begin < 0 or begin > self.torrent.piece_length:
            self.log('invalid begin %d', begin)
            return self.close()

        if index < 0 or index > len(self.torrent.pieces):
            self.log('invalid index %d', begin)
            return self.close()

        offset = self.torrent.piece_length * index + begin

        if offset + length > len(self.torrent_data):
            self.log('requested too big length (total %d, requested %d)',
                     len(self.torrent_data), offset + length)
            return self.close()

        self.send_piece(index, begin, self.torrent_data[offset: offset + length])

        return True

    def send_piece(self, index, begin, data):
        self.send(message_types['piece'],
                  struct.pack('!II', index, begin) + data)

    def init(self):
        self.file.write(protocol_header + header_reserved)
        self.file.flush()

        header = self.file.read(len(protocol_header))

        if header != protocol_header:
            self.log('invalid protocol header %r', header)
            return

        if len(self.file.read(len(header_reserved))) != len(header_reserved):
            self.log('premature EOF (header)')
            return

        self.info_hash = self.file.read(20)

        if len(self.info_hash) != 20:
            self.log('premature EOF (info hash)')
            return

        self.torrent_data = self.get_data()
        self.torrent = self.get_torrent()

        self.file.write(self.info_hash)
        self.file.write(b'-MT-workshops-'.ljust(20, b'0')) # peer id

        other_peer_id = self.file.read(20)

        if len(other_peer_id) != 20:
            self.log('premature EOF (peer id)')
            return

        self.log('connection from peer %s', other_peer_id)

        return True

    def send_have(self):
        bits = []
        piece_count = len(self.torrent.pieces)

        for i in range(0, piece_count, 8):
            mask = 0
            for j in range(min(8, piece_count - i)):
                mask |= (1 << (7 - j))
            bits.append(mask)

        print(bits)
        self.send(message_types['bitfield'], bytes(bits))
        time.sleep(1)
        self.send(message_types['unchoke'], b'')

    def get_data(self):
        resp = requests.get(settings.SITE_URL + 'api/torrent_data',
                            params={'info_hash': hexlify(self.info_hash)})
        resp.raise_for_status()
        return resp.content

    def get_torrent(self):
        resp = requests.get(settings.SITE_URL + 'api/torrent_file',
                            params={'info_hash': hexlify(self.info_hash)})
        resp.raise_for_status()
        return torrent.Torrent(bencode.decode(resp.content))

    def log(self, msg, *args):
        if args:
            msg = msg % args

        ok = False
        if self.info_hash:
            resp = requests.get(settings.SITE_URL + 'api/push_log',
                                params={'info_hash': hexlify(self.info_hash), 'msg': msg})
            ok = resp.status_code == 200

        if not ok:
            print('PREAUTH LOG', self.addr, msg)
        else:
            print('log', self.addr, msg)

def main():
    server = socket.socket()
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((settings.SELF_IP, settings.CLIENT_PORT))
    server.listen(254)

    while True:
        sock, addr = server.accept()
        print('connection from', addr)
        uploader = Uploader(sock, addr)
        threading.Thread(target=Uploader.run, args=[uploader]).start()
        del sock

if __name__ == '__main__':
    main()
