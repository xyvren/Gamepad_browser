import math
import struct

BUTTON_ORDER = ['cross','circle','square','triangle','up','down','left','right','l1','r1','l3','r3','share','options','home']
BUTTONS = set(BUTTON_ORDER)


def decode_binary(packet):
    """Decode the fixed 16-byte little-endian state and uint32 sequence."""
    if not isinstance(packet, (bytes, bytearray)) or len(packet) != 16:
        raise ValueError('Expected 16-byte input')
    mask, x, y, rx, ry, lt, rt, seq = struct.unpack('<HhhhhBBI', packet)
    if mask & 0x8000 or -32768 in (x, y, rx, ry):
        raise ValueError('Invalid buttons or axes')
    return {'buttons': [b for i, b in enumerate(BUTTON_ORDER) if mask & (1 << i)],
            'axes': [v / 32767 for v in (x, y, rx, ry)],
            'triggers': [lt / 255, rt / 255]}, seq

def neutral():
    return {'buttons': [], 'axes': [0,0,0,0], 'triggers': [0,0]}

def validate_state(data):
    if not isinstance(data, dict):
        raise ValueError('Expected state object')
    buttons, axes, triggers = (data.get(k) for k in ('buttons','axes','triggers'))
    if not isinstance(buttons,list) or len(buttons)>15 or any(not isinstance(b,str) or b not in BUTTONS for b in buttons):
        raise ValueError('Invalid buttons')
    for values, count, low in ((axes,4,-1),(triggers,2,0)):
        if not isinstance(values,list) or len(values)!=count or any(type(v) not in (int,float) or not math.isfinite(v) or not low<=v<=1 for v in values):
            raise ValueError('Invalid axes or triggers')
    return {'buttons': sorted(set(buttons)), 'axes': axes[:], 'triggers': triggers[:]}
