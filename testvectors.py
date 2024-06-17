import hashlib

"""
See the notational conventions in the accompanying draft text for definition of short hand variables.
"""

from algorithms import peaks

def hash_num64(v :int) -> bytes:
    """
    Compute the SHA-256 hash of v

    Args:
        v (int): assumed to be an unsigned integer using at most 64 bits
    Returns:
        bytes: the SHA-256 hash of the big endian representation of v
    """
    return hashlib.sha256(v.to_bytes(8, byteorder='big', signed=False)).digest()

def hash_pospair64(pos: int, vleft: bytes, vright: bytes) -> bytes:
    """
    Compute the hash of the node at pos, whose children have the values vleft and vright.

    Args:
        pos (int): the 1-based position of the parent of vleft, vright in the tree
        vleft (bytes): the value of the left child of pos
        vright (bytes): the value of the right child of pos

    Returns:
        The value for the node identified by pos
    """
    h = hashlib.sha256()
    h.update(pos.to_bytes(8, byteorder='big', signed=False))
    h.update(vleft)
    h.update(vright)
    return h.digest()


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

    id_head = " pos"
    if db:
        id_head = " i  "
    print("|" + id_head + "|" + " "*8 + "accumulator peaks" + " " + "|")
    print("|" + "-"*4 + "|" + "-"*32 + "|")

    offset = 1
    if db:
        offset = 0

    for i in range(len(complete_mmrs)):
        s = complete_mmrs[i]
        peak_values = peaks(s) # returns a list of positions, not indices
        if db:
            peak_values = [db.get(p-1).hex() for p in peak_values]
        else:
            peak_values = [str(p) for p in peak_values]

        print("|" + '{:4}'.format(i+offset) + "| " + ", ".join(peak_values))



if __name__ == "__main__":
    print_canonical39_leaves()
    print()
    print_canonical39()
    print()
    print_canonical39_accumulator_peaks()
    db = KatDB()
    db.init_canonical39()
    print_canonical39_accumulator_peaks(db=db)
    # print_canonical39_accumulator_peaks(as_indices=True)