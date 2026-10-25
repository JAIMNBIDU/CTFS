"""CAMP 14 BEACON IN THE STORM - DNS exfiltration: the flag is hex-encoded and
smuggled out one subdomain label at a time to a domain that never resolves.
Decoy A-lookups surround it so it does not stand out."""
from scapy.all import IP, UDP, DNS, DNSQR, wrpcap

EXFIL_DOMAIN = "exfil.peak"
DECOYS = ["pool.ntp.org", "updates.relay.peak", "cdn.weather.io",
          "telemetry.relay.peak", "mirror.debian.org"]


def build(ctx):
    enc = ctx.flag.encode().hex()                     # dns-safe lowercase hex
    chunks = [enc[i:i + 20] for i in range(0, len(enc), 20)]
    cli = IP(src="10.4.0.9", dst="10.4.0.53")

    pkts = []
    # a couple of ordinary lookups first, so the capture looks normal
    for i, d in enumerate(DECOYS[:2]):
        pkts.append(cli / UDP(sport=35000 + i, dport=53) /
                    DNS(id=500 + i, rd=1, qd=DNSQR(qname=d)))
    # the exfil beacon: label order == chunk order
    for idx, ch in enumerate(chunks):
        q = f"{ch}.{EXFIL_DOMAIN}"
        pkts.append(cli / UDP(sport=40000 + idx, dport=53) /
                    DNS(id=1000 + idx, rd=1, qd=DNSQR(qname=q)))
        # sprinkle a decoy between beacons
        if idx < len(DECOYS):
            d = DECOYS[idx % len(DECOYS)]
            pkts.append(cli / UDP(sport=36000 + idx, dport=53) /
                        DNS(id=700 + idx, rd=1, qd=DNSQR(qname=d)))

    wrpcap(str(ctx.stage_dir / "beacon.pcap"), pkts)
