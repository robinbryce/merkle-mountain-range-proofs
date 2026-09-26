# Consistency proof shape does not bind the target tree size

Informative note, 2026-09-26. Companion to `consistent_roots_for_sizes` in
[algorithms.py](./algorithms.py) and to issues
[#40](https://github.com/robinbryce/draft-bryce-cose-receipts-mmr-profile/issues/40),
[#41](https://github.com/robinbryce/draft-bryce-cose-receipts-mmr-profile/issues/41) and
[#43](https://github.com/robinbryce/draft-bryce-cose-receipts-mmr-profile/issues/43)
on the COSE Receipts MMR profile. It records why `tree-size-2` must be signed
even after the proof shape is checked against the two sizes, and corrects an
earlier rationale that claimed path lengths bind the size whenever an origin
peak is carried into a new peak.

## What the shape checks fix

For a complete MMR the set bits of the leaf count are the peak heights, high to
low. A consistency proof from `sizefrom` to `sizeto` has, for each origin peak,
a path to its peak in the target. Let `split` be the highest bit on which the
two leaf counts differ.

- Origin peaks above `split` are peaks of the target: empty path.
- Origin peaks below `split` are all under the new peak of height `split`: path
  of length `split - h`, all proving the same node.
- Target peaks below `split` that no path reaches are supplied by the prover as
  right-peaks.

The path lengths therefore fix `split`, and with it every bit of the target
leaf count from the top down to and including `split`. The right-peak count
fixes how many bits are set below `split`. Nothing fixes *which* bits: a
right-peak is a node value, and a node value carries no height.

Every target whose leaf count shares the prefix through `split` and has the same
number of set bits below it accepts identical proof material. With `k`
right-peaks and `s = split` lower bit positions there are `C(s, k)` such
targets. The shape is unique only when `k = 0` or `k = s`.

## The empty-path case

Origin: 7 nodes, 4 leaves (`100`), one peak.

```
              6            leaves = 4 = 100b    accumulator [H6]
           /     \
          2       5
         / \     / \
        0   1   3   4
```

Appending fewer than 4 leaves carries nothing into peak 6. Its path is empty
and every new peak is a right-peak.

```
 size 8  (5 leaves, 101b)     size 10 (6 leaves, 110b)      size 11 (7 leaves, 111b)
        6                            6                             6
      /   \                        /   \                         /   \
     2     5    7                 2     5     9                 2     5     9
    / \   / \                    / \   / \   / \               / \   / \   / \
   0  1  3  4                   0  1  3  4  7  8              0  1  3  4  7  8  10
 paths [[]]  right [H7]        paths [[]]  right [H9]        paths [[]]  right [H9,H10]
```

7 -> 8 and 7 -> 10 have the same shape: one empty path, one right-peak. Take
the genuine 7 -> 8 receipt, whose signed accumulator is `[H6, H7]`, and
redeclare `tree-size-2` as 10. The fold accepts (empty path, one right-peak),
the accumulator is `[H6, H7]`, and the signature verifies because that is what
was signed. The verifier records size 10 with `[H6, H7]`; the ledger's
accumulator at 10 is `[H6, H9]`. H7 is a height 0 node read as the height 1
peak. The ledger's next honest receipt from 10 fails against the recorded
state, which reads as ledger misbehaviour.

Here even `split` is unbound, because no path exists to fix it. Let `t` be the
number of trailing zero bits of the origin leaf count, so the smallest origin
peak holds `2^t` leaves. Every target appending fewer than `2^t` leaves has
empty paths, so the window recurs at every multiple of 2 (one target), every
multiple of 4 (three), every multiple of 8 (seven), and at an exact power of two
it runs to just under double the size. Two targets are confusable only if they
add the same number of peaks, which needs `t >= 2`. From an empty tree the
window is unbounded: a first receipt for one leaf is accepted at any power of
two leaf count, up to `2^64 - 1` nodes.

## The carried case is not exempt

7 -> 16, 7 -> 18 and 7 -> 22 all carry peak 6 into the new height 3 peak with a
path of length 1, and each has one right-peak.

```
 size 16 (9 leaves, 1001b)               size 18 (10 leaves, 1010b)
                14                                     14
             /      \                               /      \
            6        13                            6        13
          /   \     /   \                        /   \     /   \
         2     5   9    12                      2     5   9    12       17
        / \   / \ / \   / \                    / \   / \ / \   / \     /  \
        0 1  3 4  7 8  10 11   15              0 1  3 4  7 8  10 11   15  16
 path from 6: [H13]  right [H15]          path from 6: [H13]  right [H17]
```

The path length pins `split = 3` and so the leaf count prefix `1...`; the count
pins one set bit among the three below. `1001`, `1010` and `1100` all qualify.
The signature over `[H14, H15]` for size 16 is accepted at size 18 with H15
read as the height 1 peak, and at size 22 with H15 read as the height 2 peak.

## Check against the reference

```python
import os, algorithms as alg
X, Y = os.urandom(32), os.urandom(32)
for to in (8, 10, 11):
    print(7, to, len(alg.consistent_roots_for_sizes(7, to, [X], [[]])[0]),
          alg.consistent_roots_for_sizes(7, to, [X], [[]])[1])
for to in (15, 16, 18, 22, 19):
    roots, nright = alg.consistent_roots_for_sizes(7, to, [X], [[Y]])
    print(7, to, len(roots), nright)
```

Output (roots, right-peaks required):

```
7 8   1 1
7 10  1 1
7 11  1 2
7 15  1 0
7 16  1 1
7 18  1 1
7 22  1 1
7 19  1 2
```

Identical inputs are accepted for 8 and 10, and for 16, 18 and 22. This is
correct behaviour for the fold: the fold's job is to reject material that does
not have the declared shape. Binding the declared size is the signature's job,
which is why the profile carries `tree-size-2` in the protected header and
requires the verifier to compare it with the last proof's `tree-size-2`.

## Consequences for the profile text

- The shape checks are still required. Without them an empty or short path
  returns the origin peak unchanged, so a receipt for one size verifies at any
  larger size with the same peak count, and the `2^63 - 1` freeze applies to
  initialised logs, not only empty ones.
- The rationale must not claim the shape checks bind the size in the carried
  case. The accurate statement is one sentence: a right-peak carries no height,
  so the same paths and right-peaks complete the accumulator of every tree size
  that adds the same number of new peaks.
- `tree-size-1` need not be signed. The verifier supplies it from trusted state,
  and every check above is a function of that state and the signed
  `tree-size-2`.
