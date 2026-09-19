# Protocol Design

## Frame Format

```text
Preamble(32 bit)
Version + Reserved(8 bit)
Frame ID(16 bit)
Payload Length(16 bit)
Payload
CRC-16/XMODEM(16 bit)
```

Constants:

| Field | Value / Limit |
| --- | --- |
| Preamble | `0x6E9797A1` |
| Version | 1 (high nibble), reserved low nibble = 0 |
| Frame ID | 16 bit, `0..65535` |
| Payload Length | 16 bit, current code limit 512 B |
| CRC | CRC-16/XMODEM, big-endian |

CRC coverage: Version + Frame ID + Payload Length + Payload
(everything after Preamble).

## Implementations

### newtry97 v0.2

`src/newtry97/framing.py`

- bit-level frame construction;
- `FrameDecoder` sliding Preamble search;
- CRC failure → log and continue resynchronisation;
- single-frame recovery demo.

### protocol_stego

`src/protocol_stego/core/framing.py`

- `encode_frame()`;
- `decode_frame()`;
- `FrameStreamDecoder`;
- `split_payload()`;
- explicit exceptions:
  - `PreambleNotFoundError`
  - `UnsupportedVersionError`
  - `InvalidPayloadLengthError`
  - `IncompleteFrameError`
  - `CRCMismatchError`.

`src/protocol_stego/core/reassembly.py`

- reassemble by `Frame ID`;
- detect duplicate IDs;
- detect missing IDs;
- detect abnormal order;
- concatenate payloads to ciphertext.

## Multi-Frame Convention

- all frames except the last use full `max_payload_size`;
- the last frame may be shorter;
- if payload length is an exact multiple, a zero-length terminator frame is
  appended.

## Bitstream

`src/protocol_stego/core/bitstream.py`

- `bytes_to_bits()`
- `bits_to_bytes()`
- strict non-multiple-of-8 handling; optional zero padding.

## Tests

- `src/protocol_stego/tests/test_framing.py`
- `src/protocol_stego/tests/test_reassembly.py`
- `src/protocol_stego/tests/test_bitstream.py`
- `src/protocol_stego/tests/test_crc.py`

## Not Implemented

- FEC;
- retransmission;
- version negotiation;
- protocol-level key exchange.
