from django.conf import settings

import torrent
import bencode

import requests
import socket
import threading

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

    def run0(self):
        self.init()
        self.send_have()

    def init(self):
        self.file.write(protocol_header + header_reserved)
        self.file.flush()

        if self.file.read(len(protocol_header)) != protocol_header:
            self.log('invalid protocol header')
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
        self.file.write(b'\xAA' * 20) # peer id

        other_peer_id = self.file.read(20)

        if len(other_peer_id) != 20:
            self.log('premature EOF (peer id)')
            return

    def send_have(self):
        bits = []
        piece_count = len(self.torrent.pieces)

        for i in range(0, piece_count, 8):
            mask = 0
            for j in range(min(8, piece_count - i)):
                mask |= (1 << j)
            bits.append(mask)

        self.send(message_types['bitfield'], bytes(bits))
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

    def log(self, msg):
        ok = False
        if self.info_hash:
            resp = requests.get(settings.SITE_URL + 'api/push_log',
                                params={'info_hash': hexlify(self.info_hash), 'msg': msg})
            ok = resp.status_code == 200
        if not ok:
            print('PREAUTH LOG', self.addr, msg)

def main():
    server = socket.socket()
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((settings.SELF_IP, settings.CLIENT_PORT))
    server.listen(254)

    while True:
        sock, addr = server.accept()
        uploader = Uploader(sock, addr)
        threading.Thread(target=Uploader.run, args=[uploader]).start()
        del sock

if __name__ == '__main__':
    main()
