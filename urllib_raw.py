# implements some parse urllib.parse without decoding unicode

def unquote(string):
    i = 0
    ret = []
    while i < len(string):
        if string[i] == ord(b'%'):
            ch = int(string[i + 1: i + 3], 16)
            i += 3
        else:
            ch = string[i]
            i += 1

        ret.append(ch)

    return bytes(ret)

def urldecode(string):
    parts = string.split(b'&')
    ret = []

    for part in parts:
        k, v = part.split(b'=', 1)
        ret.append((unquote(k), unquote(v)))

    return dict(ret)
