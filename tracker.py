import collections
import urllib_raw
import logging
import bencode
import struct
import ipaddress

from flask import Flask, request

app = Flask(__name__)

data = collections.defaultdict(dict)

@app.route("/announce")
def hello():
    args = urllib_raw.urldecode(request.query_string)
    print(args)
    info_hash = args[b'info_hash']
    peer_id = args[b'peer_id']
    info = (request.remote_addr, int(args[b'port']))
    event = args.get(b'event')

    if event != b'stopped' and peer_id.startswith(b'-TR'):
        data[info_hash][peer_id] = info

    return bencode.encode({
        b'interval': 10,
        b'peers': b''.join([
            ipaddress.IPv4Address(this_info[0]).packed
            + struct.pack('!H', this_info[1])
            for this_peer_id, this_info in data[info_hash].items()
            if this_peer_id != peer_id
        ])
    })

@app.before_first_request
def setup_logging():
    if not app.debug:
        # In production mode, add log handler to sys.stderr.
        app.logger.addHandler(logging.StreamHandler())
        app.logger.setLevel(logging.INFO)

if __name__ == "__main__":
    app.run(port=8080)
