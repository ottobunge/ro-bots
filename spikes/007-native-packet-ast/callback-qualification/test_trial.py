"""Scratch-only callback source contract and denial checks (stdlib)."""
import hashlib
from pathlib import Path
import unittest

BASE = Path('/home/otto/.hermes/cache/scratch/native-profile-replay-s2jdj4rn/public-source/src/map/clif.cpp')

def qualification_contract(data):
    body = data[ data.index(b'static int32 clif_send_sub('):data.index(b'/*==========================================', data.index(b'static int32 clif_send_sub(')) ]
    for token in (b'const block_list *src_bl;', b'const unsigned char *buf;',
                  b'buf = static_cast<const unsigned char*>(va_arg(ap,const void*));',
                  b'va_arg(ap,const block_list*)', b'len = va_arg(ap,int32);', b'type = va_arg(ap,int32);'):
        if body.count(token) != 1:
            raise AssertionError('missing exact qualified callback contract: '+repr(token))

class Qualification(unittest.TestCase):
    def test_pristine_requires_exact_pointer_types(self):
        from trial import transform
        qualification_contract(transform(BASE.read_bytes()))

    def test_original_remains_negative_structural_control(self):
        with self.assertRaisesRegex(AssertionError, 'const block_list'):
            qualification_contract(BASE.read_bytes())

    def test_hash_drift_denied(self):
        from trial import transform
        data = BASE.read_bytes().replace(b'Packet Delegation', b'Packet DelegatioN')
        with self.assertRaisesRegex(ValueError, 'hash/size drift'):
            transform(data)

    def test_anchor_drift_denied(self):
        from trial import transform
        data = BASE.read_bytes().replace(b'\tblock_list *src_bl;', b'\tblock_list *other;')
        with self.assertRaises(ValueError):
            transform(data)

    def test_only_callback_four_substitutions(self):
        from trial import transform, REPLACEMENTS
        original = BASE.read_bytes()
        patched = transform(original)
        body = original[10749:12589]
        for old, new in REPLACEMENTS:
            body = body.replace(old, new)
        self.assertEqual(patched, original[:10749]+body+original[12589:])
        self.assertEqual(patched.count(b'len = va_arg(ap,int32);'), original.count(b'len = va_arg(ap,int32);'))
        self.assertEqual(patched.count(b'type = va_arg(ap,int32);'), original.count(b'type = va_arg(ap,int32);'))

if __name__ == '__main__':
    unittest.main()
