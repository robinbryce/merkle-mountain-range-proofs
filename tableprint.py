from algorithms import inclusion_proof_path
from algorithms import index_height
from algorithms import peaks
from algorithms import peak_depths
from algorithms import leaf_count
from algorithms import complete_mmr
from algorithms import mmr_index
from algorithms import parent
from algorithms import roots
from algorithms import leaf_witness_update_due
from algorithms import accumulator_root
from algorithms import accumulator_index


from db import KatDB, FlatDB

complete_mmr_sizes =   [ 1, 3, 4, 7, 8, 10, 11, 15, 16, 18, 19, 22, 23, 25, 26, 31, 32, 34, 35, 38, 39 ]
complete_mmr_indices = [ 0, 2, 3, 6, 7,  9, 10, 14, 15, 17, 18, 21, 22, 24, 25, 30, 31, 33, 34, 37, 38 ]

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
    for i in range(len(complete_mmr_sizes)):
        s = complete_mmr_sizes[i]
        peak_values = [i for i in peaks(s-1)]  # returns a list of positions, not indices
        if db:
            rows.append([db.get(p).hex() for p in peak_values])
            continue
        rows.append(peak_values)

    return rows


def print_39_accumulators(db=None):
    rows = peaks_table(db)

    id_head = " i"
    print("|" + id_head + "|" + " " * 8 + "accumulator peaks" + " " + "|")
    print("|" + "-" * 2 + "|" + "-" * 26 + "|")

    for i, peak_values in enumerate(rows):
        print(
            "|"
            + "{:2}".format(complete_mmr_sizes[i] - 1)
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
        leafcounts.append(leaf_count(i))

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
    max_accumulator = [ip+1 for ip in peaks(mmrsize-1)]
    for i in range(mmrsize):
        ix = complete_mmr(i)
        accumulator = [ip for ip in peaks(ix)]
        path = inclusion_proof_path(i, ix)
        path_maxsz = inclusion_proof_path(i, mmrsize-1)

        rows.append([i, ix, path, accumulator, path_maxsz, max_accumulator])

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
        saccumulator = "[" + ", ".join([str(p) for p in accumulator]) + "]"
        smax_accumulator = "[" + ", ".join([str(p) for p in acc_max]) + "]"

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
        ix = complete_mmr(i)
        while ix < mmrsize:
            accumulator = [ip for ip in peaks(ix)]
            path = inclusion_proof_path(i, ix)
            e = leaf_count(ix)

            # for leaf nodes, the peak height is len(proof) - 1, for interiors, we need to take into account the height of the node.
            g = len(path) + index_height(i)

            ai = accumulator_index(e, g)

            rows.append([i, e, ix, path, ai, accumulator])

            ix = complete_mmr(ix + 1)

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
        saccumulator = "[" + ", ".join([str(p) for p in accumulator]) + "]"

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

def getreleventindices(lastupdateidx, previdx, d):
    """
    Returns a list of indices of relevent updates, given:
        lastupdateidx: the index at which the last witness update occurred
        previdx: the index at which the last accumulator update occurred
        d: the depth of the current witness


    NOTICE:

    This is the python implemementation of "GetUpdateTimeSteps" from
    "Efficient Asynchronous Accumulators for Distributed PKI"
    -  https://eprint.iacr.org/2015/718.pdf


    This python code was provided by Sophia Yakoubov (an author on that paper)
    """
    releventindices = []
    power = 2 ** d
    releventindex = lastupdateidx + power
    while releventindex <= previdx:
        releventindices.append(releventindex)
        while releventindex % (power * 2) == 0:
            power = power * 2
        releventindex += power
    return releventindices


def node_witness_update_tables(mmrsize=39):

    rows = []
    tmax = leaf_count(mmrsize-1)

    for tw in range(tmax):
        iw = mmr_index(tw)
        mmrw = complete_mmr(iw)
        dw = len(inclusion_proof_path(iw, mmrw))
        for tx in range(tw+1, tmax):
            leaf_indices = getreleventindices(tw, tx, dw)
            rows.append([iw, tw, tx, "reysop", leaf_indices])
            ix = mmr_index(tx)
            leaf_indices_mmriver = leaf_index_updates(tw, tx, dw)
            rows.append([iw, tw, tx, "mmrive", leaf_indices_mmriver])

    return rows

def vgetreleventindices(lastupdateidx, previdx, d):
    """
    Returns a list of indices of relevent updates, given:
        lastupdateidx: the index at which the last witness update occurred
        previdx: the index at which the last accumulator update occurred
        d: the depth of the current witness


    NOTICE:

    This is the python implemementation of "GetUpdateTimeSteps" from
    "Efficient Asynchronous Accumulators for Distributed PKI"
    -  https://eprint.iacr.org/2015/718.pdf


    This python code was provided by Sophia Yakoubov (an author on that paper)
    """
    releventindices = []
    power = 2 ** d
    releventindex = lastupdateidx + power

    print(f":d={d} lupi={lastupdateidx} pow={power} ri={releventindex}")
    while releventindex <= previdx:
        releventindices.append(releventindex)
        print(f"  releventindices: {releventindices} <- {releventindex}")
        while releventindex % (power * 2) == 0:
            print(f"    ri={releventindex} pow: {power}->{power *2}")
            power = power * 2
        releventindex += power
    print(f":{releventindices}")
    print(f":{[mmr_index(i) for i in releventindices]}")

    return releventindices

def print_reysop():
    ri_reysop = vgetreleventindices(0, 8, 0)
    print("--")
    ri_mmriver = leaf_index_updates(0, 8, 0)
    print(ri_reysop)
    print(ri_mmriver)


def print_witness_updates(mmrsize=39):

    rows = node_witness_update_tables(mmrsize=mmrsize)
    for row in rows:
        print(row)


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

    t_max = leaf_count(mmrsize-1)
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
            mmrw = complete_mmr(iw)
            # dsw = index_height(sw - 1)
            # depth of the proof for ix against the accumulator sw
            dsw = len(inclusion_proof_path(ix, mmrw))
            # row0.append(tx)
            row0.append(index_witness_update_due(ix, dsw))
            # additions until burried, and also until its witness next needs updating
            row1.append(dsw)

            w = inclusion_proof_path(ix, mmrw)
            if wits:
                assert len(w) >= len(wits[-1])
                for i in range(len(wits[-1])):
                    assert wits[-1][i] == w[i]

                # check that the previous witnes is updated by the inclusion proof for its previous accumulator root

                ioldroot_by_parent = len(wits[-1]) and parent(wits[-1][-1]) or ix
                ioldroot = accumulator_root(ix, complete_mmr(mmr_index(tw - 1)))
                assert (
                    ioldroot_by_parent == ioldroot
                ), f"{ioldroot_by_parent} != {ioldroot}"

                wupdated = wits[-1] + inclusion_proof_path(ioldroot, mmrw)
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

def basesz(sz):
    # math.floor(math.log2(sz))
    return sz.bit_length() - 1

import sys

if __name__ == "__main__":

    if False:
        def s(i): return str(i).rjust(2, " ")
        def j(l): return ", ".join(l)

        leaf_mmrindices = [0,   1, 3,   4,  7,   8, 10,  11, 15,  16, 18,  19, 22,  23,   25,   26,  31,  32,   34,  35,   38]
        leaf_positions = [i+1 for i in leaf_mmrindices]

        rows = []

        def s(v): return str(v).rjust(2, " ")
        def seqs(seq): return "[" + ", ".join([str(e).rjust(2, " ") for e in seq]) + "]"

        ito = complete_mmr(0)
        while ito <= 38:

            print(seqs(peaks(ito)))
            print(seqs(peak_depths(ito)))
            print(seqs(list(reversed(sorted(list(set([len(inclusion_proof_path(ifrom, ito))+index_height(ifrom) for ifrom in range(ito)])))))))

            print("{s}".format(s=bin(leaf_count(ito))))
            print()
            ito = complete_mmr(ito + 1)

        sys.exit(0)

    # print("\n".join(rows))

    if False:
        print(j([s(sz-1) for sz in complete_mmr_sizes]))
        print(j([s(basesz(sz)) for sz in complete_mmr_sizes]))
        print(j([s(sz - basesz(sz)) for sz in complete_mmr_sizes]))
        print(j([s(p-((1<<basesz(p))-1)) for p in  complete_mmr_sizes]))
        print(j(["  "] + [s(complete_mmr_sizes[i]+d) for (i, d) in enumerate([p-((1<<basesz(p))-1) for p in  complete_mmr_sizes][1:])]))
        print(j([s(p-1) for p in leaf_positions]))
        print(j([s(depth_inext(p)) for p in leaf_positions]))


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