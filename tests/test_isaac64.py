import hashlib

import pytest

from wxvd.isaac64 import ENC_LEN, decrypt_prefix, keystream

# Generated from JohnABC/WechatSphDecrypt decrypt.go (DecryptData on 131072 zero bytes).
GOLDEN = [
    (0, "9d39247e33776d412af7398005aaa5c7",
     "e1662af3b7e59867c919ad19055fc8cecea2b154d37e1459b2f96d1da14cef1f"),
    (930220499, "12a58ee29bfd4ddf7b79fb892aba9a1b",
     "33077ca0aa580e429ceb3f86f436fd571faeaa9d804e2c7266fc299478530a3e"),
    (2136343393, "23766a3699fb876a75d5a232994844ab",
     "49b96d6fc75ba5215fbb773ce98f6b20f6441a7ac40abc9582b1e42c5f3cd9d8"),
    (2**64 - 1, "7c38fd3a2e7cd8ad64081892c82430f3",
     "5afbffd76305e81467f97c6370fa07916e9b197611bf5c357a854eb92a6354a1"),
]


@pytest.mark.parametrize("seed,head,digest", GOLDEN)
def test_keystream_matches_go_reference(seed, head, digest):
    ks = keystream(seed)
    assert len(ks) == ENC_LEN
    assert ks[:16].hex() == head
    assert hashlib.sha256(ks).hexdigest() == digest


def test_decrypt_roundtrip_leaves_tail_untouched():
    plain = bytes(range(256)) * 1024  # 256 KiB
    enc = decrypt_prefix(plain, 930220499)
    assert enc[ENC_LEN:] == plain[ENC_LEN:]
    assert enc[:ENC_LEN] != plain[:ENC_LEN]
    assert decrypt_prefix(enc, 930220499) == plain


def test_short_file():
    data = b"\x00" * 100
    assert decrypt_prefix(data, 0) == keystream(0, 100)
