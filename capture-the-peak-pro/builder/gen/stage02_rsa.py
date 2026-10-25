"""PRO CAMP 2 TOO CLOSE TO HOME - RSA with near-twin primes (Fermat-breakable)."""
from Crypto.Util.number import getPrime, isPrime, bytes_to_long


def build(ctx):
    p = getPrime(512)
    q = p + 2
    while not isPrime(q):
        q += 2                      # the next prime just above p -> tiny gap
    n = p * q
    e = 65537
    m = bytes_to_long(ctx.flag.encode())
    assert m < n, "flag too large for modulus"
    c = pow(m, e, n)
    ctx.write("rsa.txt",
              "# RSA public key + captured ciphertext. the primes are too close.\n"
              f"n = {n}\n"
              f"e = {e}\n"
              f"c = {c}\n")
