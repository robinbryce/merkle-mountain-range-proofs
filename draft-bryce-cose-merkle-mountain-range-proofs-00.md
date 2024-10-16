---
title: "Merkle Mountain Range for Immediately Verifiable and Replicable Commitments"
abbrev: MMRIVER
cat: exp
docname: draft-bryce-cose-merkle-mountain-range-proofs-latest
submissiontype: IETF
number:
date:
consensus: true
v: 3
area: "Security"
workgroup: "CBOR Object Signing and Encryption"
keyword:
 - Internet-Draft
# venue:
#   group: cose
#   type: Working Group
#   mail: WG@example.com
#   arch: https://example.com/WG
#   github: USER/REPO
#   latest: https://example.com/LATEST
#
author:
 -
    fullname: Robin Bryce
    organization: DataTrails
    # we can't change email once an I-D is accepted, and we have changed company emails twice now.
    # also, this is the email that I contribute using on github.
    email: robinbryce@gmail.com

normative:

informative:


--- abstract

Editors note: This was the original cut. Going to move all of the pedagogy to seperate content.

This specification describes a protocol for the COSE encoding of verifiable commitments to data,
providing immediate verifiability and immediate, safe, replicability of these commitments.
Using this scheme, any replicated copy of the data, or a sub range thereof,
is permanently verifiable and is permanently consistent with the complete data set.
The specification allows for historic commitments and the original data, if desired,
to be pruned without impacting the verifiability of subsequent data or any replicated copies.
Verifiers and auditors may be off line indefinitely, and yet, once back online,
be guaranteed they can prove integrity and consistency, or otherwise,
against any future state they encounter.

--- middle

# Introduction

The term "Merkle Mountain Range" is due to [PeterTodd] and has wide acceptance as the identifier for the approach to managing Merkle trees described by this specification.
This is typically abbreviated as MMR.


An MMR is the unique series of perfect binary merkle trees required to commit its leaves.
The nodes, including the leaves are stored linearly.

       6
     2   5
    0 1 3 4 7

This illustrates `MMR(8)`, which is comprised of two perfect trees.
The first is rooted at 6, and the second is the single leaf element 7.
As leaves are added to an MMR, additional nodes are appended to "merge" with the
preceding tree if the height of the new node matches the height of that tree.
This process repeats as the interior nodes are added until all trees are complete and are of different heights.

Nodes in an MMR are organized linearly in storage, and are strictly write once and append only.
The MMR can also be seen as the node visitation order obtained by the post-order traversal of a series of complete binary trees.
This specification defines how to create, verify and encode proofs of inclusion and consistency for MMR's in CBOR.

Proving and verifying is defined in terms of the cryptographic, asynchronous, accumulator described by [ReyzinYakoubov]

Algorithms for leaf addition and for proving and verifying inclusion and consistency are defined.
Additionally a small number of primitive operations commonly useful in the context of MMR's are provided.
The format of the underlying storage is outside the scope of this document, however some minimal requirements are established for interfacing with it.

There are distinct advantages for maintainers of verifiable data and for parties relying on the verifiability of that data when using this approach:

- Updates to the persistent MMR data can be co-ordination free. Competing writers
  can safely use [Optimistic Concurrency Control](https://en.wikipedia.org/wiki/Optimistic_concurrency_control)
- MMR data does not change once written.
  This makes additions immediately available for replication and caching with mechanisms such as [HTTP_ETag](https://en.wikipedia.org/wiki/HTTP_ETag)
- Proofs of inclusion for a specific element are permanently consistent with all future states of the MMR.
  And, an MMR state which fails this property is provably inconsistent.
- A proof of inclusion can be verified against any historic accumulator,
  provided the element being verified was included in the MMR at the time the accumulator was obtained.
- Proof of consistency can be defined as the proof of inclusion for each old accumulator entry, and so inherit all the properties of the inclusion proofs.
- For a previously saved inclusion proof,
  there are at most log 2 (n) future accumulator states required to show its validity against any future MMR.
  Where n is the count of additions made after the entry was added.
- MMR's can be pruned without breaking these properties of inclusion and consistency.
- The accumulator states naturally emerge from the MMR and are also permanently consistent with future states of the MMR.

The above advantages mostly follow from:

- A post order traversal of a binary tree results in a naturally linear storage organization. As observed  in [CrosbySecondaryStorage].
- An asynchronous cryptographic accumulator naturally emerges when maintaining an MMR in this way.
  [ReyzinYakoubov] defines the properties of these,
  which are particularly relevant here, as "Low update frequency" and "Old-Accumulator Compatibility".
- As the post order traversal index is permanently identifying for any elements siblings and parents,
  the verification path element indices is known and permanent.
  It can be easily computed without needing to materialize the MMR in whole or in part.

Further work in [BNT] defines additional advantages for contexts in which "stream" processing of verifiable data is desirable.
Post-order, Pre-order and in-order tree traversal are defined by [KnuthTBT]

# Conventions and Definitions

{::boilerplate bcp14-tagged}

- `i` shall be the index of any node, including leaf nodes, in the MMR
- `pos` shall be `i+1` and is important only in the implementation of some algorithms.
- `e` shall be the zero based index of leaf entry in the MMR (where only leaves are considered, and interiors are excluded)
- `f` shall be a leaf value, which is `H(x)`
- `h` shall be the 1 based tree height
- `g` shall be the 0 based tree height, `h-1`
- `v` shall be any node, including a leaf node value, which will be the result of `H(x)`.
- `S` shall be any valid MMR size, and is uniquely identifying for an MMR state
- `C` shall be the last node index of any complete MMR.
- `A` shall be the the accumulator for any complete MMR `C`
- `R` shall be the the sparse accumulator, of [ReyzinYakoubov], for any complete MMR `C`
- `H(x)` shall be the SHA-256 digest of any value x
- `||` shall mean concatenation of raw byte representations of the referenced values.
- `D` shall mean the linear array storing all node in the MMR.

In this specification, all numbers are unsigned 64 bit integers. The maximum height of a single tree is 64 (which will have `g=63` for its peak).

Were an MMR to accept a new addition once every 10 milliseconds, it would take roughly 4.6 million millennia to over flow.

Should a system exist that can extend an MMR fast enough for this to be a limitation,
the same advantages that make MMR's convenient to work with also accrue to combinations of MMR's.

# Accumulator Structure

In this section we introduce the asynchronous cryptographic accumulator naturally available in an MMR,
and which is crucial to to a number of the benefits of this approach.

The set of peaks for an MMR of any size is a naturally forming cryptographic accumulator.
This uniquely and succinctly commits the complete history of the MMR. For its formal definition see [ReyzinYakoubov]

As discussed above, an MMR is a series of binary trees maintained logically in descending order of height.
Given only the preceding peaks, and the leaf nodes of the last tree,
it is always possible to complete the last tree.
By fully exploiting this property in the organization of persistent storage,
new entries can be appended without co-ordination between competing writers.

An algorithm to add a single leaf to an MMR is given in [add_leaf_hash](#addleafhash)

The notable distinction from more traditional "mono" roots approach to merkle tree proofs is that, as the MMR grows,
elements in the accumulator change with low frequency, while a mono root is unique for each individual addition.
This frequency is defined as $$\log_2(n)$$ in the number of subsequent leaf additions after the element in question.

It is important to note that while the accumulator state evolves, all nodes in the MMR are write once.
The accumulator simply comprises the nodes at the peaks for the current MMR state.
All paths for proofs of inclusion lead to an accumulator peak, rather than a single "mono" root.

This means many proofs of inclusion are committed by a single entry in an accumulator state, and so share the same root.

The inclusion path for any element is strictly append only,
in addition to the data structure itself being append only.
Consistency proofs *are* the inclusion proofs for the old-accumulator peaks against the accumulator for the future MMR state consistency is being shown for.
An accumulator is at most MMR height long, which is also the maximum length of any single proof of inclusion + 1.

For illustration, consider `MMR(8)` which is a complete MMR with two peaks at node indices 6 and 7.

       6
     2   5
    0 1 3 4 7

The node indices match their location in storage.

MMR's are identified uniquely by their size. Above we have `MMR(8)`, because there are 8 nodes.

An incomplete MMR may still be identified. Here we have `MMR(9)`.

       6
     2   5
    0 1 3 4 7 8

However, its accumulator is that of the most recent complete MMR.

An MMR is said to be complete when all peaks have a distinct height.
The value for node 9 is `H(7 || 8)`,
and adding 8 merges the two, single element, binary trees represented by 7 and 8..

       6
     2   5   9
    0 1 3 4 7 8

The accumulator, described by [ReyzinYakoubov] is the set of peaks, with gaps reserved for the missing peaks.
MMR(8), where a gap is indicated by _ would be:

    [6, _, 7]

The packed form would be:

    [6, 7]

The accumulator for `MMR(10)` is:

    [6, 9, _]

The accumulator, packed or padded, lists the peaks strictly descending order of height.
Given this fact, straight forward primitives for selecting the desired peak can be derived from both packed and un-packed form.
The algorithms in this document work with the packed form exclusively.

Given any index `i` in the MMR, the accumulator for the previous `D[0:i)` nodes
satisfies the sibling dependencies of the inclusion paths of all subsequent `D[i:n]` nodes.

And the accumulator is itself only dependent, for proof of inclusion or consistency, on nodes in `D[i:n]`

This feature of MMR's allows for historic, no longer interesting,
log data to be cleanly purged without impacting the verifiability of the retained log.

It also lends itself to replicability. The linear, self contained,
nature of the organization makes replication of verifiable sub sections of the log extremely convenient.

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

It can be seen that the older the MMR node is,
the less frequently its verification path will be extended to reach a new accumulator entry.

An algorithm to produce the verifying path for any node `i` is given in [inclusion_proof_path](#inclusionproofpath)

In general, given the height `g` of the accumulator peak currently authenticating a node `i`,
the verification path for `i` will not change until the count of MMR leaves reaches $$2^{g+1}$$

The old inclusion path will be a strict prefix of the new inclusion path.

An algorithm defining the packed accumulator for any MMR size `S` is given by [ peaks](#peaks)

An algorithm which sets a bit for each present accumulator peaks in an MMR of size `S` is given by [leaf_count](#leafcount),
the produced value is also the count of leaves present in that MMR.

Lastly, many primitives for working with MMR's rely on a property of the *position* form of an MMR.

The position form for the complete MMR with size 8 MMR(8) is

       7
     3   6
    1 2 4 5 8

Expressing this in binary notation reveals the property that MMR's make extensive use of:

        111
     11     110
    1 10 100  101 1000

The left most node at any height is always "all ones".

# Inclusion Proof

The CBOR representation of an inclusion proof for MMRIVER is

~~~~ cddl
    inclusion-proof = bstr .cbor [

        ; zero based index of any node in the MMR
        index: uint

        ; path from the node to its accumulator peak in MMR(mmr-size)
        inclusion-path: [ + bstr ]
    ]
~~~~

## inclusion_proof_path

`inclusion_proof_path(i, C)` is used to produce the verification paths for inclusion proofs and consistency proofs.

When a path is produced for the purposes of verifying or creating proofs, including the `inclusion-path` referenced above,
the path elements MUST be resolved to the referenced node values.

The [add_leaf_hash](#addleafhash) algorithm illustrates the use of the implementation define storage
method [ get](#get) to accomplish this.
For a pruned MMR, the referenced nodes are either present directly or are present in the accumulator.
Managing the availability of the accumulator is the callers responsibility, and SHOULD typically be accomplished in the implementation specific [ get](#get) method.

Given:

- `C` the index of the last node in any complete MMR which contains `i`.
- `i` the index of the mmr node whose verification path is required.

And the methods:

- [index_height](#indexheight) which obtains the zero based height `g` of any node.

And the constraints:

- `i <= C`

We define `inclusion_proof_path` as:

    def inclusion_proof_path(i, c):

        path = []

        g = index_height(i)

        while True:

            # The sibling of i is at i +/- 2^(g+1)
            siblingoffset = (2 << g)

            # If the index after i is higher, it is the left parent,
            # and i is the right sibling
            if index_height(i+1) > g:

                # The witness to the right sibling is offset behind i
                isibling = i - siblingoffset + 1

                # The parent of a right sibling is stored immediately
                # after
                i += 1
            else:

                # The witness to a left sibling is offset ahead of i
                isibling = i + siblingoffset - 1

                # The parent of a left sibling is stored immediately after
                # its right sibling
                i += siblingoffset

            # When the computed sibling exceedes the range of MMR(C+1),
            # we have completed the path
            if isibling > c:
                return path

            path.append(isibling)

            # Set g to the height of the next item in the path.
            g += 1


## Forward consistency of inclusion proofs

The proof obtained by [inclusion_proof_path](#inclusionproofpath) can be verified against any MMR size which includes `i`,
as it is a prefix of any proof produced by a consistent future log state.

Assuming the constraints:

- `i < c0`
- `c0 < c1`

And the methods:

- [ parent](#parent) which obtains the parent node index of any node

The following hold for all MMR(c0) and MMR(c1):

    path_c0 = inclusion_proof_path(i, c0)
    path_c1 = inclusion_proof_path(parent(path_c0[-1]), c1)
    path = inclusion_proof_path(i, c1) == path_c0 + path_c1

Note: the python specific list access syntax `path_c0[-1]` obtains the last element of the array `path_c0`.

This is the basis on which consistent inclusion, or otherwise, can be show for any individually proven node `i`.

# Receipt of Inclusion

The cbor representation of an inclusion proof for MMRIVER is:

~~~~ cddl
protected-header-map = {
  &(alg: 1) => int
  &(vds: 395) => int
  * cose-label => cose-value
}
~~~~

* alg (label: 1): REQUIRED. Signature algorithm identifier. Value type: int.
* vds (label: 395): REQUIRED. verifiable data structure algorithm identifier. Value type: int.

The unprotected header for an MMRIVER inclusion proof signature is:

~~~~ cddl

inclusion-proofs = [ + inclusion-proof ]

verifiable-proofs = {
  &(inclusion-proof: -1) => inclusion-proofs
}

unprotected-header-map = {
  &(vdp: 396) => verifiable-proofs
  * cose-label => cose-value
}
~~~~

The payload of an MMRIVER inclusion proof signature is the accumulator peak committing to the nodes inclusion,
or the node itself where the proof path is empty. When the path is non-empty,
the parent of the last witness node in the proof is also the accumulator peak.
The algorithm [included_root](#includedroot) obtains this value.

The payload MUST be detached.
Detaching the payload forces verifiers to recompute the root from the inclusion proof signature,
this protects against implementation errors where the signature is verified but the merkle root does not match the inclusion proof.

## Verifying the Receipt of inclusion

1. Recompute the root from the path and the element for which inclusion is being shown using [included_root](#includedroot).
   For a leaf node, this is obtained via `H(x)` as defined by the application.
   For an interior node, this is read directly from the log, or a replicated portion of it,
   using the implementation define storage method [ get](#get).
1. Verify the signature using the obtained root as the detached payload.

## included_root

The algorithm `included_root` calculates the accumulator peak for the provided proof and node value.
Note that both interior and leaf nodes are handled identically.

Given:

- `i` is the index the `nodeHash` is to be shown at
- `nodehash` the value whose inclusion is to be shown
- `proof` is the path of ibling values committing i. They recreate the unique
  accumulator peak that committed i to the MMR state from which the proof was produced.

And the methods:

- [index_height](#indexheight) which obtains the zero based height `g` of any node.
- [hash_pospair64](#hashpospair64) which applies `H` to the new node position and its children.

We define `included_root` as:

    def included_root(i, nodehash, proof):

        root = nodehash

        g = index_height(i)

        for sibling in proof:

            # If the index after i is higher, it is the left parent,
            # and i is the right sibling

            if index_height(i + 1) > g:

                # The parent of a right sibling is stored immediately after

                i = i + 1

                # Set `root` to `H(i+1 || sibling || root)`
                root = hash_pospair64(i + 1, sibling, root)
            else:

                # The parent of a left sibling is stored immediately after
                # its right sibling.

                i = i + (2 << g)

                # Set `root` to `H(i+1 || root || sibling)`
                root = hash_pospair64(i + 1, root, sibling)

            # Set g to the height of the next item in the path.
            g = g + 1

        # If the path length was zero, the original nodehash is returned
        return root

# Consistency Proof

The cbor representation of a consistency proof for MMRIVER is:

~~~~ cddl

consistency-path = [ * bstr ]

consistency-proof =  bstr .cbor [

    ; previous MMR size
    mmr-size-1: uint

    ; latest MMR size
    mmr-size-2: uint

    ; the inclusion path from each accumulator peak in
    ; MMR(mmr-size-1) to its new accumulator peak in
    ; MMR(mmr-size-2).
    consistency-paths: [ + consistency-path ]
]
~~~~

## consistency_proof_path

Creates a proof of consistency between the identified MMR's.

The returned value is a list containing a single proof of inclusion for each peak
from the first MMR state in the second MMR state.

When a path is produced for the purposes of verifying or creating proofs,
including the `inclusion-path` referenced above,
the path elements MUST be resolved to the referenced node values.

The [add_leaf_hash](#addleafhash) algorithm illustrates the use of the implementation define
storage method [ get](#get) to accomplish this.

Given:

- `ifrom` is the last node of the complete `MMR(ifrom + 1)`
- `ito` is the last node of the complete `MMR(ito + 1)`

And the methods:

- [inclusion_proof_path](#inclusionproofpath)
- [ peaks](#peaks)

And the constraints:

- `ifrom <= ito`

We define `consistency_proof_paths` as:

    def consistency_proof_paths(ifrom, ito):

        proof = []

        for i in peaks(ifrom):
            proof.append(inclusion_proof_path(i, ito))

        return proof


# Receipt of Consistency

The cbor representation of an inclusion proof for MMRIVER is:

~~~~ cddl
protected-header-map = {
  &(alg: 1) => int
  &(vds: 395) => int
  * cose-label => cose-value
}
~~~~

* alg (label: 1): REQUIRED. Signature algorithm identifier. Value type: int.
* vds (label: 395): REQUIRED. verifiable data structure algorithm identifier. Value type: int.

The unprotected header for an MMRIVER inclusion proof signature is:

~~~~ cddl

consistency-proofs = [ + consistency-proof ]

verifiable-proofs = {
  &(consistency-proof: -2) => consistency-proofs
}

unprotected-header-map = {
  &(vdp: 396) => verifiable-proofs
  * cose-label => cose-value
}
~~~~

The payload MUST be detached. Detaching the payload forces verifiers to recompute the roots from the consistency proof signature.
This protects against implementation errors where the signature is verified but the nodes in the new accumulator do not match the inclusion proofs for the nodes comprising the old accumulator.

## Verifying the Receipt of consistency

1. Recompute the prefix of the accumulator for `MMR(mmr-size-2)` from the proofs in the receipt
   using the algorithm [consistent_roots](#consistentroots)
2. Verify the signature using the obtained prefix as the detached payload.

### consistent_roots

`consistent_roots` is supplied with the accumulator from which consistency is being shown,
and an inclusion proof for each accumulator entry in a future MMR state.
The algorithm recovers the necessary prefix (peaks) of the future accumulator against which the proofs were obtained.

It is typical that many nodes in the original accumulator share the same peak in the new accumulator.

The returned list will be a descending height ordered list of elements from the accumulator
for the consistent future state.
It may be *exactly* the future accumulator or it may be a prefix of it.
The order of the roots returned by `consistent_roots` matches the order of the nodes in the accumulator.

Implementations MUST require that the number of peaks returned by [ peaks](#peaks)`(ifrom)` equals the number of entries in `accumulatorfrom`.

Given:

- `ifrom` the last node index in the complete MMR from which consistency was proven.
- `accumulatorfrom` the node values correponding to the peaks of the accumulator at `MMR(mmr-size-1)`
- `proofs` the inclusion proofs for each node in `accumulatorfrom` in `MMR(mmr-size-2)`

And the methods:

- [included_root](#includedroot)
- [ peaks](#peaks)

We define `consistent_roots` as:

    def consistent_roots(ifrom, accumulatorfrom, proofs):

        frompeaks = peaks(ifrom)

        # if length(frompeaks) != length(proofs) -> ERROR

        roots = []
        for i in range(len(accumulatorfrom)):
            root = included_root(
                frompeaks[i], accumulatorfrom[i], proofs[i])

            # The nature of MMR's is that many nodes are committed by the
            # same accumulator peak, and that peak changes with
            # low frequency.
            if roots and roots[-1] == root:
                continue
            roots.append(root)

        return roots


# Appending to an MMR

## Leaf Node Addition

When a new node is appended, if its height matches the height of its immediate predecessor,
then we can complete a larger tree by merging the adjacent peaks,
which we do by appending a new node which takes the adjacent peaks as its left and right children.
This process proceeds until there are no more completable sub trees,
needing only the previous peak at each step.
For every even numbered node addition, adding a new leaf will always merge at least one preceding peak.


### add_leaf_hash

`add_leaf_hash(f)` adds the leaf hash value f to the MMR. The resulting MMR is always complete.

As defined in [Node values](#node-values), the interior nodes each commit the
size of the MMR, which is just the node index + 1.
This makes it impossible to create a leaf whose value collides with an interior node.
This protects the MMR against second pre-image attacks.

It is assumed that the algorithm terminates and returns on any transient error.

Given:

- `f` the leaf value resulting from `H(x)` for the caller defined leaf value `x`
- `db` an interface supporting the [ append](#append) and [ get](#get) implementation defined storage methods.

And the methods:

- [index_height](#indexheight)
- [hashpospair64](#hashpospair64)

We define `add_leaf_hash` as

    def add_leaf_hash(db, f: bytes):

        # Set g to 0, the height of the leaf item f
        g = 0

        # Set i to the result of invoking Append(f)
        i = db.append(f)

        # If index_height(i) is greater than g (#looptarget)
        while index_height(i) > g:

            # Set ileft to the index of the left child of i,
            # which is i - 2^(g+1)

            ileft = i - (2 << g)

            # Set iright to the index of the the right child of i,
            # which is i - 1

            iright = i - 1

            # Set v to H(i + 1 || Get(ileft) || Get(iright))
            # Set i to the result of invoking Append(v)

            i = db.append(
                hash_pospair64(i+1, db.get(ileft), db.get(iright)))

            1. Set g to the height of the new i, which is g + 1`
            g += 1

        return i


## Implementation defined storage methods

The following methods are assumed to be available to the implementation. Very minimal requirements are specified.

Informally, the storage must be array like and have no gaps.

### Get

Reads the value from the MMR at the supplied index.

Used by any algorithm which needs access to node values.

The read MUST be consistent with any other calls to Append or Get within the same algorithm invocation.

Get MAY fail for transient reasons.

### Append


Appends new node to storage and returns the index that will be occupied by the node provided to the next call to append.

The implementation MUST guarantee that the results of Append are immediately available to Get calls in the same invocation of the algorithm OR fail.

Append MUST return the node `i` identifying the node location which comes next.

There MUST be a 1 to 1 correspondence between the MMR node index and the storage location of the node's value.

The implementation MUST guarantee that the storage organization is linear and non-sparse.

Implementations MAY rely on the verifiable properties of the MMR,
or optimistic concurrency control, to afford detection of accidental or competing overwrites.

Used only by [add_leaf_hash](#addleafhash)

The implementation MAY defer commitment to underlying persistent storage.

Append MAY fail for transient reasons.

## Node values

Interior nodes in the MMR SHALL prefix the value provided to `H(x)` with `pos`.

The value `v` for any interior node MUST be `H(pos || Get(LEFT_CHILD) || Get(RIGHT_CHILD))`

This naturally affords the pre-image resistance typically obtained with specific leaf/interior node prefixes.
Nonce schemes to account for duplicate leaves are also un-necessary as a result,
but MAY be included by the application for other reasons.

The algorithm for leaf addition is provided the result of `H(x)` directly.
The application MUST define how it produces `x` such that parties reliant on the system for verification can recreate `H(x)`.

### hash_pospair64

Returns `H(pos || a || b)`, which is the value for the node identified by index `pos - 1`

All interior nodes MUST commit the size of the MMR created by their addition by pre-pending the size to its child hashes.

Editors note: How this draft accommodates hash alg agility is tbd.

Given:

- `pos` the size of the MMR whose last node index is `pos - 1`
- `a` the first value to include in the hash after `pos`
- `b` the second value to include in the hash after `pos`

And the constraints:

- `pos < 2^64`
- `a` and `b` MUST be hashes produced by the appropriate hash alg.

We define `hash_pospair64` as:

    def hash_pospair64(pos, a, b):

        # Note: Hash algorithm agility is tbd, this example uses SHA-256
        h = hashlib.sha256()

        # Take the big endian representation of pos
        h.update(pos.to_bytes(8, byteorder="big", signed=False))
        h.update(a)
        h.update(b)
        return h.digest()


# Essential supporting algorithms

## index_height

`index_height(i)` returns the zero based height `g` of the node index `i`

Given:

- `i` the index of any mmr node.

We define `index_height` as:

    def index_height(i) -> int:
        pos = i + 1
        while not all_ones(pos):
          pos = pos - most_sig_bit(pos) + 1

        return bit_length(pos) - 1

## peaks

`peaks(i)` returns the peak indices for `MMR(i+1)`, which is also its accumulator.


Assumes MMR(i+1) is complete, implementations can check for this condition by
testing the height of i+1

Given:

- `i` the index of any mmr node.

We define `peaks` as:


    def peaks(i):
        peak = 0
        peaks = []
        s = i+1
        while s != 0:
            # find the highest peak size in the current MMR(s)
            highest_size = (1 << log2floor(s+1)) - 1
            peak = peak + highest_size
            peaks.append(peak-1)
            s -= highest_size

        return peaks

# Security Considerations

TODO Security

# IANA Considerations

Editors note: Hash agility is desired. We can start with SHA-256. Two of the referenced implementations use BLAKE2b-256,
We would like to add support for SHA3-256, SHA3-512, and possibly Keccak and Pedersen.

## Additions to Existing Registries

Editors note: we will require an addition to the CoMETER spec once it is accepted.

## New Registries


--- back

# References

## Normative References

* [RFC9162]: https://datatracker.ietf.org/doc/html/rfc9162
  [RFC9162]
* [RFC9162_VerInc]:https://datatracker.ietf.org/doc/html/rfc9162#name-verifying-an-inclusion-proo
  [RFC9162_VerInc] 2.1.3.1 Generating an Inclusion Proof
* [RFC9162_VerCon]: https://datatracker.ietf.org/doc/html/rfc9162#name-verifying-consistency-betwe
  [RFC9162_VerCon] 2.1.4.2 Verifying Consistency between Two Tree Heads


## Informative References

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


# Supplemental, commonly useful, supporting algorithms

## leaf_count

`leaf_count(i)` Returns a the count of leaves in `MMR(i+1)`

The bits of the count also form a mask, where a single bit is set for each
peak present in the accumulator. The bit position is the height of the
binary tree committing the elements to the corresponding accumulator entry.

The (sparse) accumulator entry is also derived from the height as `accummulator[len(accumulator) - bitpos]`

Where accumulator is the list of accumulator peak indices in descending order of
height and bitpos is any bit set in the leaf count.

Given:

- `i` the index of any mmr node.

And the methods:

- [bit_length](#bitlength) which returns the number of bits required to represent the argument.

We define `leaf_count` as:

    def leaf_count(i):

        s = i + 1

        # Establish the largest relevant complete tree as our starting point
        peaksize = (1 << bit_length(s)) - 1
        peakmap = 0
        while peaksize > 0:
            peakmap <<= 1

            # At each round we halve peak size, if doing so causes our
            # current value for s to excede the remaining peak size, we need
            # the peak in the accumulator.
            if s >= peaksize:
                s -= peaksize
                peakmap |= 1
            peaksize >>= 1

        return peakmap


## mmr_index

Returns the node index `i` locating the leaf in the MMR

Given:

- `e` the index of a leaf (where the leaves are considered in isolation)

And the methods:

- [bit_length](#bitlength) which returns the number of bits required to represent the argument.

We define `mmr_index` as:

    def mmr_index(e):
        sum = 0
        while e > 0:
            # The bit length of e is its 1 based height `h`
            h = bit_length(e)
            sum += (1 << h) - 1
            half = 1 << (h - 1)
            e -= half
        return sum

## parent

Returns the parent of the supplied node index.

Given:

- `i` the index of any mmr node.

And the methods:

- [index_height](#indexheight)


We define `parent` as:

    def parent(i):
        g = index_height(i)

        if index_height(i + 1) > g:
            # The next node is higher, so it is the parent.
            return i + 1

        # i is the left sibling, so the parent is the offset to the right
        # sibling + 1, which is just 2^(g+1)
        return i + (2 << g)


## complete_mmr

Return `i` if `MMR(i+1)` is complete, and the next complete node index otherwise.

Many of the algorithms specify dealing with _complete_ mmr's.

This algorithm returns i if it is complete, and the index of the next node
corresponding to a complete mmr otherwise.

Given:

- `i` a node index

And the methods:

- [index_height](#indexheight)


We define `complate_mmr` as:

    def complete_mmr(i):

        h0 = index_height(i)
        h1 = index_height(i + 1)
        while h0 < h1:
            i += 1
            h0 = h1
            h1 = index_height(i + 1)

        return i

# Assumed bit primitives

## A Note On Hardware Sympathy

MMR's are a series of complete binary trees followed by at most one incomplete tree. This is sometimes referred to as a flat base tree. In these constructions many operations are formally $$\log_2(n)$$

However, precisely because of the binary nature of the MMR construction, most benefit from single-cycle assembly level optimizations, assuming a counter limit of $$2^{64}$$ Which as discussed above, is a _lot_ of MMR.

Finding the position of the first non-zero bit or counting the number of bits that are set are both primitives necessary for some of the algorithms.
[CLZ](https://developer.arm.com/documentation/dui0802/b/A32-and-T32-Instructions/CLZ) has single-cycle implementations on most architectures. Similarly, `POPCNT` exists.
AMD defined some useful [binary manipulation](https://en.wikipedia.org/wiki/X86_Bit_manipulation_instruction_set) extensions.

Sympathetic instructions, or compact look up table implementations exist for other fundamental operations too.
Most languages have sensible standard wrappers.
While these operations are not strictly O(1) complexity, this has little impact in practice.

## log2floor

Returns the floor of log base 2 x

    def log2floor(x):
        return x.bit_length() - 1


## most_sig_bit

Returns the mask for the the most significant bit in pos

`1 << (bit_length(pos) - 1)`

Expressed in python

    def most_sig_bit(pos) -> int:
        return 1 << (pos.bit_length() - 1)

We assume the following primitives for working with bits as they commonly have library or hardware support.

## bit_length

The minimum number of bits to represent pos. b011 would be 2, b010 would be 2, and b001 would be 1.

In python,

    def bit_length(pos):
        return pos.bit_length()

## all_ones

Tests if all bits, from the most significant that is set, are 1, b0111 would be true, b0101 would be false.

In python,

    def all_ones(pos) -> bool:
        msb = most_sig_bit(pos)
        mask = (1 << (msb + 1)) - 1
        return pos == mask

## ones_count

Count of set bits. For example `ones_count(b101)` is 2

## trailing_zeros

The count of nodes above and to the left of `pos`

In python,

    (v & -v).bit_length() - 1


# Implementation Status

Note to RFC Editor: Please remove this section as well as references to BCP205 before AUTH48.

This section records the status of known implementations of the protocol defined by this specification at the time of posting of this Internet-Draft, and is based on a proposal described in BCP205.
The description of implementations in this section is intended to assist the IETF in its decision processes in progressing drafts to RFCs.
Please note that the listing of any individual implementation here does not imply endorsement by the IETF.
Furthermore, no effort has been spent to verify the information presented here that was supplied by IETF contributors.
This is not intended as, and must not be construed to be, a catalog of available implementations or their features.
Readers are advised to note that other implementations may exist.

According to BCP205,
"this will allow reviewers and working groups to assign due consideration to documents that have the benefit of running code, which may serve as evidence of valuable experimentation and feedback that have made the implemented protocols more mature.
It is up to the individual working groups to use this information as they see fit".

## Implementers

### DataTrails

An open-source implementation was initiated and is maintained by Data Trails Inc. - DataTrails.

Uses SHA-256 as the hash alg

#### Implementation Name

An application demonstrating the concepts is available at [https://app.datatrails.ai/](https://app.datatrails.ai/).

#### Implementation URL

An open-source implementation is available at:

- https://github.com/datatrails/go-datatrails-merklelog

#### Maturity

Used in production. SEMVER unstable (no backwards compat declared yet)

### Peter Todd

Almost compatible, where here the leaf hash is not defined, in Peter Todd's formal description, all nodes, including the leaves include the position in the hash.
In this specification, leaf hashes are added 'as is'. Interior nodes commit to the size of the entire MMR including the interior node.

#### Implementation URL

- https://github.com/proofchains/python-proofmarshal/blob/master/proofmarshal/mmr.py

#### Maturity

Reference implementation, but the "original".

### Robin Bryce

#### Implementation URL

A minimal reference implementation of this draft. Used to generate the test vectors in this draft, is available at:

- https://github.com/robinbryce/merkle-mountain-range-proofs/blob/main/algorithms.py


#### Maturity

Reference only

### Mimblewimble ?

Is specifically committing to positions as we describe, but is committing zero based indices,
and uses BLAKE2B as the HASH-ALG.
Accounting for those differences, their commitment trees would be compatible with this draft.

#### Implementation URL

An implementation is available here:

- https://github.com/mimblewimble/grin/blob/master/doc/mmr.md (Grin is a rust implementation of the mimblewimble protocol)
- https://github.com/BeamMW/beam/blob/master/core/merkle.cpp (Beam is a C++ implementation of the mimblewimble protocol)

### ZCash ?

Uses an incompatible scheme for committing the sub trees, and additionally specifies how the leaf hash is produced.

- https://zips.z.cash/zip-0221

#### Implementation URL


TODO: check if they are to positions as we describe, if so their commitment trees should be compatible with this draft.


The code's level of maturity is considered to be "prototype".

### Herodotus

#### Implementation URL

https://github.com/HerodotusDev/rust-accumulators

Production, supports keccak, posiedon & pedersen hash algs

### Tari-Project

Incompatible, does not include commitment of position in the interior node hash

#### Implementation URL

- https://github.com/tari-project/tari/blob/development/base_layer/mmr/src/merkle_mountain_range.rs


# Algorithm Test Vectors

In this section we provide known answer outputs for the various algorithms for the `MMR(39)`

## MMR(39)

Editors note: The MMR table is split in two due to format restrictions.

The node indices for `MMR(39)` (leaves 0-15) are

    g

    4                         30


    3              14                       29
                  / \
                 /   \
                /     \
               /       \
              /         \
    2        6           13            21             28
           /   \        /   \        /    \
    1     2     5      9     12     17     20     24       27
         / \   / \    / \   /  \   /  \   /  \
    0   0   1 3   4  7   8 10  11 15  16 18  19 22  23   25   26

    .   0   1 2   3  4   5  6   7  8   9 10  11 12  13   14   15 e


The node indices for `MMR(39)` (leaves 16 - 20) are

    g

    2           37

    1       33      36

    0     31  32   34  35   38

    .     16  17   18  19   20 e


The vertical axis is `g`, the zero based height of the MMR.

The horizontal axis is `e`, the leaf indices corresponding to the `g=0` nodes in the MMR

## MMR(39) leaf values (excluding interior nodes)

We define `H(v)` for test vector leaf values `f` as the SHA-256 hash of the the big endian representation of `e`.

| e |                          leaf values                           |
|--:|----------------------------------------------------------------|
|  0|af5570f5a1810b7af78caf4bc70a660f0df51e42baf91d4de5b2328de0e83dfc|
|  1|cd2662154e6d76b2b2b92e70c0cac3ccf534f9b74eb5b89819ec509083d00a50|
|  2|d5688a52d55a02ec4aea5ec1eadfffe1c9e0ee6a4ddbe2377f98326d42dfc975|
|  3|8005f02d43fa06e7d0585fb64c961d57e318b27a145c857bcd3a6bdb413ff7fc|
|  4|a3eb8db89fc5123ccfd49585059f292bc40a1c0d550b860f24f84efb4760fbf2|
|  5|4c0e071832d527694adea57b50dd7b2164c2a47c02940dcf26fa07c44d6d222a|
|  6|8d85f8467240628a94819b26bee26e3a9b2804334c63482deacec8d64ab4e1e7|
|  7|0b5000b73a53f0916c93c68f4b9b6ba8af5a10978634ae4f2237e1f3fbe324fa|
|  8|e66c57014a6156061ae669809ec5d735e484e8fcfd540e110c9b04f84c0b4504|
|  9|998e907bfbb34f71c66b6dc6c40fe98ca6d2d5a29755bc5a04824c36082a61d1|
| 10|5bc67471c189d78c76461dcab6141a733bdab3799d1d69e0c419119c92e82b3d|
| 11|1b8d0103e3a8d9ce8bda3bff71225be4b5bb18830466ae94f517321b7ecc6f94|
| 12|7a42e3892368f826928202014a6ca95a3d8d846df25088da80018663edf96b1c|
| 13|aed2b8245fdc8acc45eda51abc7d07e612c25f05cadd1579f3474f0bf1f6bdc6|
| 14|561f627b4213258dc8863498bb9b07c904c3c65a78c1a36bca329154d1ded213|
| 15|1209fe3bc3497e47376dfbd9df0600a17c63384c85f859671956d8289e5a0be8|
| 16|1664a6e0ea12d234b4911d011800bb0f8c1101a0f9a49a91ee6e2493e34d8e7b|
| 17|707d56f1f282aee234577e650bea2e7b18bb6131a499582be18876aba99d4b60|
| 18|4d75f61869104baa4ccff5be73311be9bdd6cc31779301dfc699479403c8a786|
| 19|0764c726a72f8e1d245f332a1d022fffdada0c4cb2a016886e4b33b66cb9a53f|
| 20|e9a5f5201eb3c3c856e0a224527af5ac7eb1767fb1aff9bd53ba41a60cde9785|

## MMR(39) node values (including leaves)

 | i  |                          node values                           |
 |:---|----------------------------------------------------------------|
 | 0|af5570f5a1810b7af78caf4bc70a660f0df51e42baf91d4de5b2328de0e83dfc|
 | 1|cd2662154e6d76b2b2b92e70c0cac3ccf534f9b74eb5b89819ec509083d00a50|
 | 2|ad104051c516812ea5874ca3ff06d0258303623d04307c41ec80a7a18b332ef8|
 | 3|d5688a52d55a02ec4aea5ec1eadfffe1c9e0ee6a4ddbe2377f98326d42dfc975|
 | 4|8005f02d43fa06e7d0585fb64c961d57e318b27a145c857bcd3a6bdb413ff7fc|
 | 5|9a18d3bc0a7d505ef45f985992270914cc02b44c91ccabba448c546a4b70f0f0|
 | 6|827f3213c1de0d4c6277caccc1eeca325e45dfe2c65adce1943774218db61f88|
 | 7|a3eb8db89fc5123ccfd49585059f292bc40a1c0d550b860f24f84efb4760fbf2|
 | 8|4c0e071832d527694adea57b50dd7b2164c2a47c02940dcf26fa07c44d6d222a|
 | 9|b8faf5f748f149b04018491a51334499fd8b6060c42a835f361fa9665562d12d|
 |10|8d85f8467240628a94819b26bee26e3a9b2804334c63482deacec8d64ab4e1e7|
 |11|0b5000b73a53f0916c93c68f4b9b6ba8af5a10978634ae4f2237e1f3fbe324fa|
 |12|6f3360ad3e99ab4ba39f2cbaf13da56ead8c9e697b03b901532ced50f7030fea|
 |13|508326f17c5f2769338cb00105faba3bf7862ca1e5c9f63ba2287e1f3cf2807a|
 |14|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
 |15|e66c57014a6156061ae669809ec5d735e484e8fcfd540e110c9b04f84c0b4504|
 |16|998e907bfbb34f71c66b6dc6c40fe98ca6d2d5a29755bc5a04824c36082a61d1|
 |17|f4a0db79de0fee128fbe95ecf3509646203909dc447ae911aa29416bf6fcba21|
 |18|5bc67471c189d78c76461dcab6141a733bdab3799d1d69e0c419119c92e82b3d|
 |19|1b8d0103e3a8d9ce8bda3bff71225be4b5bb18830466ae94f517321b7ecc6f94|
 |20|0a4d7e66c92de549b765d9e2191027ff2a4ea8a7bd3eb04b0ed8ee063bad1f70|
 |21|61b3ff808934301578c9ed7402e3dd7dfe98b630acdf26d1fd2698a3c4a22710|
 |22|7a42e3892368f826928202014a6ca95a3d8d846df25088da80018663edf96b1c|
 |23|aed2b8245fdc8acc45eda51abc7d07e612c25f05cadd1579f3474f0bf1f6bdc6|
 |24|dd7efba5f1824103f1fa820a5c9e6cd90a82cf123d88bd035c7e5da0aba8a9ae|
 |25|561f627b4213258dc8863498bb9b07c904c3c65a78c1a36bca329154d1ded213|
 |26|1209fe3bc3497e47376dfbd9df0600a17c63384c85f859671956d8289e5a0be8|
 |27|6b4a3bd095c63d1dffae1ac03eb8264fdce7d51d2ac26ad0ebf9847f5b9be230|
 |28|4459f4d6c764dbaa6ebad24b0a3df644d84c3527c961c64aab2e39c58e027eb1|
 |29|77651b3eec6774e62545ae04900c39a32841e2b4bac80e2ba93755115252aae1|
 |30|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
 |31|1664a6e0ea12d234b4911d011800bb0f8c1101a0f9a49a91ee6e2493e34d8e7b|
 |32|707d56f1f282aee234577e650bea2e7b18bb6131a499582be18876aba99d4b60|
 |33|0c9f36783b5929d43c97fe4b170d12137e6950ef1b3a8bd254b15bbacbfdee7f|
 |34|4d75f61869104baa4ccff5be73311be9bdd6cc31779301dfc699479403c8a786|
 |35|0764c726a72f8e1d245f332a1d022fffdada0c4cb2a016886e4b33b66cb9a53f|
 |36|c861552e9e17c41447d375c37928f9fa5d387d1e8470678107781c20a97ebc8f|
 |37|6a169105dcc487dbbae5747a0fd9b1d33a40320cf91cf9a323579139e7ff72aa|
 |38|e9a5f5201eb3c3c856e0a224527af5ac7eb1767fb1aff9bd53ba41a60cde9785|

## Peak (accumulator) indices and values for all MMR's to MMR(39)

(peaks)[#peaks] will produce the following index lists.

| i|        accumulator peaks |
|--|--------------------------|
| 0| 0|
| 2| 2|
| 3| 2, 3|
| 6| 6|
| 7| 6, 7|
| 9| 6, 9|
|10| 6, 9, 10|
|14| 14|
|15| 14, 15|
|17| 14, 17|
|18| 14, 17, 18|
|21| 14, 21|
|22| 14, 21, 22|
|24| 14, 21, 24|
|25| 14, 21, 24, 25|
|30| 30|
|31| 30, 31|
|33| 30, 33|
|34| 30, 33, 34|
|37| 30, 37|
|38| 30, 37, 38|

The indices will retrieve the following values from the MMR. The row indices,
starting with 0, are the corresponding mmr node indices 0-38

|        accumulator peaks |
|--------------------------|
|af5570f5a1810b7af78caf4bc70a660f0df51e42baf91d4de5b2328de0e83dfc|
|ad104051c516812ea5874ca3ff06d0258303623d04307c41ec80a7a18b332ef8|
|ad104051c516812ea5874ca3ff06d0258303623d04307c41ec80a7a18b332ef8, d5688a52d55a02ec4aea5ec1eadfffe1c9e0ee6a4ddbe2377f98326d42dfc975|
|827f3213c1de0d4c6277caccc1eeca325e45dfe2c65adce1943774218db61f88|
|827f3213c1de0d4c6277caccc1eeca325e45dfe2c65adce1943774218db61f88, a3eb8db89fc5123ccfd49585059f292bc40a1c0d550b860f24f84efb4760fbf2|
|827f3213c1de0d4c6277caccc1eeca325e45dfe2c65adce1943774218db61f88, b8faf5f748f149b04018491a51334499fd8b6060c42a835f361fa9665562d12d|
|827f3213c1de0d4c6277caccc1eeca325e45dfe2c65adce1943774218db61f88, b8faf5f748f149b04018491a51334499fd8b6060c42a835f361fa9665562d12d, 8d85f8467240628a94819b26bee26e3a9b2804334c63482deacec8d64ab4e1e7|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112, e66c57014a6156061ae669809ec5d735e484e8fcfd540e110c9b04f84c0b4504|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112, f4a0db79de0fee128fbe95ecf3509646203909dc447ae911aa29416bf6fcba21|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112, f4a0db79de0fee128fbe95ecf3509646203909dc447ae911aa29416bf6fcba21, 5bc67471c189d78c76461dcab6141a733bdab3799d1d69e0c419119c92e82b3d|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112, 61b3ff808934301578c9ed7402e3dd7dfe98b630acdf26d1fd2698a3c4a22710|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112, 61b3ff808934301578c9ed7402e3dd7dfe98b630acdf26d1fd2698a3c4a22710, 7a42e3892368f826928202014a6ca95a3d8d846df25088da80018663edf96b1c|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112, 61b3ff808934301578c9ed7402e3dd7dfe98b630acdf26d1fd2698a3c4a22710, dd7efba5f1824103f1fa820a5c9e6cd90a82cf123d88bd035c7e5da0aba8a9ae|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112, 61b3ff808934301578c9ed7402e3dd7dfe98b630acdf26d1fd2698a3c4a22710, dd7efba5f1824103f1fa820a5c9e6cd90a82cf123d88bd035c7e5da0aba8a9ae, 561f627b4213258dc8863498bb9b07c904c3c65a78c1a36bca329154d1ded213|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7, 1664a6e0ea12d234b4911d011800bb0f8c1101a0f9a49a91ee6e2493e34d8e7b|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7, 0c9f36783b5929d43c97fe4b170d12137e6950ef1b3a8bd254b15bbacbfdee7f|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7, 0c9f36783b5929d43c97fe4b170d12137e6950ef1b3a8bd254b15bbacbfdee7f, 4d75f61869104baa4ccff5be73311be9bdd6cc31779301dfc699479403c8a786|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7, 6a169105dcc487dbbae5747a0fd9b1d33a40320cf91cf9a323579139e7ff72aa|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7 6a169105dcc487dbbae5747a0fd9b1d33a40320cf91cf9a323579139e7ff72aa, e9a5f5201eb3c3c856e0a224527af5ac7eb1767fb1aff9bd53ba41a60cde9785|


## node height, leaf count and peak mask

These tables cover the outputs of `index_height` and `leaf_count`.
`g=index_height`, `e` & `m` are the decimal and binary representations of `leaf_count`

`m` is the bit map of peaks, and also the binary representation of `e`

|i|0    |1    |2    |3    |4    |5    |6    |7    |8    |9    |
|-|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|
|g|0    |0    |1    |0    |0    |1    |2    |0    |0    |1    |
|e|1    |1    |2    |3    |3    |3    |4    |5    |5    |6    |
|m|1    |1    |10   |11   |11   |11   |100  |101  |101  |110  |

|i|10   |11   |12   |13   |14   |15   |16   |17   |18   |19   |20   |21   |
|-|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|
|g|0    |0    |1    |2    |3    |0    |0    |1    |0    |0    |1    |2    |
|e|7    |7    |7    |7    |8    |9    |9    |10   |11   |11   |11   |12   |
|m|111  |111  |111  |111  |1000 |1001 |1001 |1010 |1011 |1011 |1011 |1100 |


|i|22   |23   |24   |25   |26   |27   |28   |29   |30   |31   |32   |33   |
|-|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|
|g|0    |0    |1    |0    |0    |1    |2    |3    |4    |0    |0    |1    |
|e|13   |13   |14   |15   |15   |15   |15   |15   |16   |17   |17   |18   |
|m|1101 |1101 |1110 |1111 |1111 |1111 |1111 |1111 |10000|10001|10001|10010|

|i|34   |35   |36   |37   |38   |
|-|-----|-----|-----|-----|-----|
|g|0    |0    |1    |2    |0    |
|e|19   |19   |19   |20   |21   |
|m|10011|10011|10011|10100|10101|

## Inclusion proof paths and the associated accumulator states

- The inclusion path column defines the outputs of [inclusion_proof_path](#inclusionproofpath))
- The accumlator column shows the output of [peaks][#peaks], but adjusted index the storage.
- The accumulator root index shows the output of PeakIndex
- The root column shows the value in the storage corresponding to the index in accumulator selected by the accumulator_root_index. Eg `storage[]

This table illustrates the low, and predictably reducing, rate with which the root changes for any single entry in the MMR.
Each time the root for a leaf changes, the validity period doubles.

This table also ilustrates that the verification path for any single entry only ever grows.
It is therefore guaranteed to be a prefix of any future path for the same entry.

| i  | MMR  |inclusion path       |accumulator|accumulator root index|
|   0|in MMR(1)|[]                  |[0]                 |0   |
|   0|in MMR(3)|[1]                 |[2]                 |0   |
|   0|in MMR(4)|[1]                 |[2, 3]              |0   |
|   0|in MMR(7)|[1, 5]              |[6]                 |0   |
|   0|in MMR(8)|[1, 5]              |[6, 7]              |0   |
|   0|in MMR(10)|[1, 5]              |[6, 9]              |0   |
|   0|in MMR(11)|[1, 5]              |[6, 9, 10]          |0   |
|   0|in MMR(15)|[1, 5, 13]          |[14]                |0   |
|   0|in MMR(16)|[1, 5, 13]          |[14, 15]            |0   |
|   0|in MMR(18)|[1, 5, 13]          |[14, 17]            |0   |
|   0|in MMR(19)|[1, 5, 13]          |[14, 17, 18]        |0   |
|   0|in MMR(22)|[1, 5, 13]          |[14, 21]            |0   |
|   0|in MMR(23)|[1, 5, 13]          |[14, 21, 22]        |0   |
|   0|in MMR(25)|[1, 5, 13]          |[14, 21, 24]        |0   |
|   0|in MMR(26)|[1, 5, 13]          |[14, 21, 24, 25]    |0   |
|   0|in MMR(31)|[1, 5, 13, 29]      |[30]                |0   |
|   0|in MMR(32)|[1, 5, 13, 29]      |[30, 31]            |0   |
|   0|in MMR(34)|[1, 5, 13, 29]      |[30, 33]            |0   |
|   0|in MMR(35)|[1, 5, 13, 29]      |[30, 33, 34]        |0   |
|   0|in MMR(38)|[1, 5, 13, 29]      |[30, 37]            |0   |
|   0|in MMR(39)|[1, 5, 13, 29]      |[30, 37, 38]        |0   |
|   1|in MMR(3)|[0]                 |[2]                 |0   |
|   1|in MMR(4)|[0]                 |[2, 3]              |0   |
|   1|in MMR(7)|[0, 5]              |[6]                 |0   |
|   1|in MMR(8)|[0, 5]              |[6, 7]              |0   |
|   1|in MMR(10)|[0, 5]              |[6, 9]              |0   |
|   1|in MMR(11)|[0, 5]              |[6, 9, 10]          |0   |
|   1|in MMR(15)|[0, 5, 13]          |[14]                |0   |
|   1|in MMR(16)|[0, 5, 13]          |[14, 15]            |0   |
|   1|in MMR(18)|[0, 5, 13]          |[14, 17]            |0   |
|   1|in MMR(19)|[0, 5, 13]          |[14, 17, 18]        |0   |
|   1|in MMR(22)|[0, 5, 13]          |[14, 21]            |0   |
|   1|in MMR(23)|[0, 5, 13]          |[14, 21, 22]        |0   |
|   1|in MMR(25)|[0, 5, 13]          |[14, 21, 24]        |0   |
|   1|in MMR(26)|[0, 5, 13]          |[14, 21, 24, 25]    |0   |
|   1|in MMR(31)|[0, 5, 13, 29]      |[30]                |0   |
|   1|in MMR(32)|[0, 5, 13, 29]      |[30, 31]            |0   |
|   1|in MMR(34)|[0, 5, 13, 29]      |[30, 33]            |0   |
|   1|in MMR(35)|[0, 5, 13, 29]      |[30, 33, 34]        |0   |
|   1|in MMR(38)|[0, 5, 13, 29]      |[30, 37]            |0   |
|   1|in MMR(39)|[0, 5, 13, 29]      |[30, 37, 38]        |0   |
|   2|in MMR(3)|[]                  |[2]                 |0   |
|   2|in MMR(4)|[]                  |[2, 3]              |0   |
|   2|in MMR(7)|[5]                 |[6]                 |0   |
|   2|in MMR(8)|[5]                 |[6, 7]              |0   |
|   2|in MMR(10)|[5]                 |[6, 9]              |0   |
|   2|in MMR(11)|[5]                 |[6, 9, 10]          |0   |
|   2|in MMR(15)|[5, 13]             |[14]                |0   |
|   2|in MMR(16)|[5, 13]             |[14, 15]            |0   |
|   2|in MMR(18)|[5, 13]             |[14, 17]            |0   |
|   2|in MMR(19)|[5, 13]             |[14, 17, 18]        |0   |
|   2|in MMR(22)|[5, 13]             |[14, 21]            |0   |
|   2|in MMR(23)|[5, 13]             |[14, 21, 22]        |0   |
|   2|in MMR(25)|[5, 13]             |[14, 21, 24]        |0   |
|   2|in MMR(26)|[5, 13]             |[14, 21, 24, 25]    |0   |
|   2|in MMR(31)|[5, 13, 29]         |[30]                |0   |
|   2|in MMR(32)|[5, 13, 29]         |[30, 31]            |0   |
|   2|in MMR(34)|[5, 13, 29]         |[30, 33]            |0   |
|   2|in MMR(35)|[5, 13, 29]         |[30, 33, 34]        |0   |
|   2|in MMR(38)|[5, 13, 29]         |[30, 37]            |0   |
|   2|in MMR(39)|[5, 13, 29]         |[30, 37, 38]        |0   |
|   3|in MMR(4)|[]                  |[2, 3]              |1   |
|   3|in MMR(7)|[4, 2]              |[6]                 |0   |
|   3|in MMR(8)|[4, 2]              |[6, 7]              |0   |
|   3|in MMR(10)|[4, 2]              |[6, 9]              |0   |
|   3|in MMR(11)|[4, 2]              |[6, 9, 10]          |0   |
|   3|in MMR(15)|[4, 2, 13]          |[14]                |0   |
|   3|in MMR(16)|[4, 2, 13]          |[14, 15]            |0   |
|   3|in MMR(18)|[4, 2, 13]          |[14, 17]            |0   |
|   3|in MMR(19)|[4, 2, 13]          |[14, 17, 18]        |0   |
|   3|in MMR(22)|[4, 2, 13]          |[14, 21]            |0   |
|   3|in MMR(23)|[4, 2, 13]          |[14, 21, 22]        |0   |
|   3|in MMR(25)|[4, 2, 13]          |[14, 21, 24]        |0   |
|   3|in MMR(26)|[4, 2, 13]          |[14, 21, 24, 25]    |0   |
|   3|in MMR(31)|[4, 2, 13, 29]      |[30]                |0   |
|   3|in MMR(32)|[4, 2, 13, 29]      |[30, 31]            |0   |
|   3|in MMR(34)|[4, 2, 13, 29]      |[30, 33]            |0   |
|   3|in MMR(35)|[4, 2, 13, 29]      |[30, 33, 34]        |0   |
|   3|in MMR(38)|[4, 2, 13, 29]      |[30, 37]            |0   |
|   3|in MMR(39)|[4, 2, 13, 29]      |[30, 37, 38]        |0   |
|   4|in MMR(7)|[3, 2]              |[6]                 |0   |
|   4|in MMR(8)|[3, 2]              |[6, 7]              |0   |
|   4|in MMR(10)|[3, 2]              |[6, 9]              |0   |
|   4|in MMR(11)|[3, 2]              |[6, 9, 10]          |0   |
|   4|in MMR(15)|[3, 2, 13]          |[14]                |0   |
|   4|in MMR(16)|[3, 2, 13]          |[14, 15]            |0   |
|   4|in MMR(18)|[3, 2, 13]          |[14, 17]            |0   |
|   4|in MMR(19)|[3, 2, 13]          |[14, 17, 18]        |0   |
|   4|in MMR(22)|[3, 2, 13]          |[14, 21]            |0   |
|   4|in MMR(23)|[3, 2, 13]          |[14, 21, 22]        |0   |
|   4|in MMR(25)|[3, 2, 13]          |[14, 21, 24]        |0   |
|   4|in MMR(26)|[3, 2, 13]          |[14, 21, 24, 25]    |0   |
|   4|in MMR(31)|[3, 2, 13, 29]      |[30]                |0   |
|   4|in MMR(32)|[3, 2, 13, 29]      |[30, 31]            |0   |
|   4|in MMR(34)|[3, 2, 13, 29]      |[30, 33]            |0   |
|   4|in MMR(35)|[3, 2, 13, 29]      |[30, 33, 34]        |0   |
|   4|in MMR(38)|[3, 2, 13, 29]      |[30, 37]            |0   |
|   4|in MMR(39)|[3, 2, 13, 29]      |[30, 37, 38]        |0   |
|   5|in MMR(7)|[2]                 |[6]                 |0   |
|   5|in MMR(8)|[2]                 |[6, 7]              |0   |
|   5|in MMR(10)|[2]                 |[6, 9]              |0   |
|   5|in MMR(11)|[2]                 |[6, 9, 10]          |0   |
|   5|in MMR(15)|[2, 13]             |[14]                |0   |
|   5|in MMR(16)|[2, 13]             |[14, 15]            |0   |
|   5|in MMR(18)|[2, 13]             |[14, 17]            |0   |
|   5|in MMR(19)|[2, 13]             |[14, 17, 18]        |0   |
|   5|in MMR(22)|[2, 13]             |[14, 21]            |0   |
|   5|in MMR(23)|[2, 13]             |[14, 21, 22]        |0   |
|   5|in MMR(25)|[2, 13]             |[14, 21, 24]        |0   |
|   5|in MMR(26)|[2, 13]             |[14, 21, 24, 25]    |0   |
|   5|in MMR(31)|[2, 13, 29]         |[30]                |0   |
|   5|in MMR(32)|[2, 13, 29]         |[30, 31]            |0   |
|   5|in MMR(34)|[2, 13, 29]         |[30, 33]            |0   |
|   5|in MMR(35)|[2, 13, 29]         |[30, 33, 34]        |0   |
|   5|in MMR(38)|[2, 13, 29]         |[30, 37]            |0   |
|   5|in MMR(39)|[2, 13, 29]         |[30, 37, 38]        |0   |
|   6|in MMR(7)|[]                  |[6]                 |0   |
|   6|in MMR(8)|[]                  |[6, 7]              |0   |
|   6|in MMR(10)|[]                  |[6, 9]              |0   |
|   6|in MMR(11)|[]                  |[6, 9, 10]          |0   |
|   6|in MMR(15)|[13]                |[14]                |0   |
|   6|in MMR(16)|[13]                |[14, 15]            |0   |
|   6|in MMR(18)|[13]                |[14, 17]            |0   |
|   6|in MMR(19)|[13]                |[14, 17, 18]        |0   |
|   6|in MMR(22)|[13]                |[14, 21]            |0   |
|   6|in MMR(23)|[13]                |[14, 21, 22]        |0   |
|   6|in MMR(25)|[13]                |[14, 21, 24]        |0   |
|   6|in MMR(26)|[13]                |[14, 21, 24, 25]    |0   |
|   6|in MMR(31)|[13, 29]            |[30]                |0   |
|   6|in MMR(32)|[13, 29]            |[30, 31]            |0   |
|   6|in MMR(34)|[13, 29]            |[30, 33]            |0   |
|   6|in MMR(35)|[13, 29]            |[30, 33, 34]        |0   |
|   6|in MMR(38)|[13, 29]            |[30, 37]            |0   |
|   6|in MMR(39)|[13, 29]            |[30, 37, 38]        |0   |
|   7|in MMR(8)|[]                  |[6, 7]              |1   |
|   7|in MMR(10)|[8]                 |[6, 9]              |1   |
|   7|in MMR(11)|[8]                 |[6, 9, 10]          |1   |
|   7|in MMR(15)|[8, 12, 6]          |[14]                |0   |
|   7|in MMR(16)|[8, 12, 6]          |[14, 15]            |0   |
|   7|in MMR(18)|[8, 12, 6]          |[14, 17]            |0   |
|   7|in MMR(19)|[8, 12, 6]          |[14, 17, 18]        |0   |
|   7|in MMR(22)|[8, 12, 6]          |[14, 21]            |0   |
|   7|in MMR(23)|[8, 12, 6]          |[14, 21, 22]        |0   |
|   7|in MMR(25)|[8, 12, 6]          |[14, 21, 24]        |0   |
|   7|in MMR(26)|[8, 12, 6]          |[14, 21, 24, 25]    |0   |
|   7|in MMR(31)|[8, 12, 6, 29]      |[30]                |0   |
|   7|in MMR(32)|[8, 12, 6, 29]      |[30, 31]            |0   |
|   7|in MMR(34)|[8, 12, 6, 29]      |[30, 33]            |0   |
|   7|in MMR(35)|[8, 12, 6, 29]      |[30, 33, 34]        |0   |
|   7|in MMR(38)|[8, 12, 6, 29]      |[30, 37]            |0   |
|   7|in MMR(39)|[8, 12, 6, 29]      |[30, 37, 38]        |0   |
|   8|in MMR(10)|[7]                 |[6, 9]              |1   |
|   8|in MMR(11)|[7]                 |[6, 9, 10]          |1   |
|   8|in MMR(15)|[7, 12, 6]          |[14]                |0   |
|   8|in MMR(16)|[7, 12, 6]          |[14, 15]            |0   |
|   8|in MMR(18)|[7, 12, 6]          |[14, 17]            |0   |
|   8|in MMR(19)|[7, 12, 6]          |[14, 17, 18]        |0   |
|   8|in MMR(22)|[7, 12, 6]          |[14, 21]            |0   |
|   8|in MMR(23)|[7, 12, 6]          |[14, 21, 22]        |0   |
|   8|in MMR(25)|[7, 12, 6]          |[14, 21, 24]        |0   |
|   8|in MMR(26)|[7, 12, 6]          |[14, 21, 24, 25]    |0   |
|   8|in MMR(31)|[7, 12, 6, 29]      |[30]                |0   |
|   8|in MMR(32)|[7, 12, 6, 29]      |[30, 31]            |0   |
|   8|in MMR(34)|[7, 12, 6, 29]      |[30, 33]            |0   |
|   8|in MMR(35)|[7, 12, 6, 29]      |[30, 33, 34]        |0   |
|   8|in MMR(38)|[7, 12, 6, 29]      |[30, 37]            |0   |
|   8|in MMR(39)|[7, 12, 6, 29]      |[30, 37, 38]        |0   |
|   9|in MMR(10)|[]                  |[6, 9]              |1   |
|   9|in MMR(11)|[]                  |[6, 9, 10]          |1   |
|   9|in MMR(15)|[12, 6]             |[14]                |0   |
|   9|in MMR(16)|[12, 6]             |[14, 15]            |0   |
|   9|in MMR(18)|[12, 6]             |[14, 17]            |0   |
|   9|in MMR(19)|[12, 6]             |[14, 17, 18]        |0   |
|   9|in MMR(22)|[12, 6]             |[14, 21]            |0   |
|   9|in MMR(23)|[12, 6]             |[14, 21, 22]        |0   |
|   9|in MMR(25)|[12, 6]             |[14, 21, 24]        |0   |
|   9|in MMR(26)|[12, 6]             |[14, 21, 24, 25]    |0   |
|   9|in MMR(31)|[12, 6, 29]         |[30]                |0   |
|   9|in MMR(32)|[12, 6, 29]         |[30, 31]            |0   |
|   9|in MMR(34)|[12, 6, 29]         |[30, 33]            |0   |
|   9|in MMR(35)|[12, 6, 29]         |[30, 33, 34]        |0   |
|   9|in MMR(38)|[12, 6, 29]         |[30, 37]            |0   |
|   9|in MMR(39)|[12, 6, 29]         |[30, 37, 38]        |0   |
|  10|in MMR(11)|[]                  |[6, 9, 10]          |2   |
|  10|in MMR(15)|[11, 9, 6]          |[14]                |0   |
|  10|in MMR(16)|[11, 9, 6]          |[14, 15]            |0   |
|  10|in MMR(18)|[11, 9, 6]          |[14, 17]            |0   |
|  10|in MMR(19)|[11, 9, 6]          |[14, 17, 18]        |0   |
|  10|in MMR(22)|[11, 9, 6]          |[14, 21]            |0   |
|  10|in MMR(23)|[11, 9, 6]          |[14, 21, 22]        |0   |
|  10|in MMR(25)|[11, 9, 6]          |[14, 21, 24]        |0   |
|  10|in MMR(26)|[11, 9, 6]          |[14, 21, 24, 25]    |0   |
|  10|in MMR(31)|[11, 9, 6, 29]      |[30]                |0   |
|  10|in MMR(32)|[11, 9, 6, 29]      |[30, 31]            |0   |
|  10|in MMR(34)|[11, 9, 6, 29]      |[30, 33]            |0   |
|  10|in MMR(35)|[11, 9, 6, 29]      |[30, 33, 34]        |0   |
|  10|in MMR(38)|[11, 9, 6, 29]      |[30, 37]            |0   |
|  10|in MMR(39)|[11, 9, 6, 29]      |[30, 37, 38]        |0   |
|  11|in MMR(15)|[10, 9, 6]          |[14]                |0   |
|  11|in MMR(16)|[10, 9, 6]          |[14, 15]            |0   |
|  11|in MMR(18)|[10, 9, 6]          |[14, 17]            |0   |
|  11|in MMR(19)|[10, 9, 6]          |[14, 17, 18]        |0   |
|  11|in MMR(22)|[10, 9, 6]          |[14, 21]            |0   |
|  11|in MMR(23)|[10, 9, 6]          |[14, 21, 22]        |0   |
|  11|in MMR(25)|[10, 9, 6]          |[14, 21, 24]        |0   |
|  11|in MMR(26)|[10, 9, 6]          |[14, 21, 24, 25]    |0   |
|  11|in MMR(31)|[10, 9, 6, 29]      |[30]                |0   |
|  11|in MMR(32)|[10, 9, 6, 29]      |[30, 31]            |0   |
|  11|in MMR(34)|[10, 9, 6, 29]      |[30, 33]            |0   |
|  11|in MMR(35)|[10, 9, 6, 29]      |[30, 33, 34]        |0   |
|  11|in MMR(38)|[10, 9, 6, 29]      |[30, 37]            |0   |
|  11|in MMR(39)|[10, 9, 6, 29]      |[30, 37, 38]        |0   |
|  12|in MMR(15)|[9, 6]              |[14]                |0   |
|  12|in MMR(16)|[9, 6]              |[14, 15]            |0   |
|  12|in MMR(18)|[9, 6]              |[14, 17]            |0   |
|  12|in MMR(19)|[9, 6]              |[14, 17, 18]        |0   |
|  12|in MMR(22)|[9, 6]              |[14, 21]            |0   |
|  12|in MMR(23)|[9, 6]              |[14, 21, 22]        |0   |
|  12|in MMR(25)|[9, 6]              |[14, 21, 24]        |0   |
|  12|in MMR(26)|[9, 6]              |[14, 21, 24, 25]    |0   |
|  12|in MMR(31)|[9, 6, 29]          |[30]                |0   |
|  12|in MMR(32)|[9, 6, 29]          |[30, 31]            |0   |
|  12|in MMR(34)|[9, 6, 29]          |[30, 33]            |0   |
|  12|in MMR(35)|[9, 6, 29]          |[30, 33, 34]        |0   |
|  12|in MMR(38)|[9, 6, 29]          |[30, 37]            |0   |
|  12|in MMR(39)|[9, 6, 29]          |[30, 37, 38]        |0   |
|  13|in MMR(15)|[6]                 |[14]                |0   |
|  13|in MMR(16)|[6]                 |[14, 15]            |0   |
|  13|in MMR(18)|[6]                 |[14, 17]            |0   |
|  13|in MMR(19)|[6]                 |[14, 17, 18]        |0   |
|  13|in MMR(22)|[6]                 |[14, 21]            |0   |
|  13|in MMR(23)|[6]                 |[14, 21, 22]        |0   |
|  13|in MMR(25)|[6]                 |[14, 21, 24]        |0   |
|  13|in MMR(26)|[6]                 |[14, 21, 24, 25]    |0   |
|  13|in MMR(31)|[6, 29]             |[30]                |0   |
|  13|in MMR(32)|[6, 29]             |[30, 31]            |0   |
|  13|in MMR(34)|[6, 29]             |[30, 33]            |0   |
|  13|in MMR(35)|[6, 29]             |[30, 33, 34]        |0   |
|  13|in MMR(38)|[6, 29]             |[30, 37]            |0   |
|  13|in MMR(39)|[6, 29]             |[30, 37, 38]        |0   |
|  14|in MMR(15)|[]                  |[14]                |0   |
|  14|in MMR(16)|[]                  |[14, 15]            |0   |
|  14|in MMR(18)|[]                  |[14, 17]            |0   |
|  14|in MMR(19)|[]                  |[14, 17, 18]        |0   |
|  14|in MMR(22)|[]                  |[14, 21]            |0   |
|  14|in MMR(23)|[]                  |[14, 21, 22]        |0   |
|  14|in MMR(25)|[]                  |[14, 21, 24]        |0   |
|  14|in MMR(26)|[]                  |[14, 21, 24, 25]    |0   |
|  14|in MMR(31)|[29]                |[30]                |0   |
|  14|in MMR(32)|[29]                |[30, 31]            |0   |
|  14|in MMR(34)|[29]                |[30, 33]            |0   |
|  14|in MMR(35)|[29]                |[30, 33, 34]        |0   |
|  14|in MMR(38)|[29]                |[30, 37]            |0   |
|  14|in MMR(39)|[29]                |[30, 37, 38]        |0   |
|  15|in MMR(16)|[]                  |[14, 15]            |1   |
|  15|in MMR(18)|[16]                |[14, 17]            |1   |
|  15|in MMR(19)|[16]                |[14, 17, 18]        |1   |
|  15|in MMR(22)|[16, 20]            |[14, 21]            |1   |
|  15|in MMR(23)|[16, 20]            |[14, 21, 22]        |1   |
|  15|in MMR(25)|[16, 20]            |[14, 21, 24]        |1   |
|  15|in MMR(26)|[16, 20]            |[14, 21, 24, 25]    |1   |
|  15|in MMR(31)|[16, 20, 28, 14]    |[30]                |0   |
|  15|in MMR(32)|[16, 20, 28, 14]    |[30, 31]            |0   |
|  15|in MMR(34)|[16, 20, 28, 14]    |[30, 33]            |0   |
|  15|in MMR(35)|[16, 20, 28, 14]    |[30, 33, 34]        |0   |
|  15|in MMR(38)|[16, 20, 28, 14]    |[30, 37]            |0   |
|  15|in MMR(39)|[16, 20, 28, 14]    |[30, 37, 38]        |0   |
|  16|in MMR(18)|[15]                |[14, 17]            |1   |
|  16|in MMR(19)|[15]                |[14, 17, 18]        |1   |
|  16|in MMR(22)|[15, 20]            |[14, 21]            |1   |
|  16|in MMR(23)|[15, 20]            |[14, 21, 22]        |1   |
|  16|in MMR(25)|[15, 20]            |[14, 21, 24]        |1   |
|  16|in MMR(26)|[15, 20]            |[14, 21, 24, 25]    |1   |
|  16|in MMR(31)|[15, 20, 28, 14]    |[30]                |0   |
|  16|in MMR(32)|[15, 20, 28, 14]    |[30, 31]            |0   |
|  16|in MMR(34)|[15, 20, 28, 14]    |[30, 33]            |0   |
|  16|in MMR(35)|[15, 20, 28, 14]    |[30, 33, 34]        |0   |
|  16|in MMR(38)|[15, 20, 28, 14]    |[30, 37]            |0   |
|  16|in MMR(39)|[15, 20, 28, 14]    |[30, 37, 38]        |0   |
|  17|in MMR(18)|[]                  |[14, 17]            |1   |
|  17|in MMR(19)|[]                  |[14, 17, 18]        |1   |
|  17|in MMR(22)|[20]                |[14, 21]            |1   |
|  17|in MMR(23)|[20]                |[14, 21, 22]        |1   |
|  17|in MMR(25)|[20]                |[14, 21, 24]        |1   |
|  17|in MMR(26)|[20]                |[14, 21, 24, 25]    |1   |
|  17|in MMR(31)|[20, 28, 14]        |[30]                |0   |
|  17|in MMR(32)|[20, 28, 14]        |[30, 31]            |0   |
|  17|in MMR(34)|[20, 28, 14]        |[30, 33]            |0   |
|  17|in MMR(35)|[20, 28, 14]        |[30, 33, 34]        |0   |
|  17|in MMR(38)|[20, 28, 14]        |[30, 37]            |0   |
|  17|in MMR(39)|[20, 28, 14]        |[30, 37, 38]        |0   |
|  18|in MMR(19)|[]                  |[14, 17, 18]        |2   |
|  18|in MMR(22)|[19, 17]            |[14, 21]            |1   |
|  18|in MMR(23)|[19, 17]            |[14, 21, 22]        |1   |
|  18|in MMR(25)|[19, 17]            |[14, 21, 24]        |1   |
|  18|in MMR(26)|[19, 17]            |[14, 21, 24, 25]    |1   |
|  18|in MMR(31)|[19, 17, 28, 14]    |[30]                |0   |
|  18|in MMR(32)|[19, 17, 28, 14]    |[30, 31]            |0   |
|  18|in MMR(34)|[19, 17, 28, 14]    |[30, 33]            |0   |
|  18|in MMR(35)|[19, 17, 28, 14]    |[30, 33, 34]        |0   |
|  18|in MMR(38)|[19, 17, 28, 14]    |[30, 37]            |0   |
|  18|in MMR(39)|[19, 17, 28, 14]    |[30, 37, 38]        |0   |
|  19|in MMR(22)|[18, 17]            |[14, 21]            |1   |
|  19|in MMR(23)|[18, 17]            |[14, 21, 22]        |1   |
|  19|in MMR(25)|[18, 17]            |[14, 21, 24]        |1   |
|  19|in MMR(26)|[18, 17]            |[14, 21, 24, 25]    |1   |
|  19|in MMR(31)|[18, 17, 28, 14]    |[30]                |0   |
|  19|in MMR(32)|[18, 17, 28, 14]    |[30, 31]            |0   |
|  19|in MMR(34)|[18, 17, 28, 14]    |[30, 33]            |0   |
|  19|in MMR(35)|[18, 17, 28, 14]    |[30, 33, 34]        |0   |
|  19|in MMR(38)|[18, 17, 28, 14]    |[30, 37]            |0   |
|  19|in MMR(39)|[18, 17, 28, 14]    |[30, 37, 38]        |0   |
|  20|in MMR(22)|[17]                |[14, 21]            |1   |
|  20|in MMR(23)|[17]                |[14, 21, 22]        |1   |
|  20|in MMR(25)|[17]                |[14, 21, 24]        |1   |
|  20|in MMR(26)|[17]                |[14, 21, 24, 25]    |1   |
|  20|in MMR(31)|[17, 28, 14]        |[30]                |0   |
|  20|in MMR(32)|[17, 28, 14]        |[30, 31]            |0   |
|  20|in MMR(34)|[17, 28, 14]        |[30, 33]            |0   |
|  20|in MMR(35)|[17, 28, 14]        |[30, 33, 34]        |0   |
|  20|in MMR(38)|[17, 28, 14]        |[30, 37]            |0   |
|  20|in MMR(39)|[17, 28, 14]        |[30, 37, 38]        |0   |
|  21|in MMR(22)|[]                  |[14, 21]            |1   |
|  21|in MMR(23)|[]                  |[14, 21, 22]        |1   |
|  21|in MMR(25)|[]                  |[14, 21, 24]        |1   |
|  21|in MMR(26)|[]                  |[14, 21, 24, 25]    |1   |
|  21|in MMR(31)|[28, 14]            |[30]                |0   |
|  21|in MMR(32)|[28, 14]            |[30, 31]            |0   |
|  21|in MMR(34)|[28, 14]            |[30, 33]            |0   |
|  21|in MMR(35)|[28, 14]            |[30, 33, 34]        |0   |
|  21|in MMR(38)|[28, 14]            |[30, 37]            |0   |
|  21|in MMR(39)|[28, 14]            |[30, 37, 38]        |0   |
|  22|in MMR(23)|[]                  |[14, 21, 22]        |2   |
|  22|in MMR(25)|[23]                |[14, 21, 24]        |2   |
|  22|in MMR(26)|[23]                |[14, 21, 24, 25]    |2   |
|  22|in MMR(31)|[23, 27, 21, 14]    |[30]                |0   |
|  22|in MMR(32)|[23, 27, 21, 14]    |[30, 31]            |0   |
|  22|in MMR(34)|[23, 27, 21, 14]    |[30, 33]            |0   |
|  22|in MMR(35)|[23, 27, 21, 14]    |[30, 33, 34]        |0   |
|  22|in MMR(38)|[23, 27, 21, 14]    |[30, 37]            |0   |
|  22|in MMR(39)|[23, 27, 21, 14]    |[30, 37, 38]        |0   |
|  23|in MMR(25)|[22]                |[14, 21, 24]        |2   |
|  23|in MMR(26)|[22]                |[14, 21, 24, 25]    |2   |
|  23|in MMR(31)|[22, 27, 21, 14]    |[30]                |0   |
|  23|in MMR(32)|[22, 27, 21, 14]    |[30, 31]            |0   |
|  23|in MMR(34)|[22, 27, 21, 14]    |[30, 33]            |0   |
|  23|in MMR(35)|[22, 27, 21, 14]    |[30, 33, 34]        |0   |
|  23|in MMR(38)|[22, 27, 21, 14]    |[30, 37]            |0   |
|  23|in MMR(39)|[22, 27, 21, 14]    |[30, 37, 38]        |0   |
|  24|in MMR(25)|[]                  |[14, 21, 24]        |2   |
|  24|in MMR(26)|[]                  |[14, 21, 24, 25]    |2   |
|  24|in MMR(31)|[27, 21, 14]        |[30]                |0   |
|  24|in MMR(32)|[27, 21, 14]        |[30, 31]            |0   |
|  24|in MMR(34)|[27, 21, 14]        |[30, 33]            |0   |
|  24|in MMR(35)|[27, 21, 14]        |[30, 33, 34]        |0   |
|  24|in MMR(38)|[27, 21, 14]        |[30, 37]            |0   |
|  24|in MMR(39)|[27, 21, 14]        |[30, 37, 38]        |0   |
|  25|in MMR(26)|[]                  |[14, 21, 24, 25]    |3   |
|  25|in MMR(31)|[26, 24, 21, 14]    |[30]                |0   |
|  25|in MMR(32)|[26, 24, 21, 14]    |[30, 31]            |0   |
|  25|in MMR(34)|[26, 24, 21, 14]    |[30, 33]            |0   |
|  25|in MMR(35)|[26, 24, 21, 14]    |[30, 33, 34]        |0   |
|  25|in MMR(38)|[26, 24, 21, 14]    |[30, 37]            |0   |
|  25|in MMR(39)|[26, 24, 21, 14]    |[30, 37, 38]        |0   |
|  26|in MMR(31)|[25, 24, 21, 14]    |[30]                |0   |
|  26|in MMR(32)|[25, 24, 21, 14]    |[30, 31]            |0   |
|  26|in MMR(34)|[25, 24, 21, 14]    |[30, 33]            |0   |
|  26|in MMR(35)|[25, 24, 21, 14]    |[30, 33, 34]        |0   |
|  26|in MMR(38)|[25, 24, 21, 14]    |[30, 37]            |0   |
|  26|in MMR(39)|[25, 24, 21, 14]    |[30, 37, 38]        |0   |
|  27|in MMR(31)|[24, 21, 14]        |[30]                |0   |
|  27|in MMR(32)|[24, 21, 14]        |[30, 31]            |0   |
|  27|in MMR(34)|[24, 21, 14]        |[30, 33]            |0   |
|  27|in MMR(35)|[24, 21, 14]        |[30, 33, 34]        |0   |
|  27|in MMR(38)|[24, 21, 14]        |[30, 37]            |0   |
|  27|in MMR(39)|[24, 21, 14]        |[30, 37, 38]        |0   |
|  28|in MMR(31)|[21, 14]            |[30]                |0   |
|  28|in MMR(32)|[21, 14]            |[30, 31]            |0   |
|  28|in MMR(34)|[21, 14]            |[30, 33]            |0   |
|  28|in MMR(35)|[21, 14]            |[30, 33, 34]        |0   |
|  28|in MMR(38)|[21, 14]            |[30, 37]            |0   |
|  28|in MMR(39)|[21, 14]            |[30, 37, 38]        |0   |
|  29|in MMR(31)|[14]                |[30]                |0   |
|  29|in MMR(32)|[14]                |[30, 31]            |0   |
|  29|in MMR(34)|[14]                |[30, 33]            |0   |
|  29|in MMR(35)|[14]                |[30, 33, 34]        |0   |
|  29|in MMR(38)|[14]                |[30, 37]            |0   |
|  29|in MMR(39)|[14]                |[30, 37, 38]        |0   |
|  30|in MMR(31)|[]                  |[30]                |0   |
|  30|in MMR(32)|[]                  |[30, 31]            |0   |
|  30|in MMR(34)|[]                  |[30, 33]            |0   |
|  30|in MMR(35)|[]                  |[30, 33, 34]        |0   |
|  30|in MMR(38)|[]                  |[30, 37]            |0   |
|  30|in MMR(39)|[]                  |[30, 37, 38]        |0   |
|  31|in MMR(32)|[]                  |[30, 31]            |1   |
|  31|in MMR(34)|[32]                |[30, 33]            |1   |
|  31|in MMR(35)|[32]                |[30, 33, 34]        |1   |
|  31|in MMR(38)|[32, 36]            |[30, 37]            |1   |
|  31|in MMR(39)|[32, 36]            |[30, 37, 38]        |1   |
|  32|in MMR(34)|[31]                |[30, 33]            |1   |
|  32|in MMR(35)|[31]                |[30, 33, 34]        |1   |
|  32|in MMR(38)|[31, 36]            |[30, 37]            |1   |
|  32|in MMR(39)|[31, 36]            |[30, 37, 38]        |1   |
|  33|in MMR(34)|[]                  |[30, 33]            |1   |
|  33|in MMR(35)|[]                  |[30, 33, 34]        |1   |
|  33|in MMR(38)|[36]                |[30, 37]            |1   |
|  33|in MMR(39)|[36]                |[30, 37, 38]        |1   |
|  34|in MMR(35)|[]                  |[30, 33, 34]        |2   |
|  34|in MMR(38)|[35, 33]            |[30, 37]            |1   |
|  34|in MMR(39)|[35, 33]            |[30, 37, 38]        |1   |
|  35|in MMR(38)|[34, 33]            |[30, 37]            |1   |
|  35|in MMR(39)|[34, 33]            |[30, 37, 38]        |1   |
|  36|in MMR(38)|[33]                |[30, 37]            |1   |
|  36|in MMR(39)|[33]                |[30, 37, 38]        |1   |
|  37|in MMR(38)|[]                  |[30, 37]            |1   |
|  37|in MMR(39)|[]                  |[30, 37, 38]        |1   |
|  38|in MMR(39)|[]                  |[30, 37, 38]        |2   |

## Included roots

|0 in mmr's 1 - 39|
|--|
|ad104051c516812ea5874ca3ff06d0258303623d04307c41ec80a7a18b332ef8|
|ad104051c516812ea5874ca3ff06d0258303623d04307c41ec80a7a18b332ef8|
|827f3213c1de0d4c6277caccc1eeca325e45dfe2c65adce1943774218db61f88|
|827f3213c1de0d4c6277caccc1eeca325e45dfe2c65adce1943774218db61f88|
|827f3213c1de0d4c6277caccc1eeca325e45dfe2c65adce1943774218db61f88|
|827f3213c1de0d4c6277caccc1eeca325e45dfe2c65adce1943774218db61f88|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|

|1 in mmr's 2 - 39|
|--|
|ad104051c516812ea5874ca3ff06d0258303623d04307c41ec80a7a18b332ef8|
|ad104051c516812ea5874ca3ff06d0258303623d04307c41ec80a7a18b332ef8|
|827f3213c1de0d4c6277caccc1eeca325e45dfe2c65adce1943774218db61f88|
|827f3213c1de0d4c6277caccc1eeca325e45dfe2c65adce1943774218db61f88|
|827f3213c1de0d4c6277caccc1eeca325e45dfe2c65adce1943774218db61f88|
|827f3213c1de0d4c6277caccc1eeca325e45dfe2c65adce1943774218db61f88|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|

|2 in mmr's 3 - 39|
|--|
|ad104051c516812ea5874ca3ff06d0258303623d04307c41ec80a7a18b332ef8|
|827f3213c1de0d4c6277caccc1eeca325e45dfe2c65adce1943774218db61f88|
|827f3213c1de0d4c6277caccc1eeca325e45dfe2c65adce1943774218db61f88|
|827f3213c1de0d4c6277caccc1eeca325e45dfe2c65adce1943774218db61f88|
|827f3213c1de0d4c6277caccc1eeca325e45dfe2c65adce1943774218db61f88|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|

|3 in mmr's 4 - 39|
|--|
|827f3213c1de0d4c6277caccc1eeca325e45dfe2c65adce1943774218db61f88|
|827f3213c1de0d4c6277caccc1eeca325e45dfe2c65adce1943774218db61f88|
|827f3213c1de0d4c6277caccc1eeca325e45dfe2c65adce1943774218db61f88|
|827f3213c1de0d4c6277caccc1eeca325e45dfe2c65adce1943774218db61f88|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|

|4 in mmr's 5 - 39|
|--|
|827f3213c1de0d4c6277caccc1eeca325e45dfe2c65adce1943774218db61f88|
|827f3213c1de0d4c6277caccc1eeca325e45dfe2c65adce1943774218db61f88|
|827f3213c1de0d4c6277caccc1eeca325e45dfe2c65adce1943774218db61f88|
|827f3213c1de0d4c6277caccc1eeca325e45dfe2c65adce1943774218db61f88|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|

|5 in mmr's 6 - 39|
|--|
|827f3213c1de0d4c6277caccc1eeca325e45dfe2c65adce1943774218db61f88|
|827f3213c1de0d4c6277caccc1eeca325e45dfe2c65adce1943774218db61f88|
|827f3213c1de0d4c6277caccc1eeca325e45dfe2c65adce1943774218db61f88|
|827f3213c1de0d4c6277caccc1eeca325e45dfe2c65adce1943774218db61f88|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|

|6 in mmr's 7 - 39|
|--|
|827f3213c1de0d4c6277caccc1eeca325e45dfe2c65adce1943774218db61f88|
|827f3213c1de0d4c6277caccc1eeca325e45dfe2c65adce1943774218db61f88|
|827f3213c1de0d4c6277caccc1eeca325e45dfe2c65adce1943774218db61f88|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|

|7 in mmr's 8 - 39|
|--|
|b8faf5f748f149b04018491a51334499fd8b6060c42a835f361fa9665562d12d|
|b8faf5f748f149b04018491a51334499fd8b6060c42a835f361fa9665562d12d|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|

|8 in mmr's 9 - 39|
|--|
|b8faf5f748f149b04018491a51334499fd8b6060c42a835f361fa9665562d12d|
|b8faf5f748f149b04018491a51334499fd8b6060c42a835f361fa9665562d12d|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|

|9 in mmr's 10 - 39|
|--|
|b8faf5f748f149b04018491a51334499fd8b6060c42a835f361fa9665562d12d|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|

|10 in mmr's 11 - 39|
|--|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|

|11 in mmr's 12 - 39|
|--|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|

|12 in mmr's 13 - 39|
|--|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|

|13 in mmr's 14 - 39|
|--|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|

|14 in mmr's 15 - 39|
|--|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|78b2b4162eb2c58b229288bbcb5b7d97c7a1154eed3161905fb0f180eba6f112|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|

|15 in mmr's 16 - 39|
|--|
|f4a0db79de0fee128fbe95ecf3509646203909dc447ae911aa29416bf6fcba21|
|f4a0db79de0fee128fbe95ecf3509646203909dc447ae911aa29416bf6fcba21|
|61b3ff808934301578c9ed7402e3dd7dfe98b630acdf26d1fd2698a3c4a22710|
|61b3ff808934301578c9ed7402e3dd7dfe98b630acdf26d1fd2698a3c4a22710|
|61b3ff808934301578c9ed7402e3dd7dfe98b630acdf26d1fd2698a3c4a22710|
|61b3ff808934301578c9ed7402e3dd7dfe98b630acdf26d1fd2698a3c4a22710|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|

|16 in mmr's 17 - 39|
|--|
|f4a0db79de0fee128fbe95ecf3509646203909dc447ae911aa29416bf6fcba21|
|f4a0db79de0fee128fbe95ecf3509646203909dc447ae911aa29416bf6fcba21|
|61b3ff808934301578c9ed7402e3dd7dfe98b630acdf26d1fd2698a3c4a22710|
|61b3ff808934301578c9ed7402e3dd7dfe98b630acdf26d1fd2698a3c4a22710|
|61b3ff808934301578c9ed7402e3dd7dfe98b630acdf26d1fd2698a3c4a22710|
|61b3ff808934301578c9ed7402e3dd7dfe98b630acdf26d1fd2698a3c4a22710|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|

|17 in mmr's 18 - 39|
|--|
|f4a0db79de0fee128fbe95ecf3509646203909dc447ae911aa29416bf6fcba21|
|61b3ff808934301578c9ed7402e3dd7dfe98b630acdf26d1fd2698a3c4a22710|
|61b3ff808934301578c9ed7402e3dd7dfe98b630acdf26d1fd2698a3c4a22710|
|61b3ff808934301578c9ed7402e3dd7dfe98b630acdf26d1fd2698a3c4a22710|
|61b3ff808934301578c9ed7402e3dd7dfe98b630acdf26d1fd2698a3c4a22710|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|

|18 in mmr's 19 - 39|
|--|
|61b3ff808934301578c9ed7402e3dd7dfe98b630acdf26d1fd2698a3c4a22710|
|61b3ff808934301578c9ed7402e3dd7dfe98b630acdf26d1fd2698a3c4a22710|
|61b3ff808934301578c9ed7402e3dd7dfe98b630acdf26d1fd2698a3c4a22710|
|61b3ff808934301578c9ed7402e3dd7dfe98b630acdf26d1fd2698a3c4a22710|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|

|19 in mmr's 20 - 39|
|--|
|61b3ff808934301578c9ed7402e3dd7dfe98b630acdf26d1fd2698a3c4a22710|
|61b3ff808934301578c9ed7402e3dd7dfe98b630acdf26d1fd2698a3c4a22710|
|61b3ff808934301578c9ed7402e3dd7dfe98b630acdf26d1fd2698a3c4a22710|
|61b3ff808934301578c9ed7402e3dd7dfe98b630acdf26d1fd2698a3c4a22710|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|

|20 in mmr's 21 - 39|
|--|
|61b3ff808934301578c9ed7402e3dd7dfe98b630acdf26d1fd2698a3c4a22710|
|61b3ff808934301578c9ed7402e3dd7dfe98b630acdf26d1fd2698a3c4a22710|
|61b3ff808934301578c9ed7402e3dd7dfe98b630acdf26d1fd2698a3c4a22710|
|61b3ff808934301578c9ed7402e3dd7dfe98b630acdf26d1fd2698a3c4a22710|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|

|21 in mmr's 22 - 39|
|--|
|61b3ff808934301578c9ed7402e3dd7dfe98b630acdf26d1fd2698a3c4a22710|
|61b3ff808934301578c9ed7402e3dd7dfe98b630acdf26d1fd2698a3c4a22710|
|61b3ff808934301578c9ed7402e3dd7dfe98b630acdf26d1fd2698a3c4a22710|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|

|22 in mmr's 23 - 39|
|--|
|dd7efba5f1824103f1fa820a5c9e6cd90a82cf123d88bd035c7e5da0aba8a9ae|
|dd7efba5f1824103f1fa820a5c9e6cd90a82cf123d88bd035c7e5da0aba8a9ae|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|

|23 in mmr's 24 - 39|
|--|
|dd7efba5f1824103f1fa820a5c9e6cd90a82cf123d88bd035c7e5da0aba8a9ae|
|dd7efba5f1824103f1fa820a5c9e6cd90a82cf123d88bd035c7e5da0aba8a9ae|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|

|24 in mmr's 25 - 39|
|--|
|dd7efba5f1824103f1fa820a5c9e6cd90a82cf123d88bd035c7e5da0aba8a9ae|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|

|25 in mmr's 26 - 39|
|--|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|

|26 in mmr's 27 - 39|
|--|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|

|27 in mmr's 28 - 39|
|--|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|

|28 in mmr's 29 - 39|
|--|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|

|29 in mmr's 30 - 39|
|--|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|

|30 in mmr's 31 - 39|
|--|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|
|d4fb5649422ff2eaf7b1c0b851585a8cfd14fb08ce11addb30075a96309582a7|

|31 in mmr's 32 - 39|
|--|
|0c9f36783b5929d43c97fe4b170d12137e6950ef1b3a8bd254b15bbacbfdee7f|
|0c9f36783b5929d43c97fe4b170d12137e6950ef1b3a8bd254b15bbacbfdee7f|
|6a169105dcc487dbbae5747a0fd9b1d33a40320cf91cf9a323579139e7ff72aa|
|6a169105dcc487dbbae5747a0fd9b1d33a40320cf91cf9a323579139e7ff72aa|

|32 in mmr's 33 - 39|
|--|
|0c9f36783b5929d43c97fe4b170d12137e6950ef1b3a8bd254b15bbacbfdee7f|
|0c9f36783b5929d43c97fe4b170d12137e6950ef1b3a8bd254b15bbacbfdee7f|
|6a169105dcc487dbbae5747a0fd9b1d33a40320cf91cf9a323579139e7ff72aa|
|6a169105dcc487dbbae5747a0fd9b1d33a40320cf91cf9a323579139e7ff72aa|

|33 in mmr's 34 - 39|
|--|
|0c9f36783b5929d43c97fe4b170d12137e6950ef1b3a8bd254b15bbacbfdee7f|
|6a169105dcc487dbbae5747a0fd9b1d33a40320cf91cf9a323579139e7ff72aa|
|6a169105dcc487dbbae5747a0fd9b1d33a40320cf91cf9a323579139e7ff72aa|

|34 in mmr's 35 - 39|
|--|
|6a169105dcc487dbbae5747a0fd9b1d33a40320cf91cf9a323579139e7ff72aa|
|6a169105dcc487dbbae5747a0fd9b1d33a40320cf91cf9a323579139e7ff72aa|

|35 in mmr's 36 - 39|
|--|
|6a169105dcc487dbbae5747a0fd9b1d33a40320cf91cf9a323579139e7ff72aa|
|6a169105dcc487dbbae5747a0fd9b1d33a40320cf91cf9a323579139e7ff72aa|

|36 in mmr's 37 - 39|
|--|
|6a169105dcc487dbbae5747a0fd9b1d33a40320cf91cf9a323579139e7ff72aa|
|6a169105dcc487dbbae5747a0fd9b1d33a40320cf91cf9a323579139e7ff72aa|

|37 in mmr's 38 - 39|
|--|
|6a169105dcc487dbbae5747a0fd9b1d33a40320cf91cf9a323579139e7ff72aa|

# Acknowledgments
{:numbered="false"}

TODO acknowledge.
