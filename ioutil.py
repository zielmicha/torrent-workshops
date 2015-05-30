
def read_until(stream, char):
    ret = []
    while True:
        ch = stream.read(1)
        if not ch:
            raise EOFError
        if ch == char:
            return b''.join(ret)
        ret.append(ch)
