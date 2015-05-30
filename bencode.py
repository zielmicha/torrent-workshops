import ioutil
import string
import io

EndSenitel = object()

class Decoder():
    def __init__(self, stream):
        self.stream = stream

    def decode(self):
        c = self.stream.read(1)
        if c == b'i':
            data = ioutil.read_until(self.stream, b'e')
            if data != b'0' and data.startswith(b'0'):
                raise BencodingError()
            if data == b'-0':
                raise BencodingError()
            return int(data)

        elif c == b'l':
            return self.read_list()

        elif c in string.digits.encode():
            size_data = ioutil.read_until(self.stream, b':')
            size = int(c + size_data)
            data = self.stream.read(size)
            if len(data) != size:
                raise EOFError()
            return data

        elif c == b'd':
            l = self.read_list()
            return dict(zip(l[::2], l[1::2]))

        elif c == b'e':
            return EndSenitel

    def read_list(self):
        ret = []
        while True:
            obj = self.decode()
            if obj == EndSenitel:
                break
            ret.append(obj)
        return ret

class Encoder():
    def __init__(self, stream):
        self.stream = stream

    def encode(self, obj):
        w = self.stream.write
        if isinstance(obj, int):
            w(b'i')
            w(str(obj).encode())
            w(b'e')

        elif isinstance(obj, bytes):
            w(str(len(obj)).encode())
            w(b':')
            w(obj)

        elif isinstance(obj, dict):
            items = list(obj.items())
            items.sort()
            w(b'd')
            for k, v in items:
                self.encode(k)
                self.encode(v)
            w(b'e')

        elif isinstance(obj, list):
            w(b'l')
            for v in obj:
                self.encode(v)
            w(b'e')

        elif isinstance(obj, str):
            raise BencodingError('str passed to encode - use bytes instead')

        else:
            raise BencodingError('don\'t know how to encode %s' % type(obj))

class BencodingError(Exception):
    pass

def decode(s):
    return Decoder(io.BytesIO(s)).decode()

def encode(v):
    stream = io.BytesIO()
    enc = Encoder(stream)
    enc.encode(v)
    return stream.getvalue()

if __name__ == '__main__':
    import sys
    import pprint

    v = Decoder(sys.stdin.buffer).decode()
    pprint.pprint(v)
