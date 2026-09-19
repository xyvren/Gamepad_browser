import unittest

class ProtocolTests(unittest.TestCase):
    def test_binary_wire_format(self):
        import struct
        import protocol
        self.assertTrue(hasattr(protocol, 'decode_binary'))
        state, seq = protocol.decode_binary(struct.pack('<HhhhhBBI', 0x4001, 32767, -32767, 0, 123, 255, 0, 30))
        self.assertEqual(state['buttons'], ['cross', 'home'])
        self.assertEqual(state['axes'], [1, -1, 0, 123 / 32767])
        self.assertEqual(state['triggers'], [1, 0])
        self.assertEqual(seq, 30)
        for packet in (b'', bytes(15), bytes(17), struct.pack('<HhhhhBBI', 0x8000, 0, 0, 0, 0, 0, 0, 0), struct.pack('<HhhhhBBI', 0, -32768, 0, 0, 0, 0, 0, 0)):
            with self.assertRaises(ValueError):
                protocol.decode_binary(packet)

    def test_state_validation(self):
        from protocol import validate_state
        self.assertEqual(validate_state({'buttons':['cross'], 'axes':[0.5,-1,0,1], 'triggers':[0,1]})['axes'], [0.5,-1,0,1])
        for value in [None, {}, {'buttons':['evil'],'axes':[0]*4,'triggers':[0,0]}, {'buttons':[], 'axes':[float('nan'),0,0,0], 'triggers':[0,0]}]:
            with self.assertRaises(ValueError):
                validate_state(value)

if __name__ == '__main__': unittest.main()
