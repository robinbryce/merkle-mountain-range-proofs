#!/usr/bin/env python3
"""Generate the cross-language checkpoint-receipt KAT over the canonical
39-node MMR (KAT-39).

The Python reference is the arbiter: every number in the output comes from
algorithms.py / db.py. Sections:

  tree                 the 39 nodes, complete sizes, all 21 accumulators
  consistency_pairs    consistent_roots_for_sizes on every ordered pair of
                       complete sizes (210) plus the 21 from-empty pairs
  consistency_negatives  proof shapes every verifier MUST reject
  protected_headers    protected-header byte classes (ADR-0066 D9)
  keys, receipts, receipt_negatives  signed receipts under fixed test keys

Usage: gen_checkpoint_receipt_kat39.py [--go-kat PATH] > out.json
  --go-kat  path to go-merklelog mmr/draft_kat39_test.go; when given, the
            generated tree is asserted equal to Go's literal tables.
"""
import argparse
import hashlib
import json
import re
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import algorithms as alg  # noqa: E402
from db import KatDB  # noqa: E402

# --------------------------------------------------------------------------
# minimal deterministic CBOR (RFC 8949 §4.2.1) for the pieces we emit
# --------------------------------------------------------------------------

def _head(mt, n):
    if n < 24:
        return bytes([(mt << 5) | n])
    for ai, fmt, lim in ((24, ">B", 1 << 8), (25, ">H", 1 << 16), (26, ">I", 1 << 32), (27, ">Q", 1 << 64)):
        if n < lim:
            return bytes([(mt << 5) | ai]) + struct.pack(fmt, n)
    raise ValueError(n)


def cbor_int(v):
    return _head(0, v) if v >= 0 else _head(1, -1 - v)


def cbor_bstr(b):
    return _head(2, len(b)) + b


def cbor_tstr(s):
    b = s.encode()
    return _head(3, len(b)) + b


def cbor_array(items):
    return _head(4, len(items)) + b"".join(items)


def cbor_map(pairs):
    """pairs: list of (encoded_key, encoded_value); sorted length-first then bytewise."""
    enc = sorted(pairs, key=lambda kv: (len(kv[0]), kv[0]))
    return _head(5, len(enc)) + b"".join(k + v for k, v in enc)


def cbor_tag(n, item):
    return _head(6, n) + item


CBOR_NULL = b"\xf6"

LABEL_ALG, LABEL_VDS, LABEL_VDP = 1, 395, 396
VDS_MMR_CONSISTENCY = 3
KEY_CONSISTENCY_PROOF = -2
LABEL_TREE_SIZE_2 = -65535 - 398  # -65933
ALG_ES256, ALG_KS256 = -7, -65799


def protected_header(alg_id, size2, extra=()):
    pairs = [(cbor_int(LABEL_ALG), cbor_int(alg_id)),
             (cbor_int(LABEL_VDS), cbor_int(VDS_MMR_CONSISTENCY)),
             (cbor_int(LABEL_TREE_SIZE_2), cbor_int(size2))]
    pairs += list(extra)
    return cbor_map(pairs)


def sig_structure(protected, payload):
    return cbor_array([cbor_tstr("Signature1"), cbor_bstr(protected), cbor_bstr(b""), cbor_bstr(payload)])


def consistency_proof_bstr(size1, size2, paths, right):
    return cbor_bstr(cbor_array([cbor_int(size1), cbor_int(size2),
                                 cbor_array([cbor_array([cbor_bstr(n) for n in p]) for p in paths]),
                                 cbor_array([cbor_bstr(n) for n in right])]))


def receipt_cbor(protected, proof_bstr, signature):
    unprotected = cbor_map([(cbor_int(LABEL_VDP), cbor_map([(cbor_int(KEY_CONSISTENCY_PROOF), proof_bstr)]))])
    return cbor_tag(18, cbor_array([cbor_bstr(protected), unprotected, CBOR_NULL, cbor_bstr(signature)]))


# --------------------------------------------------------------------------
# tree
# --------------------------------------------------------------------------

def hx(b):
    return b.hex()


def build_tree():
    db = KatDB()
    db.init_canonical39()
    nodes = [db.get(i) for i in range(39)]
    complete_sizes = [s for s in range(1, 40) if alg.mmr_size_for_leaf_count(alg.leaf_count(s - 1)) == s]
    leaves = [i for i in range(39) if alg.index_height(i) == 0]
    acc = {}
    for s in complete_sizes:
        pk = alg.peaks(s - 1)
        acc[str(s)] = {"peak_indices": pk, "peaks_hex": [hx(db.get(i)) for i in pk]}
    tree = {
        "leaf_rule": "sha256(BE8(mmr_index))",
        "interior_rule": "sha256(BE8(pos)) || left || right) with pos = mmr_index + 1 (hash_pospair64)",
        "node_count": 39,
        "leaf_count": len(leaves),
        "leaf_mmr_indices": leaves,
        "complete_mmr_sizes": complete_sizes,
        "complete_mmr_indices": [s - 1 for s in complete_sizes],
        "nodes_hex": [hx(n) for n in nodes],
        "accumulators": acc,
    }
    return db, tree, complete_sizes


def check_against_go(tree, go_path):
    src = Path(go_path).read_text()
    m = re.search(r"KAT39Nodes = \[\]string\{(.*?)\n\t\}", src, re.S)
    go_nodes = re.findall(r'"([0-9a-f]{64})"', m.group(1))
    assert go_nodes == tree["nodes_hex"], "KAT39Nodes differ from the Python reference"
    m = re.search(r"KAT39PeakHashes = map\[uint64\]\[\]string\{(.*?)\n\t\}", src, re.S)
    for row in re.finditer(r"(\d+):\s*\{([^}]*)\}", m.group(1)):
        idx = int(row.group(1))
        hexes = re.findall(r'"([0-9a-f]{64})"', row.group(2))
        assert hexes == tree["accumulators"][str(idx + 1)]["peaks_hex"], f"peaks differ at index {idx}"
    m = re.search(r"KAT39CompleteMMRSizes\s*=\s*\[\]uint64\{([^}]*)\}", src)
    go_sizes = [int(x) for x in m.group(1).split(",")]
    assert go_sizes == tree["complete_mmr_sizes"]
    print("go-merklelog KAT39 tables agree with the reference", file=sys.stderr)


# --------------------------------------------------------------------------
# consistency pairs and negatives
# --------------------------------------------------------------------------

def proof_for(db, s1, s2):
    if s1 == 0:
        return [], []
    acc = [db.get(i) for i in alg.peaks(s1 - 1)]
    paths = [[db.get(k) for k in p] for p in alg.consistency_proof_paths(s1 - 1, s2 - 1)]
    return acc, paths


def pair_row(db, s1, s2):
    acc, paths = proof_for(db, s1, s2)
    roots, nright = alg.consistent_roots_for_sizes(s1, s2, acc, paths)
    target = [db.get(i) for i in alg.peaks(s2 - 1)]
    right = target[len(roots):]
    assert len(right) == nright and roots + right == target
    return {
        "name": f"{s1}-to-{s2}",
        "tree_size_1": s1, "tree_size_2": s2,
        "accumulator_from_hex": [hx(a) for a in acc],
        "paths_hex": [[hx(n) for n in p] for p in paths],
        "roots_hex": [hx(r) for r in roots],
        "right_peak_count": nright,
        "right_peaks_hex": [hx(r) for r in right],
        "accumulator_to_hex": [hx(t) for t in target],
    }


def negatives(db):
    rows = []

    def add(name, base, mutation, s1, s2, acc, paths, right, cls):
        try:
            alg.consistent_roots_for_sizes(s1, s2, acc, paths)
            ok = True
        except ValueError:
            ok = False
        # base_mismatch and right_peak_count are outside the fold's own checks
        if cls not in ("base_mismatch", "right_peak_count_mismatch"):
            assert not ok, name
        rows.append({
            "name": name, "base": base, "mutation": mutation,
            "tree_size_1": s1, "tree_size_2": s2,
            "accumulator_from_hex": [hx(a) for a in acc],
            "paths_hex": [[hx(n) for n in p] for p in paths],
            "right_peaks_hex": [hx(r) for r in right],
            "expect": {"result": "reject", "class": cls},
        })

    acc, paths = proof_for(db, 7, 15)
    target = [db.get(i) for i in alg.peaks(14)]
    add("size-must-increase/7-to-7", "7-to-15", "tree_size_2 set equal to tree_size_1", 7, 7, acc, paths, [], "size_must_increase")
    add("incomplete-tree-size/7-to-9", "7-to-15", "tree_size_2 set to 9, which is not a complete MMR size", 7, 9, acc, paths, [], "incomplete_tree_size")
    add("peak-count-mismatch/7-to-15-missing-peak", "7-to-15", "last accumulator entry and its path removed", 7, 15, acc[:-1], paths[:-1], [], "peak_count_mismatch")
    add("path-length-mismatch/1-to-3-empty-path", "1-to-3", "the single path emptied; sizes imply length 1", 1, 3, *proof_for(db, 1, 3)[:1], [[]], [], "path_length_mismatch")
    a2, p2 = proof_for(db, 7, 15)
    p2 = [p + [db.get(0)] for p in p2]
    add("path-length-mismatch/7-to-15-lengthened", "7-to-15", "one node appended to every path", 7, 15, a2, p2, [], "path_length_mismatch")
    a3, p3 = proof_for(db, 10, 15)
    p3[1] = [b"\x00" * 32] + p3[1][1:]
    add("root-mismatch/10-to-15-altered-sibling", "10-to-15", "first sibling of the second path zeroed; two paths under one target peak prove different roots", 10, 15, a3, p3, [], "root_mismatch")
    a4, p4 = proof_for(db, 7, 8)
    add("right-peak-count-mismatch/7-to-8-surplus", "7-to-8", "an extra right peak supplied; the sizes fix the count at 1", 7, 8, a4, p4, [db.get(7), db.get(0)], "right_peak_count_mismatch")
    a5, p5 = proof_for(db, 7, 8)
    add("base-mismatch/declared-4-trusted-7", "7-to-8", "proof declares tree_size_1 = 4 while the verifier's trusted size is 7; the verifier compares and rejects before folding", 4, 8, a5, p5, [db.get(7)], "base_mismatch")
    rows[-1]["trusted_tree_size_1"] = 7
    return rows


# --------------------------------------------------------------------------
# protected-header classes (ADR-0066 D9 as amended: unread labels may carry
# int, bstr, valid tstr, false/true/null, shortest-form float; integer keys)
# --------------------------------------------------------------------------

def header_rows():
    H8 = "a3012619018b033a0001018c08"
    rows = []

    def acc(name, hexs, note, size=8):
        rows.append({"name": name, "hex": hexs, "note": note, "expect": {"result": "accept", "tree_size_2": size}})

    def rej(name, hexs, note, reason):
        rows.append({"name": name, "hex": hexs, "note": note, "expect": {"result": "reject", "reason": reason}})

    def absent(name, hexs, note):
        rows.append({"name": name, "hex": hexs, "note": note, "expect": {"result": "absent"}})

    acc("canonical/size-8", H8, "the sealer's ES256 header, size 8 as a 1-byte uint")
    acc("canonical/size-1", "a3012619018b033a0001018c01", "the sealer's ES256 header, size 1", 1)
    acc("canonical/ks256-size-8", "a3013a0001010619018b033a0001018c08", "the sealer's KS256 header (alg -65799)")
    acc("canonical/size-39-1-byte-arg", "a3012619018b033a0001018c1827", "size 39 needs a 1-byte argument (0x18 0x27)", 39)
    acc("canonical/size-2^40-8-byte-arg", "a3012619018b033a0001018c1b0000010000000000", "size 2^40 needs an 8-byte argument; accepted by the header parser (the fold rejects it later as incomplete). Kept below 2^53 so every JSON consumer reads it exactly", 1 << 40)
    # skip: unread label 7 carrying an allowed type
    acc("skip/int", "a4012607182a19018b033a0001018c08", "{7: 42} under an unread label")
    acc("skip/negative-int", "a40126072019018b033a0001018c08", "{7: -1}")
    acc("skip/bstr", "a4012607420102" + "19018b033a0001018c08", "{7: h'0102'}")
    acc("skip/tstr", "a401260762686919018b033a0001018c08", "{7: \"hi\"}")
    acc("skip/mt7-false", "a4012607f419018b033a0001018c08", "{7: false}")
    acc("skip/mt7-true", "a4012607f519018b033a0001018c08", "{7: true}")
    acc("skip/mt7-null", "a4012607f619018b033a0001018c08", "{7: null}")
    acc("skip/mt7-half-float-1.0", "a4012607f93c0019018b033a0001018c08", "{7: 1.0} as a half float, its shortest form")
    acc("skip/mt7-half-nan", "a4012607f97e0019018b033a0001018c08", "{7: NaN} as a half float, its shortest form")
    acc("skip/mt7-half-inf", "a4012607f97c0019018b033a0001018c08", "{7: Infinity} as a half float")
    acc("skip/mt7-double-float-1e300", "a4012607fb7e37e43c880759db19018b033a0001018c08", "{7: 1e300}; no shorter form preserves the value")
    acc("skip/two-unread-labels-length-first-order", "a50126200018180019018b033a0001018c08",
        "keys 1, -1 (0x20), 24 (0x1818), 395, -65933 in length-first order; -1 (1 byte) precedes 24 (2 bytes) although 0x18 < 0x20 bytewise")
    absent("absent/no-tree-size-label", "a2012619018b03", "{1: -7, 395: 3}: the pre-ADR-0066 header; no signed size")
    # reject: value types excluded by D9
    rej("reject/mt7-simple-40", "a4012607f82819018b033a0001018c08", "{7: simple(40)}; only false, true and null are allowed", "excluded_value_type")
    rej("reject/mt7-undefined", "a4012607f719018b033a0001018c08", "{7: undefined}", "excluded_value_type")
    rej("reject/mt7-single-float-1.0", "a4012607fa3f80000019018b033a0001018c08", "1.0 as a single; a half preserves the value", "shortest_form")
    rej("reject/mt7-double-float-1.0", "a4012607fb3ff000000000000019018b033a0001018c08", "1.0 as a double", "shortest_form")
    rej("reject/mt7-double-nan", "a4012607fb7ff800000000000019018b033a0001018c08", "NaN as a double; the half form preserves it", "shortest_form")
    rej("reject/mt7-single-inf", "a4012607fa7f80000019018b033a0001018c08", "Infinity as a single", "shortest_form")
    rej("reject/mt7-double-inf", "a4012607fb7ff000000000000019018b033a0001018c08", "Infinity as a double", "shortest_form")
    rej("reject/array-under-unread-label", "a40126078019018b033a0001018c08", "{7: []}; containers are excluded", "excluded_value_type")
    rej("reject/map-under-unread-label", "a4012607a019018b033a0001018c08", "{7: {}}", "excluded_value_type")
    rej("reject/tag-under-unread-label", "a4012607c10819018b033a0001018c08", "{7: 1(8)}; tags are rejected everywhere", "tag")
    rej("reject/invalid-utf8-under-unread-label", "a401260761ff19018b033a0001018c08", "{7: tstr(0xff)}; text strings must be valid UTF-8", "invalid_utf8")
    rej("reject/text-string-key", "a4012661610019018b033a0001018c08", "{1: -7, \"a\": 0, 395: 3, -65933: 8}; keys must be integers", "non_integer_key")
    # reject: encoding
    rej("reject/non-shortest-value-4-byte", "a3012619018b033a0001018c1a00000008", "size 8 as a 4-byte argument", "shortest_form")
    rej("reject/non-shortest-value-1-byte", "a3012619018b033a0001018c1808", "size 8 as a 1-byte argument", "shortest_form")
    rej("reject/non-shortest-key", "a301261a0000018b033a0001018c08", "key 395 as a 4-byte argument", "shortest_form")
    rej("reject/keys-reversed", "a33a0001018c0819018b030126", "keys in descending length", "key_order")
    rej("reject/tree-size-before-vds", "a301263a0001018c0819018b03", "5-byte key before 3-byte key", "key_order")
    rej("reject/two-unread-labels-bytewise-order", "a50126181800200019018b033a0001018c08",
        "keys 1, 24 (0x1818), -1 (0x20), 395, -65933: bytewise order (0x18 < 0x20) is not length-first order", "key_order")
    rej("reject/duplicate-tree-size-label", "a4012619018b033a0001018c043a0001018c08", "-65933 twice", "duplicate_key")
    rej("reject/trailing-byte", "a3012619018b033a0001018c0800", "one byte after the map", "trailing_bytes")
    rej("reject/under-declared-map", "a2012619018b033a0001018c08", "map(2) carrying three pairs; the third is trailing", "trailing_bytes")
    rej("reject/string-length-beyond-header", "a20126044a0102", "kid bstr declares 10 bytes, 2 remain", "truncated")
    rej("reject/uint-key-beyond-int64", "a4012619018b033a0001018c081b800000000000000000", "key 2^63", "key_beyond_int64")
    rej("reject/negative-key-beyond-int64", "a4012619018b033a0001018c083b800000000000000000", "key -2^63-1", "key_beyond_int64")
    # reject: the tree-size value itself
    rej("reject/tree-size-negative", "a3012619018b033a0001018c27", "-65933: -8", "size_not_uint")
    rej("reject/tree-size-bstr", "a3012619018b033a0001018c4108", "-65933: h'08'", "size_not_uint")
    rej("reject/tree-size-half-float", "a3012619018b033a0001018cf94800", "-65933: 8.0", "size_not_uint")
    rej("reject/tree-size-tagged", "a3012619018b033a0001018cc108", "-65933: 1(8)", "tag")
    rej("reject/tree-size-bignum", "a3012619018b033a0001018cc24108", "-65933: 2(h'08')", "tag")
    # reject: malformed
    rej("reject/indefinite-map", "bf012619018b033a0001018c08ff", "indefinite-length map", "indefinite_length")
    rej("reject/mt7-additional-info-28", "a3012619018b033a0001018cfc", "reserved additional information", "malformed")
    rej("reject/mt7-break-as-value", "a3012619018b033a0001018cff", "break code as a value", "malformed")
    rej("reject/mt7-two-byte-simple-below-32", "a3012619018b033a0001018cf81f", "two-byte simple value 31", "malformed")
    rej("reject/mt7-truncated-float", "a3012619018b033a0001018cf93c", "half float cut off by the header end", "truncated")
    # self-check every accept row decodes to the stated size with our own encoder for the canonical ones
    assert rows[0]["hex"] == hx(protected_header(ALG_ES256, 8))
    assert rows[2]["hex"] == hx(protected_header(ALG_KS256, 8))
    assert rows[3]["hex"] == hx(protected_header(ALG_ES256, 39))
    assert rows[4]["hex"] == hx(protected_header(ALG_ES256, 1 << 40))
    assert rows[16]["hex"] == hx(protected_header(ALG_ES256, 8, [(cbor_int(-1), cbor_int(0)), (cbor_int(24), cbor_int(0))]))
    return rows


# --------------------------------------------------------------------------
# signed receipts under fixed keys
# --------------------------------------------------------------------------

ES256_PRIV = bytes.fromhex("c1" + "f1" * 31)
KS256_PRIV = bytes.fromhex("ac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80")  # Anvil account 0


def es256_signer():
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
    from cryptography.hazmat.primitives import hashes
    k = ec.derive_private_key(int.from_bytes(ES256_PRIV, "big"), ec.SECP256R1())
    pub = k.public_key().public_numbers()
    n = 0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551

    def sign(msg):
        der = k.sign(msg, ec.ECDSA(hashes.SHA256()))
        r, s = decode_dss_signature(der)
        if s > n // 2:
            s = n - s
        return r.to_bytes(32, "big") + s.to_bytes(32, "big"), r, s

    def verify(msg, r, s):
        from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
        k.public_key().verify(encode_dss_signature(r, s), msg, ec.ECDSA(hashes.SHA256()))

    return {"private_hex": hx(ES256_PRIV), "public_x_hex": pub.x.to_bytes(32, "big").hex(), "public_y_hex": pub.y.to_bytes(32, "big").hex()}, sign, verify, n


def ks256_signer():
    from eth_keys import keys
    from eth_hash.auto import keccak
    pk = keys.PrivateKey(KS256_PRIV)
    addr = pk.public_key.to_checksum_address()

    def sign(msg):
        digest = keccak(msg)
        sig = pk.sign_msg_hash(digest)
        r, s, v = sig.r, sig.s, sig.v + 27
        return r.to_bytes(32, "big") + s.to_bytes(32, "big") + bytes([v]), digest

    return {"private_hex": hx(KS256_PRIV), "address": addr, "public_x_hex": pk.public_key.to_bytes()[:32].hex(), "public_y_hex": pk.public_key.to_bytes()[32:].hex()}, sign


def receipts(db):
    es_key, es_sign, es_verify, n = es256_signer()
    ks_key, ks_sign = ks256_signer()
    rows, negs = [], []
    pairs = [(0, 1), (7, 8), (4, 7), (7, 15), (26, 39)]
    for s1, s2 in pairs:
        acc, paths = proof_for(db, s1, s2)
        roots, nright = alg.consistent_roots_for_sizes(s1, s2, acc, paths)
        target = [db.get(i) for i in alg.peaks(s2 - 1)]
        right = target[len(roots):]
        payload = b"".join(target)
        proof_b = consistency_proof_bstr(s1, s2, paths, right)
        for alg_id, alg_name in ((ALG_ES256, "ES256"), (ALG_KS256, "KS256")):
            ph = protected_header(alg_id, s2)
            ss = sig_structure(ph, payload)
            if alg_id == ALG_ES256:
                digest = hashlib.sha256(ss).digest()
                sig, r, s = es_sign(ss)
                es_verify(ss, r, s)
                extra = {}
            else:
                sig, digest = ks_sign(ss)
                extra = {"signer_kind": "eoa"}
            rows.append({
                "name": f"{alg_name.lower()}/{s1}-to-{s2}",
                "alg": alg_id, "alg_name": alg_name,
                "tree_size_1": s1, "tree_size_2": s2,
                "protected_header_hex": hx(ph),
                "consistency_proof_hex": hx(proof_b),
                "detached_payload_hex": hx(payload),
                "sig_structure_hex": hx(ss),
                "message_digest_hex": hx(digest),
                "digest_alg": "sha256" if alg_id == ALG_ES256 else "keccak256",
                "signature_hex": hx(sig),
                "receipt_cbor_hex": hx(receipt_cbor(ph, proof_b, sig)),
                **extra,
            })
    # negatives, ES256 over 7 -> 8
    acc, paths = proof_for(db, 7, 8)
    target = [db.get(i) for i in alg.peaks(7)]
    payload = b"".join(target)
    right = target[len(alg.consistent_roots_for_sizes(7, 8, acc, paths)[0]):]
    proof_b8 = consistency_proof_bstr(7, 8, paths, right)
    # (a) header signed for size 10, proof declares 8: signature valid, sizes disagree
    ph10 = protected_header(ALG_ES256, 10)
    sig10, _, _ = es_sign(sig_structure(ph10, payload))
    negs.append({"name": "reject/signed-size-10-declared-8", "alg": ALG_ES256, "tree_size_1": 7,
                 "protected_header_hex": hx(ph10), "consistency_proof_hex": hx(proof_b8), "detached_payload_hex": hx(payload),
                 "signature_hex": hx(sig10), "receipt_cbor_hex": hx(receipt_cbor(ph10, proof_b8, sig10)),
                 "expect": {"result": "reject", "reason": "signed_size_mismatch"},
                 "note": "the signature verifies over {..., -65933: 10} and this payload; the proof's tree_size_2 is 8"})
    # (a2) the FOR-568 replay: the genuine 7 -> 8 receipt with the proof re-declared as 7 -> 10.
    # Both targets have one right peak, so the fold cannot tell them apart; only the signed size does.
    ph8 = protected_header(ALG_ES256, 8)
    sig8, _, _ = es_sign(sig_structure(ph8, payload))
    proof_b10 = consistency_proof_bstr(7, 10, paths, right)
    negs.append({"name": "reject/replay-7-to-8-declared-7-to-10", "alg": ALG_ES256, "tree_size_1": 7,
                 "protected_header_hex": hx(ph8), "consistency_proof_hex": hx(proof_b10), "detached_payload_hex": hx(payload),
                 "signature_hex": hx(sig8), "receipt_cbor_hex": hx(receipt_cbor(ph8, proof_b10, sig8)),
                 "expect": {"result": "reject", "reason": "signed_size_mismatch"},
                 "note": "the FOR-568 substitution: byte-identical paths, right peak and signature, tree_size_2 declared 10; sizes 8 and 10 both take one right peak so the fold accepts either, and only the signed size rejects it"})
    # (b) header without the label, otherwise valid (pre-ADR-0066 sealer)
    ph_old = cbor_map([(cbor_int(LABEL_ALG), cbor_int(ALG_ES256)), (cbor_int(LABEL_VDS), cbor_int(VDS_MMR_CONSISTENCY))])
    sig_old, _, _ = es_sign(sig_structure(ph_old, payload))
    negs.append({"name": "reject/signed-size-absent", "alg": ALG_ES256, "tree_size_1": 7,
                 "protected_header_hex": hx(ph_old), "consistency_proof_hex": hx(proof_b8), "detached_payload_hex": hx(payload),
                 "signature_hex": hx(sig_old), "receipt_cbor_hex": hx(receipt_cbor(ph_old, proof_b8, sig_old)),
                 "expect": {"result": "reject", "reason": "signed_size_missing"},
                 "note": "a valid pre-ADR-0066 receipt: {1: -7, 395: 3} signed over the same payload"})
    # (c) payload is sha256(concat) rather than the raw concat
    sig_h, _, _ = es_sign(sig_structure(ph8, hashlib.sha256(payload).digest()))
    negs.append({"name": "reject/payload-is-hashed-accumulator", "alg": ALG_ES256, "tree_size_1": 7,
                 "protected_header_hex": hx(ph8), "consistency_proof_hex": hx(proof_b8), "detached_payload_hex": hx(payload),
                 "signature_hex": hx(sig_h), "receipt_cbor_hex": hx(receipt_cbor(ph8, proof_b8, sig_h)),
                 "expect": {"result": "reject", "reason": "signature_invalid"},
                 "note": "signed over sha256(peaks) instead of the raw concatenation (ADR-0046)"})
    # (d) high-s ES256 over the correct structure
    ss8 = sig_structure(ph8, payload)
    sig_ok, r, s = es_sign(ss8)
    s_high = n - s
    sig_high = r.to_bytes(32, "big") + s_high.to_bytes(32, "big")
    negs.append({"name": "reject/es256-high-s", "alg": ALG_ES256, "tree_size_1": 7,
                 "protected_header_hex": hx(ph8), "consistency_proof_hex": hx(proof_b8), "detached_payload_hex": hx(payload),
                 "signature_hex": hx(sig_high), "receipt_cbor_hex": hx(receipt_cbor(ph8, proof_b8, sig_high)),
                 "expect": {"result": "reject", "reason": "signature_malleable"},
                 "note": "mathematically valid ECDSA with s > n/2; verifiers require low-s"})
    return {"es256": es_key, "ks256": ks_key}, rows, negs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--go-kat")
    a = ap.parse_args()
    db, tree, sizes = build_tree()
    if a.go_kat:
        check_against_go(tree, a.go_kat)
    pairs = [pair_row(db, s1, s2) for s1 in [0] + sizes for s2 in sizes if s2 > s1]
    keys, rcpts, rneg = receipts(db)
    out = {
        "version": 1,
        "description": "Checkpoint receipt of consistency KAT over the canonical 39-node MMR: tree, size-driven fold (consistent_roots_for_sizes), rejected proof shapes, protected-header classes (ADR-0066 D9), and signed receipts under fixed test keys.",
        "generator": "robinbryce/merkle-mountain-range-proofs scripts/gen_checkpoint_receipt_kat39.py",
        "conventions": {
            "hex": "unprefixed lowercase",
            "sizes": "node counts; MMR(size) has size nodes; tree_size_1 = 0 is the empty origin",
            "protected_header": "deterministic CBOR map {1: alg, 395: 3, -65933: tree_size_2}, keys ordered shorter-encoding-first then bytewise",
            "detached_payload": "raw concatenation of the accumulator peaks of tree_size_2, descending height, no framing",
            "sig_structure": "['Signature1', bstr(protected), bstr(''), bstr(payload)] as CBOR",
            "es256": "ECDSA P-256 over sha256(sig_structure); signature r||s, 64 bytes, low-s",
            "ks256": "ECDSA secp256k1 over keccak256(sig_structure); signature r||s||v, 65 bytes, v in {27, 28}; verifier recovers the address",
            "receipt": "CBOR tag 18 [bstr(protected), {396: {-2: bstr(consistency_proof)}}, null, bstr(signature)]",
            "consistency_proof": "bstr(CBOR [tree_size_1, tree_size_2, [[bstr path node]...], [bstr right peak]...])",
        },
        "tree": tree,
        "consistency_pairs": pairs,
        "consistency_negatives": negatives(db),
        "protected_headers": header_rows(),
        "keys": keys,
        "receipts": rcpts,
        "receipt_negatives": rneg,
    }
    json.dump(out, sys.stdout, indent=1)
    sys.stdout.write("\n")
    print(f"pairs={len(pairs)} negatives={len(out['consistency_negatives'])} headers={len(out['protected_headers'])} receipts={len(rcpts)} receipt_negatives={len(rneg)}", file=sys.stderr)


if __name__ == "__main__":
    main()
