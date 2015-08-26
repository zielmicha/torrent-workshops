import downloader
import torrent
import sys
import bencode
import collections
import socket

class StreamingDownloader(downloader.Downloader):
    def __init__(self, torrent, file):
        super().__init__(torrent)
        self.out_file = file
        self.written = 0
        self.queue = collections.deque()

    def add_data(self, piece_i, begin, data):
        super().add_data(piece_i, begin, data)
        offset = piece_i * self.torrent.piece_length + begin

        self.queue.append((offset, len(data), data))
        self.queue = collections.deque(sorted(self.queue))

        print('queue size', len(self.queue), self.written, self.queue[0][:2])

        while self.queue and self.queue[0][0] == self.written:
            offset, length, data = self.queue.popleft()
            self.written += length
            self.out_file.write(data)
            self.out_file.flush()

if __name__ == '__main__':
    v = bencode.Decoder(open(sys.argv[1], 'rb')).decode()
    t = torrent.Torrent(v)

    sock = socket.socket()
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('localhost', 7000))
    sock.listen(5)
    child, _ = sock.accept()
    print('accepted')
    out = child.makefile('rwb')
    out.write(b'HTTP/1.0 200 OK\r\n\r\n')

    downloader = StreamingDownloader(t, out)
    downloader.main()
