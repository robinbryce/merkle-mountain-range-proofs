from algorithms import inclusion_proof_path
from algorithms import index_height
from algorithms import peaks
from algorithms import leaf_count
from algorithms import complete_mmr_size
from algorithms import mmr_index
from algorithms import parent
from algorithms import next_proof, next_leaf_proof
from algorithms import accumulator_root
from algorithms import accumulator_index


from db import KatDB, FlatDB

complete_mmrs = [
    1,
    3,
    4,
    7,
    8,
    10,
    11,
    15,
    16,
    18,
    19,
    22,
    23,
    25,
    26,
    31,
    32,
    34,
    35,
    38,
    39,
]


def kat39_leaf_table():
    """Returns a row for each leaf entry [mmrIndex, leafIndex, leafHash]"""
    db = KatDB()
    db.init_canonical39()
    leaf_indices = [
        0,
        1,
        3,
        4,
        7,
        8,
        10,
        11,
        15,
        16,
        18,
        19,
        22,
        23,
        25,
        26,
        31,
        32,
        34,
        35,
        38,
    ]
    rows = []
    for e in range(21):
        i = leaf_indices[e]
        rows.append([i, e, db.store[i].hex()])

    return rows


def print_leaves_kat39():
    print(
        "|"
        + "  i "
        + "|"
        + "  e "
        + "|"
        + " " * (32 - 5 - 1)
        + "leaf values"
        + " " * (32 - 5)
        + "|"
    )
    print("|:" + "-" * 3 + "|" + "-" * 3 + ":|" + "-" * 64 + "|")
    for r in kat39_leaf_table():
        print("|" + "{:4}".format(r[0]) + "|" + "{:4}".format(r[1]) + "|" + r[2] + "|")


def _print_db(*dbs):
    print(
        ("|" + " i  " + "|" + " " * (32 - 5 - 1) + "node values" + " " * (32 - 5) + "|")
        * len(dbs)
    )
    print(("|" + "-" * 3 + ":|" + "-" * 64 + "|") * len(dbs))

    for i in range(39):
        for db in dbs:
            sys.stdout.write("|" + "{:4}".format(i) + "|" + db.store[i].hex() + "|")
        sys.stdout.write("\n")


def print_kat39():
    db = KatDB()
    db.init_canonical39()
    _print_db(db)


def peaks_table(db=None):
    rows = []
    for i in range(len(complete_mmrs)):
        s = complete_mmrs[i]
        peak_values = peaks(s)  # returns a list of positions, not indices
        if db:
            rows.append([db.get(p - 1).hex() for p in peak_values])
            continue
        peak_values = [p for p in peak_values]
        rows.append(peak_values)

    return rows


def print_39_accumulators(db=None):
    rows = peaks_table(db)

    id_head = " S "
    if db:
        id_head = " S-1  "
    print("|" + id_head + "|" + " " * 8 + "accumulator peaks" + " " + "|")
    print("|" + "-" * 4 + "|" + "-" * 32 + "|")

    offset = 0
    if db:
        offset = 1

    for i, peak_values in enumerate(rows):
        print(
            "|"
            + "{:4}".format(complete_mmrs[i] - offset)
            + "| "
            + ", ".join([str(p) for p in peak_values])
            + "| "
        )
        # adjust to generate kat tables for particular languages.
        # print('{%d, []string{%s}},' % (complete_mmrs[i]-offset, ", ".join(peak_values)))


def print_katdb39_accumulators():
    katdb = KatDB()
    katdb.init_canonical39()
    print_39_accumulators(katdb)


def index_values_table(mmrsize=39):
    heights = []
    leafcounts = []
    for i in range(mmrsize):
        heights.append(index_height(i))
        leafcounts.append(leaf_count(i + 1))

    return [heights, leafcounts]


def print_index_height(mmrsize=39):
    table = index_values_table(mmrsize=mmrsize)

    heights = table[0]
    leafcounts = table[1]
    w = 5

    print("|" + "|".join([str(i).ljust(w, " ") for i in range(mmrsize)]) + "|")
    print("|" + "|".join([("-" * w) for i in range(mmrsize)]) + "|")
    print("|" + "|".join([str(h).ljust(w, " ") for h in heights]) + "|")
    print("|" + "|".join([str(n).ljust(w, " ") for n in leafcounts]) + "|")
    print(
        "|"
        + "|".join([bin(n)[2:].ljust(w, " ").ljust(w, " ") for n in leafcounts])
        + "|"
    )


def minmax_inclusion_path_table(mmrsize=39):

    rows = []
    max_accumulator = peaks(mmrsize)
    for i in range(mmrsize):
        s = complete_mmr_size(i)
        accumulator = [p-1 for p in peaks(s)]
        path = inclusion_proof_path(s, i)
        path_maxsz = inclusion_proof_path(mmrsize, i)

        rows.append([i, s, path, accumulator, path_maxsz, max_accumulator])

    return rows

def print_minmax_inclusion_paths(mmrsize=39):
    # note we produce inclusion paths for _all_ nodes

    table = minmax_inclusion_path_table(mmrsize=mmrsize)

    print(
        "|"
        + " i  "
        + "|"
        + " s  "
        + "|"
        + "min inclusion paths"
        + "|"
        + "min accumulator"
        + "|"
        + "MMR(39) inclusion paths"
        + "|"
        + "ACC MMR(39)"
        + "|"
    )
    print(
        "|:"
        + "-".ljust(3, "-")
        + "|"
        + "-".ljust(3, "-")
        + ":|"
        + "-".ljust(20, "-")
        + "|"
        + "-".ljust(20, "-")
        + "|"
    )

    for (i, s, path, accumulator, path_max, acc_max) in table:
        spath = "[" + ", ".join([str(p) for p in path]) + "]"
        spath_max = "[" + ", ".join([str(p) for p in path_max]) + "]"

        # it is very confusingif we list the accumulator as positions yet have the paths be indices. so lets not do that.
        saccumulator = "[" + ", ".join([str(p - 1) for p in accumulator]) + "]"
        smax_accumulator = "[" + ", ".join([str(p - 1) for p in acc_max]) + "]"

        print(
            "|"
            + "{:4}".format(i)
            + "|"
            + "MMR({})".format(s).ljust(7, " ")
            + "|"
            + spath.ljust(20, " ")
            + "|"
            + saccumulator.ljust(20, " ")
            + "|"
            + spath_max.ljust(20, " ")
            + "|"
            + smax_accumulator.ljust(20, " ")
            + "|"
        )


def inclusion_paths_table(mmrsize=39):

    rows = []
    for i in range(mmrsize):
        s = complete_mmr_size(i)
        while s < mmrsize:
            accumulator = [p-1 for p in peaks(s)]
            path = inclusion_proof_path(s, i)
            e = leaf_count(s)

            # for leaf nodes, the peak height is len(proof) - 1, for interiors, we need to take into account the height of the node.
            g = len(path) + index_height(i)

            ai = accumulator_index(e, g)

            rows.append([i, e, s, path, ai, accumulator])

            s = complete_mmr_size(s + 1)

    return rows


def print_inclusion_paths(mmrsize=39):
    # note we produce inclusion paths for _all_ nodes

    # so we can print the roots
    db = KatDB()
    db.init_canonical39()

    w1 = 4
    w2 = 20

    print(
        "|"
        + " i  "
        + "|"
        + " MMR  "
        + "|"
        + "inclusion path"
        + "|"
        + "accumulator"
        + "|"
        + "accumulator root index"
        + "|"
        + "root"
        + "|"
    )
    print(
        "|:"
        + "-".ljust(w1 - 1, "-")
        + "|"
        + "-".ljust(w1 - 1, "-")
        + ":|"
        + "-".ljust(w2, "-")
        + "|"
        + "-".ljust(w2, "-")
        + "|"
        + "-".ljust(w1, "-")
        + "|"
        + "-".ljust(w1, "-")
        + "|"
    )

    table = inclusion_paths_table(mmrsize=mmrsize)

    for (i, e, s, path, ai, accumulator) in table:

        spath = "[" + ", ".join([str(p) for p in path]) + "]"

        # it is very confusingif we list the accumulator as positions yet have the paths be indices. so lets not do that.
        saccumulator = "[" + ", ".join([str(p - 1) for p in accumulator]) + "]"

        sroot = db.get(accumulator[ai]).hex()

        print(
            "|"
            + "{:4}".format(i)
            + "|"
            + "MMR({})".format(s).ljust(7, " ")
            + "|"
            + spath.ljust(w2, " ")
            + "|"
            + saccumulator.ljust(w2, " ")
            + "|"
            + str(ai).ljust(w1, " ")
            + "|"
            + sroot
            + "|"
        )


def print_node_witness_longevity(mmrsize=39):
    # time in the mmr is measured in terms of discrete leaf additions.  this is
    # because, for each leaf addition, the number of additional interior nodes
    # required to form a complete mmr added is deterministic. In our specific
    # implementation, and indeed all we have studied, all interiors are added in
    # the same operation as the corresponding leaf.
    #
    # That said, we must be able to produce inclusion and consistency proofs for
    # *any* node.  This is because the accumulator, except in degenerate cases,
    # is populated by interior nodes, and, when showing consistency of an
    # outdated proof with a new mmr, we will typically be working with a node
    # which was once a peak and  has since been "burried", making it an
    # interiour.

    t_max = leaf_count(mmrsize)
    print("| ta  |{tw:s}".format(tw="|".join(["--" for i in range(t_max)])))
    print(
        "|tx:ix|{tw:s}".format(
            tw="|".join([str(i).rjust(2, " ") for i in range(t_max)])
        )
    )
    print("|-----|{tw:s}".format(tw="|".join(["--" for i in range(t_max)])))

    for ix in range(mmrsize):
        tx = leaf_count(ix)

        row0 = []
        row1 = []
        row2 = []
        wits = []

        for tw in range(tx, t_max):
            iw = mmr_index(tw)
            sw = complete_mmr_size(iw)
            # dsw = index_height(sw - 1)
            # depth of the proof for ix against the accumulator sw
            dsw = len(inclusion_proof_path(sw, ix))
            # row0.append(tx)
            row0.append(next_proof(ix, dsw))
            # additions until burried, and also until its witness next needs updating
            row1.append(dsw)

            w = inclusion_proof_path(sw, ix)
            if wits:
                assert len(w) >= len(wits[-1])
                for i in range(len(wits[-1])):
                    assert wits[-1][i] == w[i]

                # check that the previous witnes is updated by the inclusion proof for its previous accumulator root

                ioldroot_by_parent = len(wits[-1]) and parent(wits[-1][-1]) or ix
                ioldroot = accumulator_root(complete_mmr_size(mmr_index(tw - 1)), ix)
                assert (
                    ioldroot_by_parent == ioldroot
                ), f"{ioldroot_by_parent} != {ioldroot}"

                wupdated = wits[-1] + inclusion_proof_path(sw, ioldroot)
                for i in range(len(wupdated)):
                    assert wupdated[i] == w[i]

                # row2.append(len(w) - len(wits[-1]))
            # else:
            #     row2.append(0)

            # TODO: calculate the mmr index of the peak that contains ix for sw
            # .     then pick the correct child as the last proof path entry for ix in sw

            row2.append(wits and wits[-1] and wits[-1][-1] or ix)

            wits.append(w)

        if row0:
            srow0 = ["  " for i in range(t_max - len(row0))]
            srow0.extend([str(t).rjust(2, " ") for t in row0])
        if row1:
            srow1 = ["  " for i in range(t_max - len(row1))]
            srow1.extend([str(t).rjust(2, " ") for t in row1])
        if row2:
            srow2 = ["  " for i in range(t_max - len(row2))]
            srow2.extend([str(t).rjust(2, " ") for t in row2])

        if row0:
            print(
                "|{tx: >2d} {ix: >2d}|{row:s}".format(tx=tx, ix=ix, row="|".join(srow0))
            )
        if row1:
            print(
                "|{tx: >2d} {ix: >2d}|{row:s}".format(tx=tx, ix=ix, row="|".join(srow1))
            )
        if row2:
            print(
                "|{tx: >2d} {ix: >2d}|{row:s}".format(tx=tx, ix=ix, row="|".join(srow2))
            )


def xprint_leaf_witness_longevity(mmrsize=39):
    t_max = leaf_count(mmrsize)
    print("| ta|{tw:s}".format(tw="|".join(["--" for i in range(t_max)])))
    print(
        "|tx |{tw:s}".format(tw="|".join([str(i).rjust(2, " ") for i in range(t_max)]))
    )
    print("|---|{tw:s}".format(tw="|".join(["--" for i in range(t_max)])))

    for tx in range(t_max):
        ix = mmr_index(tx)
        sx = complete_mmr_size(ix)

        dsx = len(inclusion_proof_path(sx, ix))
        assert dsx == index_height(sx - 1)

        row0 = []
        row1 = []
        row2 = []
        wits = []

        for tw in range(tx, t_max):
            iw = mmr_index(tw)
            sw = complete_mmr_size(iw)
            dsw = index_height(sw - 1)
            # depth of the proof for ix against the accumulator sw
            w = inclusion_proof_path(sw, ix)
            if wits:
                assert len(w) == len(wits[-1]) + 0
                for i in range(len(wits[-1])):
                    assert wits[-1][i] == w[i]

            wits.append(w)

            dsw = len(inclusion_proof_path(sw, ix))
            # elementcount = peaks_bitmap(sw)
            # x = elementcount.bit_length() - most_sig_bit(elementcount)
            # assert dsw == x, f"{dsw} != {x}"

            # element count for a single binary tree is 1 << g
            # (it is necessary to sum them all to get the element count in the mmr, and that is just the peak bits)
            ec = 1 << dsw

            # leaf index local to its single binary tree
            te = tx % ec

            row0.append(next_leaf_proof(tx, sw, dsw))
            row1.append(next_proof(ix, dsw))
            # additions until burried, and also until its witness next needs updating
            # row2.append()

        if row0:
            srow0 = ["  " for i in range(t_max - len(row0))]
            srow0.extend([str(t).rjust(2, " ") for t in row0])
        if row1:
            srow1 = ["  " for i in range(t_max - len(row1))]
            srow1.extend([str(t).rjust(2, " ") for t in row1])
        if row2:
            srow2 = ["  " for i in range(t_max - len(row2))]
            srow2.extend([str(t).rjust(2, " ") for t in row2])

        if row0:
            print("| {tx: >2d}|{row:s}".format(tx=tx, row="|".join(srow0)))
        if row1:
            print("| {tx: >2d}|{row:s}".format(tx=tx, row="|".join(srow1)))
        if row2:
            print("| {tx: >2d}|{row:s}".format(tx=tx, row="|".join(srow2)))

    return

    for tx in range(t_max):
        if False:
            i = mmr_index(tx)
            s = complete_mmr_size(i)
            d = len(inclusion_proof_path(s, i))

            blen = tx.bit_length()
            bcnt = tx.bit_count()

            row = f"{tx: >2d} {i: >2d} {s: >2d} {d: >2d}"

            theight = (2 << tx.bit_length()) - 1
            dheight = (2 << d) - 1

            dnext = complete_mmr_size(s + dheight) - 1
            # uptimes = reyzin_uptimes(mmr_index(tx), mmr_index(t_max), d)
            uptimes = reyzin_uptimes(tx, t_max, d + 1)
            suptimes = ", ".join([str(t).rjust(2, " ") for t in uptimes])
            supindices = ", ".join([str(mmr_index(t)).rjust(2, " ") for t in uptimes])

            print(
                # f"{row: <9s}: ({blen:d}, {bcnt:d}), (2 << {blen:d}) - 1 = {theight: >2d}, (2 << ({d:d} + 1)) - 1 = {dheight: >2d}, {dnext: >2d}"
                f"{row: <9s}: {dnext: >2d}, [{suptimes:s}]"
            )
            continue

        lowd = []
        firstvalid = []
        validity = []
        expires = []
        dexpires = []
        lenproofs = []  # d list
        wbitlens = []  # d list

        for ta in range(tx, t_max):
            # lower bound d as log base 2 (tx - tw)
            if True or ta != tx:
                # lowd.append((ta - tx).bit_length() - 1)
                # d = (ta - tx + 1).bit_length() - 1
                # d = max(1, ta - tx)
                # d = d.bit_length() - 1
                d = (ta - tx + 1).bit_length() - 1
                lowd.append((1 << d) - 1)

            i = mmr_index(tx)
            s = mmr_index(ta) + 1
            d = len(inclusion_proof_path(s, i))

            mi = (2 << d) - 2

            # expires.append(mmr_index(tw + (1<<d)))
            # because the accumulator root for tw has h = tw.bit_length()
            expires.append((2 << ta.bit_length()) - 1)
            wbitlens.append(ta.bit_length() - 1)
            lenproofs.append(d)
            dexpires.append((2 << (d + 1)) - 1)
            # validity.append(dexpires[-1] - i + 1)
            validity.append(expires[-1] - s + 1)

            firstvalid.append((tx + ta) >> 1)

        slowd = ["  " for i in range(t_max - len(lowd))]
        slowd.extend([str(t).rjust(2, " ") for t in lowd])

        sfirst = ["  " for i in range(t_max - len(firstvalid))]
        sfirst.extend([str(t).rjust(2, " ") for t in firstvalid])

        sexpires = ["  " for i in range(t_max - len(expires))]
        sexpires.extend([str(n).rjust(2, " ") for n in expires])

        svalidity = ["  " for i in range(t_max - len(validity))]
        svalidity.extend([str(n).rjust(2, " ") for n in validity])

        sdexpires = ["  " for i in range(t_max - len(dexpires))]
        sdexpires.extend([str(n).rjust(2, " ") for n in dexpires])

        swbitlens = ["  " for i in range(t_max - len(wbitlens))]
        swbitlens.extend([str(d).rjust(2, " ") for d in wbitlens])

        slenproofs = ["  " for i in range(t_max - len(lenproofs))]
        slenproofs.extend([str(d).rjust(2, " ") for d in lenproofs])

        print("| {tx: >2d}|{lowd:s}".format(tx=tx, lowd="|".join(slowd)))

        continue
        print("| {tx: >2d}|{tfirst:s}".format(tx=tx, tfirst="|".join(sfirst)))

        print("| {tx: >2d}|{expires:s}".format(tx=tx, expires="|".join(sexpires)))
        print("| {tx: >2d}|{validity:s}".format(tx=tx, validity="|".join(sdexpires)))
        print("| {tx: >2d}|{validity:s}".format(tx=tx, validity="|".join(svalidity)))
        print("|d{tx: >2d}|{d:s}".format(tx=tx, d="|".join(swbitlens)))

        print("|d{tx: >2d}|{d:s}".format(tx=tx, d="|".join(slenproofs)))

    return
    for i in range(mmrsize):
        g = index_height(i)
        if g != 0:
            continue

        useleaves = True
        if useleaves:
            tx = leaf_count(i)
            validity = []
            for ta in range(tx, t_max):
                validity.append((2 * ta) - tx)
            dexpires = []
            dproof = []
            s = complete_mmr_size(i + 1)
            s = complete_mmr_size(i + 1)
            while s <= mmrsize:
                ta = leaf_count(s)
                d = len(inclusion_proof_path(s, i))
                dexpires.append(ta + (1 << d))
                dproof.append(d)
                s = complete_mmr_size(s + 1)

        sdproof = ["  " for i in range(t_max - len(dproof))]
        sdproof.extend([str(d).rjust(2, " ") for d in dproof])
        svalidity = ["  " for i in range(t_max - len(validity))]
        svalidity.extend([str(n).rjust(2, " ") for n in validity])

        sdexpires = ["  " for i in range(t_max - len(dexpires))]
        sdexpires.extend([str(n).rjust(2, " ") for n in dexpires])

        print("| {tx: >2d}|{validity:s}".format(tx=tx, validity="|".join(svalidity)))
        print("| {tx: >2d}|{validity:s}".format(tx=tx, validity="|".join(sdexpires)))
        print("|d{tx: >2d}|{d:s}".format(tx=tx, d="|".join(sdproof)))

        continue

        g = index_height(i)
        if g != 0:
            continue

        print(
            "i:{i:02d} z:{sz:02d} g:{log:d} x:{x:02d}".format(
                i=i,
                sz=complete_mmr_size(i),
                log=(i + 2).bit_length() - 1,
                x=(1 << ((i + 2).bit_length() - 0)) - 2,
            )
        )


def _print_mmr_indices(leaves: int):
    print("|".join([str(e).rjust(2, " ") for e in range(leaves)]))
    print("|".join([str(mmr_index(e)).rjust(2, " ") for e in range(leaves)]))


import sys

if __name__ == "__main__":
    if len(sys.argv) > 1:
        try:
            globals()["print_%s" % sys.argv[1]]()
        except KeyError:
            print("%s not found" % sys.argv[1])
            sys.exit(1)
        sys.exit(0)

    names = list(globals())
    for name in names:
        if not name.startswith("print_"):
            continue
        globals()[name]()