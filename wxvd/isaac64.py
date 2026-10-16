"""Isaac64 keystream used by WeChat Channels (视频号) video encryption.

Only the first ``ENC_LEN`` bytes of a Channels MP4 are encrypted: they are
XORed with an Isaac64 keystream seeded by the feed's ``decodeKey``. The rest
of the file is plain MP4.

Port of JohnABC/WechatSphDecrypt ``decrypt.go``. Results are drained from
the top of each 256-word block down and written big-endian, which equals
WeChat's WASM ``WxIsaac64(seed).generate(n)`` output reversed.
"""

ENC_LEN = 131072

_MASK = (1 << 64) - 1
_GOLDEN = 0x9E3779B97F4A7C13


def _mix(s):
    a, b, c, d, e, f, g, h = s
    a = (a - e) & _MASK; f ^= h >> 9;  h = (h + a) & _MASK
    b = (b - f) & _MASK; g ^= (a << 9) & _MASK;  a = (a + b) & _MASK
    c = (c - g) & _MASK; h ^= b >> 23; b = (b + c) & _MASK
    d = (d - h) & _MASK; a ^= (c << 15) & _MASK; c = (c + d) & _MASK
    e = (e - a) & _MASK; b ^= d >> 14; d = (d + e) & _MASK
    f = (f - b) & _MASK; c ^= (e << 20) & _MASK; e = (e + f) & _MASK
    g = (g - c) & _MASK; d ^= f >> 17; f = (f + g) & _MASK
    h = (h - d) & _MASK; e ^= (g << 14) & _MASK; g = (g + h) & _MASK
    return [a, b, c, d, e, f, g, h]


class Isaac64:
    def __init__(self, seed: int):
        self.mm = [0] * 256
        self.rsl = [0] * 256
        self.aa = self.bb = self.cc = 0

        self.rsl[0] = seed & _MASK
        s = [_GOLDEN] * 8
        for _ in range(4):
            s = _mix(s)
        for src in (self.rsl, self.mm):
            for i in range(0, 256, 8):
                s = [(s[j] + src[i + j]) & _MASK for j in range(8)]
                s = _mix(s)
                self.mm[i:i + 8] = s
        self._generate()
        self.cnt = 255

    def _generate(self):
        mm, rsl = self.mm, self.rsl
        self.cc = (self.cc + 1) & _MASK
        aa, bb = self.aa, (self.bb + self.cc) & _MASK
        for i in range(256):
            r = i & 3
            if r == 0:
                aa = ~(aa ^ ((aa << 21) & _MASK)) & _MASK
            elif r == 1:
                aa ^= aa >> 5
            elif r == 2:
                aa ^= (aa << 12) & _MASK
            else:
                aa ^= aa >> 33
            aa = (aa + mm[(i + 128) & 255]) & _MASK
            x = mm[i]
            y = (mm[(x >> 3) & 255] + aa + bb) & _MASK
            mm[i] = y
            bb = (mm[(y >> 11) & 255] + x) & _MASK
            rsl[i] = bb
        self.aa, self.bb = aa, bb

    def next(self) -> int:
        result = self.rsl[self.cnt]
        if self.cnt == 0:
            self._generate()
            self.cnt = 255
        else:
            self.cnt -= 1
        return result


def keystream(seed: int, length: int = ENC_LEN) -> bytes:
    rng = Isaac64(seed)
    out = bytearray()
    while len(out) < length:
        out += rng.next().to_bytes(8, "big")
    return bytes(out[:length])


def decrypt_prefix(data: bytes, seed: int, enc_len: int = ENC_LEN) -> bytes:
    """XOR the first ``enc_len`` bytes of ``data``; the rest is returned unchanged."""
    n = min(enc_len, len(data))
    ks = keystream(seed, n)
    head = (int.from_bytes(data[:n], "big") ^ int.from_bytes(ks, "big")).to_bytes(n, "big")
    return head + data[n:]
