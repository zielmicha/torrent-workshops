import hashlib
import ipaddress
import struct
import requests

import bencode

class Torrent(object):
    def __init__(self, torrent_dict):
        self.info = torrent_dict[b'info']
        self.announce = torrent_dict[b'announce']

        self.info_binary = bencode.encode(self.info)
        self.info_hash = hashlib.sha1(self.info_binary).digest()

        self.piece_length = self.info[b'piece length']
        self.length = self.info[b'length']

        pieces = self.info[b'pieces']
        self.pieces = [
            pieces[20 * i: 20 * (i + 1)]
            for i in range(len(pieces) // 20)
        ]

def tracker_request(announce, info_hash, *, peer_id, port, uploaded, downloaded, left):
    resp = requests.get(announce,
                        params=dict(peer_id=peer_id, port=port, uploaded=uploaded,
                                    downloaded=downloaded, left=left, info_hash=info_hash,
                                    compact='1'))
    resp.raise_for_status()

    data = bencode.decode(resp.content)
    peers = data[b'peers']

    npeers = int(len(peers) / 6)
    assert npeers * 6 == len(peers)

    peer_arr = []

    for i in range(npeers):
        ip = peers[i * 6: i * 6 + 4]
        port = peers[i * 6 + 4: i * 6 + 6]

        peer_arr.append((
            str(ipaddress.IPv4Address(ip)),
            struct.unpack('!H', port)[0]
        ))

    return peer_arr

if __name__ == '__main__':
    import sys
    import os

    v = bencode.Decoder(sys.stdin.buffer).decode()
    torrent = Torrent(v)

    peer_id = os.urandom(20)
    port = 6882
    uploaded = '0'
    downloaded = '0'
    left = torrent.info[b'length']
    info_hash = torrent.info_hash

    r = tracker_request(torrent.announce, info_hash,
                        peer_id=peer_id, port=port, uploaded=uploaded,
                        downloaded=downloaded, left=left)
    print(r)
