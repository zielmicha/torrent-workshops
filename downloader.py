import torrent
import bencode
import sys
import socket
import os

protocol_header = b'19BitTorrent protocol\0\0\0\0\0\0\0\0'

class Connection(object):
    def __init__(self, addr):
        self.sock = socket.socket()
        self.addr = addr

    def init(self, info_hash):
        self.sock.connect(self.addr)
        self.file = self.sock.makefile('rwb', 0)
        self.file.write(protocol_header)
        self.file.write(info_hash)

        print(self.file.read(20))

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
    v = bencode.Decoder(open(sys.argv[1], 'rb')).decode()
    t = torrent.Torrent(v)

    downloader = Downloader(t)
    downloader.main()
