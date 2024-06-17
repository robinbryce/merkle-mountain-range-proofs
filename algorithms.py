from typing import List

def peaks(s) -> List[int]:
    """Returns the peak indices for MMR(s)

    Assumes MMR(s) is complete, implementations can check for this condition by testing the height of s+1 
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

