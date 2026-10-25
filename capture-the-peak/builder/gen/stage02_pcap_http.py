"""CAMP 02 THE WIRE - HTTP POST with the flag in the clear, in a pcap."""
from scapy.all import IP, TCP, Raw, wrpcap
def build(ctx):
    body = f"user=ridge_ops&secret={ctx.flag}&remember=1"
    req = ("POST /auth HTTP/1.1\r\nHost: relay.peak\r\n"
           "User-Agent: curl/8.0\r\nAccept: */*\r\n"
           "Content-Type: application/x-www-form-urlencoded\r\n"
           f"Content-Length: {len(body)}\r\n\r\n{body}")
    resp = ("HTTP/1.1 200 OK\r\nServer: relay\r\nContent-Type: text/plain\r\n"
            "Content-Length: 24\r\n\r\nwelcome back, ridge_ops\n")
    c = IP(src="10.4.0.9", dst="10.4.0.1")
    s = IP(src="10.4.0.1", dst="10.4.0.9")
    sp, dp, qc, qs = 51510, 80, 1000, 5000
    pkts = [
        c/TCP(sport=sp, dport=dp, flags="S", seq=qc),
        s/TCP(sport=dp, dport=sp, flags="SA", seq=qs, ack=qc+1),
        c/TCP(sport=sp, dport=dp, flags="A", seq=qc+1, ack=qs+1),
        c/TCP(sport=sp, dport=dp, flags="PA", seq=qc+1, ack=qs+1)/Raw(load=req),
        s/TCP(sport=dp, dport=sp, flags="PA", seq=qs+1, ack=qc+1+len(req))/Raw(load=resp),
        c/TCP(sport=sp, dport=dp, flags="A", seq=qc+1+len(req), ack=qs+1+len(resp)),
    ]
    wrpcap(str(ctx.stage_dir / "ridge.pcap"), pkts)
