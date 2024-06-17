from typing import List

def index_height(i) -> int:
    """Returns the 0 based height of the mmr entry indexed by i"""
    # convert the index to a position to take advantage of the bit patterns afforded
    pos = i + 1
    while not all_ones(pos):
      pos = pos - (most_sig_bit(pos) - 1)

    return pos.bit_length() - 1


def peaks(s) -> List[int]:
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

def complete_mmr_size(i) -> int:
    """Returns the smallest complete mmr size which contains node index i"""

    h0 = index_height(i)
    h1 = index_height(i + 1)
    while h0 < h1:
        i+= 1
        h0 = h1
        h1 = index_height(i + 1)

    return i + 1


# various bit primitives that typically have very efficient implementations for 64 bit integers

def most_sig_bit(pos) -> int:
    """Returns the mask for the the most significant bit in pos"""
    return 1 << (pos.bit_length() - 1)

def all_ones(pos) -> bool:
    """Returns true if all bits, starting with the most significant, are 1"""
    imsb = pos.bit_length() - 1
    mask = (1 << (imsb+1)) - 1
    return pos == mask

