from typing import List, Tuple
import hashlib

def consistency_proof(asize: int, bsize: int) -> List[int]:
    """Returns a proof of consistency between the MMR's identified by asize and bsize.

    The returned path is the concatenation of the inclusion proofs
    authenticating the peaks of MMR(a) in MMR(b)
    """
    apeaks = peaks(asize)

    proof = []

    for apos in apeaks:
        proof.extend(index_proof_path(bsize, apos-1))

    return proof

def verify_consistency(
        asize: int, bsize: int,
        aaccumulator: List[bytes], baccumulator: List[bytes],
        path: List[bytes]) -> bool:
    """
    """
    apeakpositions = peaks(asize)
    bpeakpositions = peaks(bsize)

    if len(aaccumulator) != len(apeakpositions):
        return False
    
    if len(baccumulator) != len(bpeakpositions):
        return False

    ipeaka = ipeakb = 0

    apos = apeakpositions[ipeaka]

    ok = False
    while ipeaka < len(aaccumulator):
        bpeak = bpeakpositions[ipeakb]
        while apos  <= bpeak:
            (ok, used) = verify_inclusion_path(
                bsize, aaccumulator[ipeaka], apos-1,
                path, baccumulator[ipeakb])
            if not (ok or used > len(path)):
                return False
            path = path[used:]
            ipeaka += 1
            if ipeaka == len(aaccumulator):
                break
            apos = apeakpositions[ipeaka]
        ipeakb += 1

    return ok and len(path) == 0



def verify_inclusion_path(s: int, i: int, nodehash: bytes, proof: List[bytes], root: bytes) -> Tuple[bool, int]:
    """
    Args:
        s (int): The size of the MMR providing the accumulator `root`
        i (int): The mmr index where `nodehash` is located
        proof (List[bytes]): The siblings required to produce `root` from `nodehash`
        root (bytes): The peak from the accumulator for MMR(s) which includes node `i`

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
            elementhash = hash_pospair64(i+1, pathitem, elementhash)
        else:
            # 1. Set `i` to `i + (2 << g)`
            i = i + (2 << g)
            # 1. Set `elementHash` to `H(i+1 || elementHash || pathItem)`
            elementhash = hash_pospair64(i+1, elementhash, pathitem)
        
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


def index_proof_path(s, i) -> List[int]:
    """Returns the list of node indices proving inclusion of i"""

    # 1. Set the path to the empty list
    path = []
    # 1. Set `g` to `IndexHeight(i)`
    g = index_height(i)

    # 1. Repeat until #termination_condition evaluates true
    while True:

        isibling = None # lexical scopes

        # 1. Set iLocalPeak to `i`
        ilocalpeak = i
        # 1. if `IndexHeight(i+1)` is greater than `g`
        if index_height(i+1) > g:
            # 1. Set `iSibling` to `iLocalPeak - SiblingOffset(g)`
            isibling = ilocalpeak - ((2 << g) -1)
            # 1. Set `i` to `i+1`
            i = i + 1
        else:
            # 1. Set `iSibling` to `iLocalPeak + SiblingOffset(g)` 
            isibling = ilocalpeak + ((2 << g) -1)
            # 1. Set `i` to `i` + `2 << g`
            i = i + (2 << g)

        # If `iSibling` is greater or equal to `S` (#termination_condition)
        if isibling >= s:
            # Return the current path to the caller, terminating the algorithm.
            return path
        # 1. Append the current pathElement to the proof.
        path.append(isibling)
        # 1. Increment the index height `g`
        g = g + 1

def index_height(i: int) -> int:
    """Returns the 0 based height of the mmr entry indexed by i"""
    # convert the index to a position to take advantage of the bit patterns afforded
    pos = i + 1
    while not all_ones(pos):
      pos = pos - (most_sig_bit(pos) - 1)

    return pos.bit_length() - 1

def peaks(s: int) -> List[int]:
    """Returns the peak indices for MMR(s)

    Assumes MMR(s) is complete, implementations can check for this condition by
    testing the height of s+1 
    """

    peak = 0
    peaks = []
    while s != 0:
        # find the highest peak size in the current MMR(s)
        highest_size = (1 <<((s +1).bit_length()-1)) - 1
        peak = peak + highest_size
        peaks.append(peak)
        s -= highest_size

    return peaks

def peaks_bitmap(s: int) -> int:
    """Returns a mask with a bit set for each peak,
    
    The resulting binary value is also the count of leaves contained in the
    largest complete MMR included in, or equal to, s
    """
    if s == 0:
        return 0
    
	# peakSize := (uint64(1) << bits.Len64(mmrSize)) - 1
    peaksize = (1 << s.bit_length()) - 1
    peakmap = 0
    while peaksize > 0:
        peakmap <<= 1
        if s >= peaksize:
            s -= peaksize
            peakmap |= 1
        peaksize >>= 1

    return peakmap


def peak_index(e:int, g:int) -> int:
    """Return the packed accumulator index for the inclusion proof of e in MMR(s)

    Where e = peaks_bitmap(s)

    Args:
        e (int): the leaf count
        g (int): the height index of the smallest complete mmr peak containing e
    Returns:
        The index into the accumulator
    """
    return (e & ~((1 << g)-1)).bit_count() - 1

# various bit primitives that typically have efficient implementations for 64 bit integers

def most_sig_bit(pos) -> int:
    """Returns the mask for the the most significant bit in pos"""
    return 1 << (pos.bit_length() - 1)

def all_ones(pos) -> bool:
    """Returns true if all bits, starting with the most significant, are 1"""
    imsb = pos.bit_length() - 1
    mask = (1 << (imsb+1)) - 1
    return pos == mask

def trailing_zeros(v: int) -> int:
    """
    returns the count of 0 bits after the least significant set bit
    returns -1 if v is 0
    """
    # https://stackoverflow.com/a/63552117/13846602
    return (v & -v).bit_length() - 1


# generally useful helpers for the testvectors

def hash_pospair64(pos: int, a: bytes, b: bytes) -> bytes:
    """
    Compute the hash of  pos || a || b

    Args:
        pos (int): the 1-based position of an mmr node. If a, b are left and
            right childre, pos should be the parent position.
        a (bytes): the first value to include in the hash
        b (bytes): the second value to include in the hash

    Returns:
        The value for the node identified by pos
    """
    h = hashlib.sha256()
    h.update(pos.to_bytes(8, byteorder='big', signed=False))
    h.update(a)
    h.update(b)
    return h.digest()


def complete_mmr_size(i) -> int:
    """Returns the smallest complete mmr size which contains node index i"""

    h0 = index_height(i)
    h1 = index_height(i + 1)
    while h0 < h1:
        i+= 1
        h0 = h1
        h1 = index_height(i + 1)

    return i + 1