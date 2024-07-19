"""Variations on inclusion and consistency algorithms

The differences are:

* The roots are verified inline. This isn't compatible with the detached payload
  approach for the COSE Receipts draft.
* The consistency proof is a single flat array to align with the example in the
  COSE Receipts draft. This results in a less obvious implementation. accomodate
  the original "flat list" form of consistency proofs in the COSE Receipts
  example.
"""
from typing import List, Tuple
import hashlib

from algorithms import inclusion_proof_path
from algorithms import peaks, index_height, hash_pospair64

def verify_inclusion_path(
    i: int, nodehash: bytes, proof: List[bytes], root: bytes
) -> Tuple[bool, int]:
    """
    Args:
        i (int): The mmr index where `nodehash` is located.
        nodehash (bytes): The value whose inclusion is being proven.
        proof (List[bytes]): The siblings required to produce `root` from `nodehash`.
        root (bytes): The peak from the accumulator which includes node `i`.

    Returns:
        A tuple  (bool, int), where the bool is True if `root` was produced and
        the int is the count of path elements required to do so.
    """
    # 1. If the proof length is zero and the leaf is equal the root, succeed
    if len(proof) == 0 and nodehash == root:
        return (True, 0)

    # 1. Set `g` to `IndexHeight(i)`
    g = index_height(i)

    # 1. Set elementHash to the value whose inclusion is to be proven
    elementhash = nodehash

    # 1. For each pathItem with index iProof in proof
    for iproof, pathitem in enumerate(proof):
        # 1. if `IndexHeight(i+1)` is greater than `g`
        if index_height(i + 1) > g:
            # 1. Set `i` to `i + 1`
            i = i + 1
            # 1. Set `elementHash` = `H(i+1 || pathItem || elementHash)`
            elementhash = hash_pospair64(i + 1, pathitem, elementhash)
        else:
            # 1. Set `i` to `i + (2^(g+1))`
            i = i + (2 << g)
            # 1. Set `elementHash` to `H(i+1 || elementHash || pathItem)`
            elementhash = hash_pospair64(i + 1, elementhash, pathitem)

        # 1. Compare root to `elementHash`.
        if elementhash == root:
            # If root is equal, we have shown that index items from proof have
            # proven inclusion of the value at the initial value for `i`.  Return
            # index to the caller and indicate success.
            return (True, iproof + 1)
        # 1. Increment `g`
        g = g + 1

    # 1. We have consumed the proof without producing the root, fail the verification.
    return (False, len(proof))


def consistency_proof_flat(ifrom : int, ito: int) -> List[int]:
    """Returns a proof of consistency between the MMR's identified by ifrom and ito.

    The returned path is the concatenation of the inclusion proofs
    authenticating the peaks of MMR(ifrom) in MMR(ito)
    """
    apeaks = peaks(ifrom)

    proof = []

    for ipeak in apeaks:
        proof.extend(inclusion_proof_path(ipeak, ito))

    return proof

def verify_consistency_flat(
    ifrom: int,
    ito: int,
    accumulatorfrom: List[bytes],
    accumulatorto: List[bytes],
    path: List[bytes],
) -> bool:
    """ """
    frompeaks = peaks(ifrom)
    topeaks = peaks(ito)

    if len(accumulatorfrom) != len(frompeaks):
        return False

    if len(accumulatorto) != len(topeaks):
        return False

    ipeakfrom = ipeakto = 0

    ia = frompeaks[ipeakfrom]

    ok = False
    while ipeakfrom < len(accumulatorfrom):
        ib = topeaks[ipeakto]

        while ia <= ib:
            if ia == ib:
                ok = accumulatorfrom[ipeakfrom] == accumulatorto[ipeakto]
            else:
                (ok, used) = verify_inclusion_path(
                    ia, accumulatorfrom[ipeakfrom], path, accumulatorto[ipeakto]
                )
                if used == 0 or used > len(path):
                    return False
                path = path[used:]

            if not ok:
                return False

            ipeakfrom += 1
            if ipeakfrom == len(accumulatorfrom):
                break
            ia = frompeaks[ipeakfrom]

        ipeakto += 1

    return ok and len(path) == 0 
 