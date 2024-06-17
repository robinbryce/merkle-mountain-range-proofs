# Merkle Mountain Range for verifiable, write once, data commitments

## Introduction

The affordances of a post-order binary tree serialization, first noted in [CrosbySecondaryStorage],
enable distinct advantages for maintaining verifiable data and for parties relying on the verifiability of that data.

The term "Merkle Mountain Range" is due to [PeterTodd] and has wide acceptance as the identifier for this approach to managing Merkle trees in this way. This is typically abbreviated as MMR.

This experimental draft defines algorithms for leaf addition, proofs of inclusion and consistency, and the related necessary primitives in order to make the advantages of this approach to Merkle trees available in an interoperable manner.

Editors note: This definition is currently constrained to require the SHA3/256. It may make sense to make the specific hash an implementation choice, and instead define the required properties.

The following advantages are realized when using this merkle tree construction

- Updates to the persistent tree data are co-ordination free. Competing writers
  can safely use [Optimistic Concurency Control](https://en.wikipedia.org/wiki/Optimistic_concurrency_control)
- Tree data does not change once written.
  This makes additions immediately available for replication and caching with mechanisms such as [HTTP_ETag](https://en.wikipedia.org/wiki/HTTP_ETag)
- Proofs of inclusion for a specific element are permanently consistent with all future states of the tree.
  And, a tree state which fails this property is provably inconsistent.
- A proof of consistency from any single point in the tree is permanently
  consistent with all future tree states.
- Trees can be pruned without breaking these properties of inclusion and consistency.
  For a previously saved inclusion proof,
  there are at most log 2 (n) future checkpoints required to show its validity against any future tree.
  Where n is the count of additions made after the entry was added.
- The checkpoints themselves naturally emerge from the tree and are also permanently consistent with future states of the tree.
- Any tree state which fails to satisfy these stated properties is provably inconsistent.
  For both proofs of inclusion and proofs of consistency,
  the authentication paths for each tree state are strict sub paths of those in any future state.

The "write once" property is particularly amenable to use with storage approaches such as Microsoft [ProjectSilica],
which stores data on glass, with an infinite lifespan with no degradation and no costs for cold storage.

These properties mostly follow from:

- A post order traversal of a binary tree results in a naturally linear storage organization. As observed  in [CrosbySecondaryStorage].
- An asynchronous cryptographic accumulator naturally emerges when maintaining a tree in this way.
  [ReyzinYakoubov] defines the properties of these, which are particularly relevant here, as "Low update frequency" and "Old-Accumulator Compatibility".
  The checkpoint mentioned above is exactly the accumulator state for any valid tree size.
- As the post order traversal index is permanently identifying for any elements siblings and parents,
  the authentication path element indices is known and permanent.
  It can be easily computed without needing to materialize the tree in whole or in part.

Further work in [BNT] defines additional advantages for contexts in which "stream" processing of verifiable data is desirable. Post-order, Pre-order and in-order tree traversal are defined by [KnuthTBT]

## Accumulator and Structure

To maximise the benefits of using an MMR, inclusion and consistency proofs are defined against the accumulator cited above,
rather than a single tree root. In this section we describe and define the accumulator in the context of an MMR.

An MMR is a flat base binary tree, where incomplete sub-trees are maintained in series.
The roots of each sub-tree are described as peaks.
The set of peaks for an MMR of any size is its accumulator. And this uniquely and succinctly commits the content of the MMR.
As the tree grows, elements in the accumulator change with low frequency. This frequency is defined as $$\log_2(n)$$ in the number of subsequent tree additions.
It is important to note that while the accumulator state evolves, all nodes in the tree are write once.
The accumulator simply comprises the nodes at the "peaks" for the current MMR state.
All paths for proofs of inclusion lead to an accumulator peak, rather than a single "mono" root.
Because of this, the inclusion path for any element is strictly append only.
Consistency proofs *are* the inclusion proofs for the old-accumulator peaks against the accumulator for the future tree state consistency is being shown for.
An accumulator is at most tree height long, which is also the maximum length of any single proof of inclusion + 1.

For illustration, consider `MMR(8)` which is a complete MMR with two peaks at node indices 6 and 7.

```
   6
 2   5
0 1 3 4 7
```

The node indices match their location in storage.
When constructing the tree, addition of nodes is strictly append only.

MMR's are identified uniquely by their size. Above we have `MMR(8)`, because there are 8 nodes.

An incomplete MMR may still be identified. Here we have `MMR(9)`.

```
   6
 2   5
0 1 3 4 7 8
```

An MMR is said to be "complete" when all possible ancestors have been "filled in".
The value for node 9 is `H(7 || 8)`, and adding that node completes the previous MMR.

```
   6
 2   5   9
0 1 3 4 7 8
```

The accumulator, described by [ReyzinYakoubov] is the set of peaks, with "gaps" reserved for the missing peaks.
MMR(8), where a gap is indicated by _ would be:

    [6, _, 7]

The packed form would be:

    [6, 7]

The accumulator, packed or padded, lists the peaks strictly descending order of height.
Given this fact, straight forward primitives for selecting the desired peak can be derived from both packed and un-packed form.
The algorithms in this document work with the packed form exclusively.

Given any index `i` in the tree, the accumulator for the previous `D[0:i)` nodes
satisfies the sibling dependencies of the inclusion paths of all subsequent `D[i:n]` nodes.

And the accumulator is itself, only dependent, for proof of inclusion or consistency, on nodes in `D[i:n]`

The progression of the packed accumulator for MMR sizes 1, 3, 4, 7, 8 is then:

`MMR(1): [0]`

`MMR(3): [2]`

`MMR(4): [2, 3]`

`MMR(7): [6]`

`MMR(8): [6, 7]`

`MMR(10): [6, 9]`

The verification path for node `1` in `MMR(3)` is `[0]`, because `H(0, 1)` is the value at `2`.

The path for node `1` in `MMR(4)` remains un changed.

The path for node `1` in `MMR(7)` becomes `[0, 5]`, because `H(0, 1)` is the value at `2`, and `H(H(0, 1), 5)` is the value at `6`.

The path for node `1` in `MMR(8)` and `MMR(10)` remains unchanged.

It can be seen that the older the tree item is,
the less frequently its verification path will be extended to reach a new accumulator entry.

An algorithm to add a single leaf to an MMR is given in [AddLeafHash]()

An algorithm to produce the verifying path for any node `i` is given in [IndexProofPaths](#indexproofpaths-i)

In general, given the height `g` of the accumulator peak currently authenticating a node `i`,
the verification path for `i` will not change until the count of tree leaves reaches $$2^{g+1}$$.

An algorithm defining the packed accumulator for any MMR size `S` is given by [Peaks](#peakss)

An algorithm which sets a bit for each present accumulator peaks in an MMR of size `S` is given by [PeaksBitmap](#peaksbitmap),
the produced value is also the count of leaves present in that MMR. This algorithm is independent of whether the accumulator is maintained in packed or padded form.

Lastly, many primitives for working with MMR's rely on a property of the *position* tree form of an MMR.

The position tree for the complete MMR with size 8 MMR(8) is

```
   7
 3   6
1 2 4 5 8
```

Expressing this in binary notation reveals the property that MMR's make extensive use of:

```
    111
 11     110
1 10 100  101 1000
```

The left most node at any height is always "all ones".

## Notational Conventions

- `i` shall be the index of a node in the MMR
- `pos` shall be `i+1`
- `e` shall be the zero based index of leaf entry in the MMR
- `f` shall be a leaf value, which is `H(x)`
- `h` shall be the 1 based tree height
- `g` shall be the 0 based height, `h-1`
- `v` shall be any node, including a leaf node value, which will be the result of `H(x)`.
- `S` shall be any valid MMR size, and is uniquely identifying for an MMR state
- `A` shall be the the accumulator for any valid MMR size `S`
- `R` shall be the the sparse accumulator, of [ReyzinYakoubov], for any valid MMR size `S`
- `H(x)` shall be the SHA3/256 digest of any value x
- `||` shall mean concatenation of raw byte representations of the referenced values.


## Implementation defined methods

The following methods are assumed to be available to the implementation. Very minimal requirements are specified.

### Get

Reads the value from the MMR at the supplied position.

Used by any algorithm which may need access to node values.

The read MUST be consistent with any other calls to Append or Get within the *same* algorithm invocation.

When adding leaves and obtaining values for proofs, the nodes referenced are highly deterministic.
It is reasonable to expect the caller to have ensured their availability.

Get MAY fail for transient reasons.

### Append

Adds a new element to the append only, write-once data.

The implementation MUST guarantee that the results of Append are immediately available to Get calls in the same invocation of the algorithm OR fail.

Append MUST return the node `i` identifying the node just appended.

Implementations MAY rely on the verifiable properties of the tree,
or optimistic concurrency control, to afford detection of accidental or competing overwrites.

Used only by [AddLeafHash](#addleafhashe)

The implementation MAY defer commitment to underlying storage.

Append MAY fail for transient reasons.

## Node values

Interior nodes in the tree SHALL prefix the value provided to `H(x)` with `pos`.

The value `v` for any interior node MUST be `H(pos || Get(LEFT_CHILD) || Get(RIGHT_CHILD))`

This naturally affords the pre-image resistance typically obtained with specific leaf/interior node prefixes.
Nonce schemes to account for duplicate leaves are also un-necessary as a result,
but MAY be included by the application for other reasons.


The algorithm for leaf addition is provided the result of `H(x)` directly.
The application MUST define how it produces `x` such that parties reliant on the system for verification can recreate `H(x)`.


## Addition, Inclusion and Consistency Proof Algorithms

All numbers are unsigned 64 bit integers. The maximum height of a single tree is 64.

Were a tree to accept a new addition once every 10 milliseconds, it would take roughly 4.6 million milenia to over flow.

Should a system exist that can extend a tree fast enough for this to be a limitation,
the same advantages that make MMR's convenient to work with also accrue to combinations of trees.

The algorithms are offered in both a python like informal pseudo code, and structured english.

### AddLeafHash(f)

Note: it is assumed that the algorithm terminates and returns on any transient error.

Given,

`f` the leaf value resulting from `H(x)` for the caller defined leaf value `x`

1. Set `i` to the result of invoking `Append(f)`
1. Set `g` to 0, the height of the leaf item f
1. If `IndexHeight(i)` is greater than `g` (#looptarget)
    1. Set `iLeft` to `i - (2 << g)`
    1. Set `iRight` to `i - 1`
    1. Set `v` to `H(i + 1 || Get(iLeft) || Get(iRight))`
    1. Set `i` to the result of invoking `Append(v)`
    1. Set `g` to `g + 1`
    1. Goto #looptarget
1. Return `i` to the caller


Editors node: TODO check this algebra is sound
```
    iRight := iLeft + SiblingOffset(height) == i - 1
    because i - (2 << height ) + SiblingOffset(height)
            => i - (2 << height ) + (2 << height) - 1
            => i - 1
    And, intuitively, the 'next' i is always last i + 1, and that is
    always going to be RHS when we are adding
    iRight := iLeft + SiblingOffset(height)

```
### IndexProofPath(S, i)

IndexProofPath is used to produce the verification paths for inclusion proofs and consistency proofs.

When a path is produced for the purposes of verification, the path elements MUST be resolved to the referenced node values.
Whether this is accomplished in-line, as the algorithm proceeds, or later as a second pass, is an implementation choice.

For a pruned tree, the post order index of the element is either present directly or is present in the accumulator.
Managing the availability of the accumulator is the callers responsibility.

Given

- `S` identifies the MMR state.
- `i` is the index the `nodeHash` is to be shown at

In the described algorithm,
pathElement is either the the post-order index `i` for the node or the value obtained from storage for that index.

1. Set the path to the empty list
1. Set `g` to `IndexHeight(i)`
1. Repeat until #termination_condition evaluates true
    1. Set iLocalPeak to `i`
    1. if `IndexHeight(i+1)` is greater than `g`
        1. Set `iSibling` to `iLocalPeak - SiblingOffset(g)`
        1. Set `i` to `i+1`
    1. Otherwise,
        1. Set `iSibling` to `iLocalPeak + SiblingOffset(g)` 
        1. Set `i` to `i` + `2 << g`
    1. If `iSibling` is greater or equal to `S` (#termination_condition)
       Return the current path to the caller, terminating the algorithm.
    1. Append the current pathElement to the proof.
    1. Increment the index height `g`

* `SiblingOffset` is defined as `(2 << g) - 1`
* `IndexHeight` is defined in [IndexHeight(i)](#indexheighti)

Note that at the #termination_condition it MAY be convenient for implementations to return the index of the local peak `iLocalPeak` and its height `g` to the caller.

For reference in the supplementary worked examples, the decision points are annotated (1), (2)

```python

  proof = []
  g = IndexHeight(i)

  while True:

    iLocalPeak = i
 
    if IndexHeight(i+1) > g: # (1)
        iSibling = iLocalPeak - SiblingOffset(g)
        i += 1
    else:
        iSibling = iLocalPeak + SiblingOffset(g)
        i += 2 << g
  
    if iSibling >= mmrSize: # (2)
        return proof, iLocalPeak, g

    proof = append(proof, iSibling)
  
    g += 1
```

## Inclusion and Consistency Verification Algorithms

### VerifyInclusionPath

Verifies an accumulator peak root can be reached from the leaf using the path

Given

- `S` identifies the MMR state.
- `nodeHash` the value whose inclusion is to be shown
- `i` is the index the `nodeHash` is to be shown at
- `proof` is the inclusion path node values, verifying inclusion of `nodeHash` at `i` in the `MMR(S)`
- `root` is the root of the sub tree occupied by `i`, and is a member of the accumulator for `MMR(S)`

Note: `PosHeight` is defined as `IndexHeight(pos - 1)`. For this algorithm it is most convenient to works with the position tree.

`VerifyInclusionPath` is defined as

1. If the proof length is zero and the leaf is equal the root, succeed
1. Set `g` to `PosHeight(pos)`
1. Set elementHash to the value whose inclusion is to be proven
1. For each pathItem with index iProof in proof
    1. if `PosHeight(pos+1)` is greater than `g`
        1. Set `pos` to `pos + 1`
        1. Set `elementHash` = `H(pos || pathItem || elementHash)`
    1. Otherwise:
        1. Set `pos` to `pos + 2 << g`
        1. Set `elementHash` to `H(pos || elementHash || pathItem)`
    1. Compare root to `elementHash`.
       If root is equal,
       we have shown that index items from proof have proven inclusion
       of the value at the initial value for `pos`.
       Return index to the caller and indicate success.
    1. Increment `g`
1. We have consumed the proof without producing the root, fail the verification.

Verification MUST require that the path is fully consumed during verification.
The algorithm above defers that final requirement to the caller.
Where the caller is verifying a single proof of inclusion, they MUST check the returned consumed length equals the length of the poof provided.
Where the caller is verifying a series of concatenated proofs of inclusion, such as for consistency proofs,
the caller MUST ensure the entire concatenated series of proofs is fully consumed.
In the case of concatenated inclusion proof verification,
the sub range of the aggregate proof must be advanced by the returned consumed length on each call.

Consistency proofs concatenate inclusion proofs for each accumulator peak in the origin mmr state.

!!!Note Identifying local peak for accumulator node proof. Its the smallest peak in the new accumulator that is larger than the historic peak ...

```python
# If the proof length is zero and the leaf is equal the root, succeed

pos =  i + 1
heightIndex = PosHeight(pos)
elementHash = leafHash
proofConsumed = 0

for each pathItem in proof:

    if PosHeight(pos+1) > heightIndex: # (1)
        pos += 1
        elementHash = H(pos || pathItem || elementHash)
    else:
        pos += 2 << heightIndex
        elementHash = H(pos || elementHash || pathItem)

    if elementHash == root: # (2)
        return true, proofConsumed

    heightIndex += 1
    proofConsumed += 1
```

## Algorithms for working with the accumulator

### IndexHeight(i)

Index height returns the zero based height `g` of the node index `i`

```
  pos = i + 1
  while !AllOnes(pos):
    pos = pos - MostSigBit(pos) + 1

  return BitLength(pos) - 1
```


### Peaks(S)

### SparsePeakIndex(R, g)

When working with a sparse accumulator, and the height of the desired peak is known,
the accumulator index is given by `length(R) - g - 1`

### PeakIndex(e, g)

### PeaksBitmap

The leaf count is often available, in which case its binary form is exactly the result of this transformation on MMR size `S`.
Otherwise, to obtain either the bitmap of the peaks, or the count of the leaves contained in the size `S`,
this algorithm can be used.

```
    if mmrSize == 0:
        return 0
    pos = mmrSize
    peakSize = (1 << BitLength(mmrSize)) - 1
    peakMap = 0
    while peakSize > 0: (1)
        peakMap <<= 1
        if pos >= peakSize: (2)
            pos -= peakSize
            peakMap |= 1
        peakSize >>= 1
    return peakMap
```


## General Algorithms & Primitives

### A Note On Hardware Sympathy

For flat base trees, many operations are formally $$\log_2(n)$$

However, precisely because of the binary nature of the tree, most benefit from single-cycle assembly level optimizations, assuming a counter limit of $$2^{64}$$ Which as discussed above, is a _lot_ of tree.

Finding the position of the first non-zero bit or counting the number of bits that are set are both primitives necessary for some of the algorithms.
[CLZ](https://developer.arm.com/documentation/dui0802/b/A32-and-T32-Instructions/CLZ) has single-cycle implementations on most architectures. Similarly, `POPCNT` exists.
AMD defined some useful [binary manipulation](https://en.wikipedia.org/wiki/X86_Bit_manipulation_instruction_set) extensions.

Sympathetic instructions, or compact look up table implementations exist for other fundamental operations too.
Most languages have sensible standard wrappers.
While these operations are not strictly O(1) complexity, this has little impact in practice.

## Primitives

### PeakIndex `OnesCount(peakBits & ^((1<<heightIndex)-1)) - 1`

Index of the peak accumulator for the peak with the provided height. Note that
this works with the compact accumulator directly.


### TopPeak `1<<(BitLength(pos+1)-1) - 1`

Smallest, left most (all ones) peak, containing or **equal to** pos

This is essentially a ^2 *floor* function for the accumulation of bits
```

TopPeak(1) = TopPeak(2) = 1
TopPeak(2) = TopPeak(3) = TopPeak(4) = TopPeak(5) = TopPeak(6) = 3
TopPeak(7) = 7

2       7
      /   \
1    3     6    10
    / \  /  \   / \
0  1   2 4   5 8   9 11

```

### TopHeight `BitLength(pos+1)-1`

The height index `g` of the largest perfect peak contained in, or exactly, pos
This is essentially a ^2 *floor* function for the accumulation of bits:

```
TopHeight(1) = TopHeight(2) = 0
TopHeight(2) = TopHeight(3) = TopHeight(4) = TopHeigth(5) = TopHeight(6) = 1
TopHeight(7) = 2

2       7
      /   \
1    3     6    10
    / \  /  \   / \
0  1   2 4   5 8   9 11

```

### SiblingOffset `(2 << g) - 1`
### JumpLeftPerfect `pos - MostSigBit(pos) + 1`
### MostSigBit `1 << (BitLength(pos) - 1)`
  
We assume the following primitives for working with bits as they have obvious implementations.

### BitLength

The minimum number of bits to represent pos. b011 would be 2, b010 would be 2, and b001 would be 1.

### AllOnes

Tests if all bits, from the most significant that is set, are 1, b0111 would be true, b0101 would be false.

### OnesCount

Count of set bits. For example `OnesCount(b101)` is 2

## References

# Algorithm Test Vectors

In this section we provide known answer outputs for the various algorithms for the `MMR(39)`

## MMR(39)

The node index tree for `MMR(39)` is

    g

    4                         30


    3              14                       29
                  / \
                 /   \
                /     \
               /       \
              /         \
    2        6           13            21             28                37
           /   \        /   \        /    \
    1     2     5      9     12     17     20     24       27       33      36
         / \   / \    / \   /  \   /  \   /  \
    0   0   1 3   4  7   8 10  11 15  16 18  19 22  23   25   26  31  32   34  35   38

    .   0   1 2   3  4   5  6   7  8   9 10  11 12  13   14   15  16  17   18  19   20 e

The vertical axis is `g`, the one based height of the tree.

The horizontal axis is `e`, the leaf indices corresponding to the `g=0` nodes in the tree
 
## MMR(39) leaf values

We define `H(v)` for test vector leaf values `f` as the SHA3/256 hash of the the big endian representation of `e`.

TABLE of values TODO

### Normative References

* [RFC9162]: https://datatracker.ietf.org/doc/html/rfc9162
  [RFC9162]
* [RFC9162_VerInc]:https://datatracker.ietf.org/doc/html/rfc9162#name-verifying-an-inclusion-proo
  [RFC9162_VerInc] 2.1.3.1 Generating an Inclusion Proof
* [RFC9162_VerCon]: https://datatracker.ietf.org/doc/html/rfc9162#name-verifying-consistency-betwe
  [RFC9162_VerCon] 2.1.4.2 Verifying Consistency between Two Tree Heads


### Informative References

* [PeterTodd]: https://lists.linuxfoundation.org/pipermail/bitcoin-dev/2016-May/012715.html
  [PeterTodd]
* [CrosbyWallach]: https://static.usenix.org/event/sec09/tech/full_papers/crosby.pdf
  [CrosbyWallach]
* [CrosbySecondaryStorage]: https://static.usenix.org/event/sec09/tech/full_papers/crosby.pdf
  [CrosbySecondaryStorage] 3.3 Storing the log on secondary storage
* [PostOrderTlog]: https://research.swtch.com/tlog#appendix_a
  [PostOrderTlog]
* [KnuthTBT]: https://www-cs-faculty.stanford.edu/~knuth/taocp.html
  [KnuthTBT] 2.3.1 Traversing Binary Trees
* [BNT]: https://eprint.iacr.org/2021/038.pdf
  [BNT]
* [ReyzinYakoubov]: https://eprint.iacr.org/2015/718.pdf
  [ReyzinYakoubov]
* [ProjectSilica]: https://www.tomshardware.com/news/microsoft-repositions-7tb-project-silica-glass-media-as-a-cloud-storage-solution
  [ProjectSilica]