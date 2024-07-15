"""
See the notational conventions in the accompanying draft text for definition of short hand variables.
"""
import unittest

from typing import List

from algorithms import consistency_proof
from algorithms import verify_consistency
from algorithms import inclusion_proof_path
from algorithms import verify_inclusion_path
from algorithms import mmr_index
from algorithms import index_height
from algorithms import accumulator_index
from algorithms import peaks
from algorithms import leaf_count
from algorithms import parent
from algorithms import accumulator_root
from algorithms import complete_mmr_size
from algorithms import next_proof
from algorithms import complete_mmr

from tableprint import complete_mmrs
from tableprint import peaks_table
from tableprint import index_values_table
from tableprint import inclusion_paths_table

from db import KatDB, FlatDB


class TestIndexOperations(unittest.TestCase):
    """
    Tests for the various algorithms that work on mmr indexes and leaf indexes,
    with out reference to a materialized tree.
    """

    def test_index_heights(self):
        """The heights calculated for each mmr index are correct"""

        expect = [
            0, 0, 1, 0, 0, 1, 2, 0, 0, 1, 0, 0, 1, 2, 3, 0, 0, 1, 0, 0,
            1, 2, 0, 0, 1, 0, 0, 1, 2, 3, 4, 0, 0, 1, 0, 0, 1, 2, 0 ]

        heights = index_values_table(mmrsize=39)[0]

        for i in range(39):
            self.assertEqual(heights[i], expect[i])

    def test_index_leaf_counts(self):
        """The leaf counts calculated for each mmr index are correct"""

        expect = [ 1, 1, 2, 3, 3, 3, 4, 5, 5, 6, 7, 7, 7, 7, 8, 9, 9, 10, 11,
                  11, 11, 12, 13, 13, 14, 15, 15, 15, 15, 15, 16, 17, 17, 18, 19, 19, 19, 20, 21 ]

        leaf_counts = index_values_table(mmrsize=39)[1]

        for i in range(39):
            self.assertEqual(leaf_counts[i], expect[i])


class TestAddLeafHash(unittest.TestCase):

    def test_add(self):
        """The dynamically created db matches the canonical known answer db"""
        db = FlatDB()
        db.init_canonical39()

        katdb = KatDB()
        katdb.init_canonical39()
        for i in range(len(db.store)):
            self.assertEqual(db.store[i], katdb.store[i])

    def test_addleafhash(self):
        """Adding the 21 canonical leaf values produces the canonical db"""
        katdb = KatDB()
        katdb.init_canonical39()
        db = FlatDB()
        db.init_size(39)

        for i in range(39):
            self.assertEqual(
                db.store[i],
                katdb.store[i],
                "node %d != %s (%s)" % (i, katdb.store[i], db.store[i]),
            )

    def test_addleafhash_accumulators(self):
        """Adding the 21 canonical leaf values produces the expected accumulators for each  mmr size"""

        expect = [
            [0, "af5570f5a1810b7af78caf4bc70a660f0df51e42baf91d4de5b2328de0e83dfc"],
            [2, "ad104051c516812ea5874ca3ff06d0258303623d04307c41ec80a7a18b332ef8"],
            [
                3,
                "ad104051c516812ea5874ca3ff06d0258303623d04307c41ec80a7a18b332ef8",
                "d5688a52d55a02ec4aea5ec1eadfffe1c9e0ee6a4ddbe2377f98326d42dfc975",
            ],
            [6, "827f3213c1de0d4c6277caccc1eeca325e45dfe2c65adce1943774218db61f88"],
            [
                7,
                "827f3213c1de0d4c6277caccc1eeca325e45dfe2c65adce1943774218db61f88",
                "a3eb8db89fc5123ccfd49585059f292bc40a1c0d550b860f24f84efb4760fbf2",
            ],
            [
                9,
                "827f3213c1de0d4c6277caccc1eeca325e45dfe2c65adce1943774218db61f88",
                "b8faf5f748f149b04018491a51334499fd8b6060c42a835f361fa9665562d12d",
            ],
            [
                10,
                "827f3213c1de0d4c6277caccc1eeca325e45dfe2c65adce1943774218db61f88",
                "b8faf5f748f149b04018491a51334499fd8b6060c42a835f361fa9665562d12d",
                "8d85f8467240628a94819b26bee26e3a9b2804334c63482deacec8d64ab4e1e7",
            ],
            [14, "78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112"],
            [
                15,
                "78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112",
                "e66c57014a6156061ae669809ec5d735e484e8fcfd540e110c9b04f84c0b4504",
            ],
            [
                17,
                "78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112",
                "f4a0db79de0fee128fbe95ecf3509646203909dc447ae911aa29416bf6fcba21",
            ],
            [
                18,
                "78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112",
                "f4a0db79de0fee128fbe95ecf3509646203909dc447ae911aa29416bf6fcba21",
                "5bc67471c189d78c76461dcab6141a733bdab3799d1d69e0c419119c92e82b3d",
            ],
            [
                21,
                "78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112",
                "61b3ff808934301578c9ed7402e3dd7dfe98b630acdf26d1fd2698a3c4a22710",
            ],
            [
                22,
                "78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112",
                "61b3ff808934301578c9ed7402e3dd7dfe98b630acdf26d1fd2698a3c4a22710",
                "7a42e3892368f826928202014a6ca95a3d8d846df25088da80018663edf96b1c",
            ],
            [
                24,
                "78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112",
                "61b3ff808934301578c9ed7402e3dd7dfe98b630acdf26d1fd2698a3c4a22710",
                "dd7efba5f1824103f1fa820a5c9e6cd90a82cf123d88bd035c7e5da0aba8a9ae",
            ],
            [
                25,
                "78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112",
                "61b3ff808934301578c9ed7402e3dd7dfe98b630acdf26d1fd2698a3c4a22710",
                "dd7efba5f1824103f1fa820a5c9e6cd90a82cf123d88bd035c7e5da0aba8a9ae",
                "561f627b4213258dc8863498bb9b07c904c3c65a78c1a36bca329154d1ded213",
            ],
            [30, "d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7"],
            [
                31,
                "d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7",
                "1664a6e0ea12d234b4911d011800bb0f8c1101a0f9a49a91ee6e2493e34d8e7b",
            ],
            [
                33,
                "d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7",
                "0c9f36783b5929d43c97fe4b170d12137e6950ef1b3a8bd254b15bbacbfdee7f",
            ],
            [
                34,
                "d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7",
                "0c9f36783b5929d43c97fe4b170d12137e6950ef1b3a8bd254b15bbacbfdee7f",
                "4d75f61869104baa4ccff5be73311be9bdd6cc31779301dfc699479403c8a786",
            ],
            [
                37,
                "d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7",
                "6a169105dcc487dbbae5747a0fd9b1d33a40320cf91cf9a323579139e7ff72aa",
            ],
            [
                38,
                "d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7",
                "6a169105dcc487dbbae5747a0fd9b1d33a40320cf91cf9a323579139e7ff72aa",
                "e9a5f5201eb3c3c856e0a224527af5ac7eb1767fb1aff9bd53ba41a60cde9785",
            ],
        ]
        db = FlatDB()
        db.init_size(39)

        peak_positions_table = peaks_table()
        peak_values_table = peaks_table(db)

        for i in range(len(complete_mmrs)):
            peak_positions = peak_positions_table[i]
            peak_values = peak_values_table[i]
            expect_mmrsize, expect_values = (expect[i][0] + 1, expect[i][1:])
            for j, p in enumerate(peak_positions):
                self.assertEqual(complete_mmrs[i], expect_mmrsize)
                self.assertEqual(db.store[p - 1].hex(), peak_values[j])
                self.assertEqual(db.store[p - 1].hex(), expect_values[j])


class TestVerifyInclusion(unittest.TestCase):

    def test_verify_inclusion(self):
        """Every node can be verified against an accumulator peak for every subsequent complete MMR size"""
        # Hand populate the db
        db = KatDB()
        db.init_canonical39()

        # Show that inclusion_proof_path verifies for all complete mmr's which include i
        for i in range(39):
            s = complete_mmr_size(i)
            while s < 39:
                # typically, the size, accumulator and paths will be givens.
                accumulator = [db.get(p - 1) for p in peaks(s)]
                path = [db.get(isibling) for isibling in inclusion_proof_path(i, s-1)]

                e = leaf_count(s)

                # for leaf nodes, the peak height is len(proof) - 1,
                # for interiors, we need to take into account the height of the node.
                g = len(path) + index_height(i)

                iacc = accumulator_index(e, g)

                ok, pathconsumed = False, 0

                (ok, pathconsumed) = verify_inclusion_path(
                    i, db.get(i), path, accumulator[iacc]
                )
                self.assertTrue(ok)
                self.assertEqual(pathconsumed, len(path))

                s = complete_mmr_size(s + 1)


    def test_verify_inclusion_all_mmrs(self):
        """Every inclusion proof for every node proves the expected peak root"""
        db = KatDB()
        db.init_canonical39()

        table = inclusion_paths_table(39)
        for (i, e, s, pathindices, ai, accumulator) in table:
            root = db.get(accumulator[ai])
            node = db.get(i)
            path = [db.get(ip) for ip in pathindices]
            (ok, pathlen) = verify_inclusion_path(i, node, path, root)
            self.assertTrue(ok)
            self.assertEqual(pathlen, len(path))


class TestVerifyConsistency(unittest.TestCase):
    def test_verify_consistency(self):
        """Consistency proofs of arbitrary MMR ranges verify"""
        # Hand populate the db
        db = KatDB()
        db.init_canonical39()

        for stride in range(int(39 / 2)):
            stride = stride + 1
            ia = 0
            ib = complete_mmr(min(ia + stride, 38))

            while ib <= 39 and (ib - ia > 0):
                iproof = consistency_proof(ia, ib)
                proof = [db.get(i) for i in iproof]
                iaacc = [p - 1 for p in peaks(ia+1)]
                aacc = [db.get(i) for i in iaacc]
                ibacc = [p - 1 for p in peaks(ib+1)]
                bacc = [db.get(i) for i in ibacc]

                ok = verify_consistency(ia, ib, aacc, bacc, proof)
                self.assertTrue(ok)
                ia = complete_mmr(ia + stride)
                ib = complete_mmr(ia + 2 * stride)


class TestWitnessUpdate(unittest.TestCase):

    def test_witness_update(self):
        """Each witness is a prefix of all future witnesses for the same entry"""

        mmrsize = 39

        t_max = leaf_count(mmrsize)

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
                dsw = len(inclusion_proof_path(ix, sw-1))
                # row0.append(tx)
                row0.append(next_proof(ix, dsw))
                # additions until burried, and also until its witness next needs updating
                row1.append(dsw)

                w = inclusion_proof_path(ix, sw-1)
                if wits:
                    self.assertGreaterEqual(len(w), len(wits[-1]))
                    # The old witness is a strict subset of the new witness
                    self.assertEqual(wits[-1], w[: len(wits[-1])])

                    # check that the previous witness is updated by the inclusion proof for its previous accumulator root

                    ioldroot_by_parent = len(wits[-1]) and parent(wits[-1][-1]) or ix
                    ioldroot = accumulator_root(
                        complete_mmr_size(mmr_index(tw - 1)), ix
                    )

                    self.assertEqual(ioldroot_by_parent, ioldroot)

                    wupdated = wits[-1] + inclusion_proof_path(ioldroot, sw-1)

                    self.assertEqual(wupdated, w)

                row2.append(wits and wits[-1] and wits[-1][-1] or ix)

                wits.append(w)


if __name__ == "__main__":
    unittest.main()
