
"""
See the notational conventions in the accompanying draft text for definition of short hand variables.
"""
import hashlib

from algorithms import consistency_proof
from algorithms import verify_consistency
from algorithms import index_proof_path
from algorithms import verify_inclusion_path
from algorithms import index_height
from algorithms import peaks
from algorithms import peaks_bitmap
from algorithms import peak_index
from algorithms import complete_mmr_size
from algorithms import hash_pospair64


def hash_num64(v :int) -> bytes:
    """
    Compute the SHA-256 hash of v

    Args:
        v (int): assumed to be an unsigned integer using at most 64 bits
    Returns:
        bytes: the SHA-256 hash of the big endian representation of v
    """
    return hashlib.sha256(v.to_bytes(8, byteorder='big', signed=False)).digest()

class KatDB:
    def __init__(self):
        # A map is used so we can build the tree in layers, with explicit put()
        # calls, for illustrative purposes In a more typical implementation,
        # this would just be a list.
        self.store = {}

    def parent_hash(self, iparent: int, ileft: int, iright: int) -> bytes:
        vleft = self.store[ileft]
        vright = self.store[iright]
        return hash_pospair64(iparent+1, vleft, vright)

    def put(self, i :int, v: bytes):
        self.store[i] = v

    def get(self, i) -> bytes:
        return self.store[i]


    def init_canonical39(self):
        """
        Initialise the db to the canonical MMR(39) which is,

            4                         30


            3              14                       29
                         /    \
                      /          \
            2        6            13           21             28                37
                   /   \        /    \
            1     2     5      9     12     17     20     24       27       33      36
                 / \   / \    / \   /  \   /  \
            0   0   1 3   4  7   8 10  11 15  16 18  19 22  23   25   26  31  32   34  35   38
                0   1 2   3  4   5  6   7  8   9 10  11 12  13   14   15  16  17   18  19   20

        """

        self.store = {}

        # height 0 (the leaves)
        self.put(0, hash_num64(0))
        self.put(1, hash_num64(1))
        self.put(3, hash_num64(3))
        self.put(4, hash_num64(4))
        self.put(7, hash_num64(7))
        self.put(8, hash_num64(8))
        self.put(10, hash_num64(10))
        self.put(11, hash_num64(11))
        self.put(15, hash_num64(15))
        self.put(16, hash_num64(16))
        self.put(18, hash_num64(18))
        self.put(19, hash_num64(19))
        self.put(22, hash_num64(22))
        self.put(23, hash_num64(23))
        self.put(25, hash_num64(25))
        self.put(26, hash_num64(26))
        self.put(31, hash_num64(31))
        self.put(32, hash_num64(32))
        self.put(34, hash_num64(34))
        self.put(35, hash_num64(35))
        self.put(38, hash_num64(38))

        # height 1
        self.put(2, self.parent_hash(2, 0, 1))
        self.put(5, self.parent_hash(5, 3, 4))
        self.put(9, self.parent_hash(9, 7, 8))
        self.put(12, self.parent_hash(12, 10, 11))
        self.put(17, self.parent_hash(17, 15, 16))
        self.put(20, self.parent_hash(20, 18, 19))
        self.put(24, self.parent_hash(24, 22, 23))
        self.put(27, self.parent_hash(27, 25, 26))
        self.put(33, self.parent_hash(33, 31, 32))
        self.put(36, self.parent_hash(36, 34, 35))

        # height 2
        self.put(6, self.parent_hash(6, 2, 5))
        self.put(13, self.parent_hash(13, 9, 12))
        self.put(21, self.parent_hash(21, 17, 20))
        self.put(28, self.parent_hash(28, 24, 27))
        self.put(37, self.parent_hash(37, 33, 36))

        # height 3
        self.put(14, self.parent_hash(14, 6, 13))
        self.put(29, self.parent_hash(29, 21, 28))

        # height 4
        self.put(30, self.parent_hash(30, 14, 29))

def print_canonical39_leaves():
    db = KatDB()
    db.init_canonical39()
    print("|" + "  i " + "|" + "  e " + "|" + "|" + " "*(32-5-1) + "leaf values" + " "*(32-5))
    print("|:" + "-"*3 + "|" + "-"*3 + ":|" + "|" + "-"*64 )

    leaf_indices = [0, 1, 3, 4, 7, 8, 10, 11, 15, 16, 18, 19, 22, 23, 25, 26, 31, 32, 34, 35, 38]
    for e in range(21):
        i = leaf_indices[e]
        print("|" + '{:4}'.format(i) + "|" + '{:4}'.format(e) + "|" + db.store[i].hex() + "|")

def print_canonical39():
    db = KatDB()
    db.init_canonical39()

    print("|" + " i  " + "|" + " "*(32-5-1) + "node values" + " "*(32-5) + "|")
    print("|" + "-"*3 + ":|" + "-"*64 + "|")
    for i in range(39):
        print("|" + '{:4}'.format(i) + "|" + db.store[i].hex() + "|")

def print_canonical39_accumulator_peaks(db=None):
    # there is a complete mmr for each leaf
    complete_mmrs = [1, 3, 4, 7, 8, 10, 11, 15, 16, 18, 19, 22, 23, 25, 26, 31, 32, 34, 35, 38, 39]
    # leaf_indices= [0, 1, 2, 3, 4,  5,  6,  7,  8,  9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]

    id_head = " S "
    if db:
        id_head = " S-1  "
    print("|" + id_head + "|" + " "*8 + "accumulator peaks" + " " + "|")
    print("|" + "-"*4 + "|" + "-"*32 + "|")

    offset = 0
    if db:
        offset = 1

    for i in range(len(complete_mmrs)):
        s = complete_mmrs[i]
        peak_values = peaks(s) # returns a list of positions, not indices
        if db:
            peak_values = ['"' + "" + db.get(p-1).hex() + '"'  for p in peak_values]
        else:
            peak_values = [str(p) for p in peak_values]

        print("|" + '{:4}'.format(complete_mmrs[i]-offset) + "| " + ", ".join(peak_values))
        # adjust to generate kat tables for particular languages.
        #print('{%d, []string{%s}},' % (complete_mmrs[i]-offset, ", ".join(peak_values)))

def print_canonical39_index_height():

    # print("|  i |  g |")
    # print("|:---|---:|")
    heights = []
    indices = []
    heading = []
    peakmaps = []
    leafcounts = []
    w = 5
    for i in range(39):
        indices.append(str(i).ljust(w, " "))
        heading.append("-" * w)
        heights.append(str(index_height(i)).ljust(w, " "))
        peakmap = peaks_bitmap(i+1)
        peakmaps.append(bin(peakmap)[2:].ljust(w, " "))
        leafcounts.append(str(peakmap).ljust(w, " "))

    print("|" + "|".join(indices) + "|")
    print("|" + "|".join(heading) + "|")
    print("|" + "|".join(heights) + "|")
    print("|" + "|".join(leafcounts) + "|")
    print("|" + "|".join(peakmaps) + "|")
    # print("|{:4}|".format(index_height(i)))
    # print("|{:4}|".format(i, index_height(i)))

def print_canonical39_inclusion_paths():
    # note we produce inclusion paths for _all_ nodes

    max_accumulator = peaks(39)
    smax_accumulator =  "[" + ", ".join([str(p-1) for p in max_accumulator]) + "]"
    print("|" + " i  " + "|" + " s  " + "|" + "min inclusion paths" + "|" + "min accumulator" + "|" + "max inclusion paths" + "|" + smax_accumulator.ljust(20, " ") + "|")
    print("|:" + "-".ljust(3, "-") + "|" + "-".ljust(3, "-") + ":|" + "-".ljust(20, "-") + "|" + "-".ljust(20, "-") + "|")

    for i in range(39):
        s = complete_mmr_size(i)
        accumulator = peaks(s)
        path = index_proof_path(s, i)
        spath = "[" + ", ".join([str(p) for p in path]) + "]"
        path_39 = index_proof_path(39, i)
        spath_39 = "[" + ", ".join([str(p) for p in path_39]) + "]"

        # it is very confusingif we list the accumulator as positions yet have the paths be indices. so lets not do that.
        saccumulator = "[" + ", ".join([str(p-1) for p in accumulator]) + "]"
        
        print("|" + '{:4}'.format(i) + "|" + 'MMR({})'.format(s).ljust(7, " ") + "|" + spath.ljust(20, " ") + "|" + saccumulator.ljust(20, " ") + "|" + spath_39.ljust(20, " ") + "|" + smax_accumulator.ljust(20, " ") + "|")

def print_canonical39_inclusion_paths2():
    # note we produce inclusion paths for _all_ nodes

    # so we can print the roots
    db = KatDB()
    db.init_canonical39()

    w1 = 4
    w2 = 20

    print("|" + " i  " + "|" + " MMR  " + "|" + "inclusion path" + "|" + "accumulator" + "|" + "accumulator root index" + "|" + "root" + "|")
    print("|:" + "-".ljust(w1-1, "-") + "|" + "-".ljust(w1-1, "-") + ":|" + "-".ljust(w2, "-") + "|" + "-".ljust(w2, "-") + "|" + "-".ljust(w1, "-") + "|" + "-".ljust(w1, "-") + "|")

    for i in range(39):
        s = complete_mmr_size(i)
        while s < 39:
            accumulator = peaks(s)
            path = index_proof_path(s, i)
            e = peaks_bitmap(s)

            # for leaf nodes, the peak height is len(proof) - 1, for interiors, we need to take into account the height of the node.
            g = len(path) + index_height(i)

            accumulator_index = peak_index(e, g)

            spath = "[" + ", ".join([str(p) for p in path]) + "]"

            # it is very confusingif we list the accumulator as positions yet have the paths be indices. so lets not do that.
            saccumulator = "[" + ", ".join([str(p-1) for p in accumulator]) + "]"

            sroot = db.get(accumulator[accumulator_index]).hex()
        
            print(
                "|" + '{:4}'.format(i) +
                "|" + 'MMR({})'.format(s).ljust(7, " ") +
                "|" + spath.ljust(w2, " ") +
                "|" + saccumulator.ljust(w2, " ") +
                "|" + str(accumulator_index).ljust(w1, " ") +
                "|" + sroot + "|")
 
            s = complete_mmr_size(s+1)


def test_verify_inclusion():
    # Hand populate the db
    db = KatDB()
    db.init_canonical39()

    # Show that index_proof_path verifies for all complete mmr's which include i
    failcount = 0
    for i in range(39):
        s = complete_mmr_size(i)
        while s < 39:

            # typically, the size, accumulator and paths will be givens.
            accumulator = [db.get(p-1) for p in peaks(s)]
            saccumulator = [str(p-1) for p in peaks(s)]
            path = [db.get(isibling) for isibling in index_proof_path(s, i)]
            ipath = [str(isibling) for isibling in index_proof_path(s, i)]

            e = peaks_bitmap(s)

            # for leaf nodes, the peak height is len(proof) - 1,
            # for interiors, we need to take into account the height of the node.
            g = len(path) + index_height(i)

            accumulator_index = peak_index(e, g)

            ok, pathconsumed = False, 0

            (ok, pathconsumed) = verify_inclusion_path(s, i, db.get(i), path, accumulator[accumulator_index])

            if ok and pathconsumed == len(path):
                print("|" + "OK".ljust(4, " ") + "|" + str(i).ljust(4, " ") + "|" + str(s).ljust(4, " ") + "|")
            else:
                print(
                    "|" + "FAIL".ljust(4, " ") +
                    "|" + str(i).ljust(4, " ") +
                    "|" + str(s).ljust(4, " ") +
                    "|[" + ", ".join(ipath) + "]" +
                    "|" + str(accumulator_index).ljust(4, " ") + 
                    "|[" + ", ".join(saccumulator) + "]")

                failcount += 1
                return

            s = complete_mmr_size(s+1)

    if failcount == 0:
        print("OK")
    else:
        print("FAILED to verify %d" % failcount)


def test_verify_consistency():

    # Hand populate the db
    db = KatDB()
    db.init_canonical39()

    for stride in range(int(39/2)):
        stride = (stride + 1)
        sizea = 1
        sizeb = complete_mmr_size(min(sizea + stride, 39))

        while sizeb <=39 and (sizeb - sizea > 0):
            iproof = consistency_proof(sizea, sizeb)
            proof = [db.get(i) for i in iproof]
            iaacc = [p -1 for p in peaks(sizea)]
            aacc = [db.get(i) for i in iaacc]
            ibacc = [p - 1 for p in peaks(sizeb)]
            bacc = [db.get(i) for i in ibacc]

            ok = verify_consistency(sizea, sizeb, aacc, bacc, proof)
            if not ok:
                ok = verify_consistency(sizea, sizeb, aacc, bacc, proof)
                print("FAILED: MMR(%d) -> MMR(%d)" % (sizea, sizeb))
                return
            print("OK: MMR(%d) -> MMR(%d)" % (sizea, sizeb))
            sizea = complete_mmr_size(sizea + stride)
            sizeb = complete_mmr_size(sizea + 2 *stride)


import sys
if __name__ == "__main__":
    test_verify_consistency()
    sys.exit(0)
    print_canonical39_inclusion_paths2()
    test_verify_inclusion()
    print_canonical39_index_height()
    db = KatDB()
    db.init_canonical39()
    print_canonical39_accumulator_peaks(db=db)
    print_canonical39_leaves()
    print()
    print_canonical39()
    print()
    print_canonical39_accumulator_peaks()
    # print_canonical39_accumulator_peaks(as_indices=True)