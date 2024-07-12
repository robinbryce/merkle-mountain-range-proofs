# Informantive examples and supplimentary definitions

## PeaksBitmap

The leafcount is often available, in which case its binary form is exactly the
result of this transformation on mmrSize

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

### Example PeaksBitmap(10)

```
          14
       /       \
     6          13
   /   \       /   \
  2     5     9     12     17
 / \   /  \  / \   /  \   /  \
0   1 3   4 7   8 10  11 15  16 18
0   1 2   3 4   5
```

```
    pos = mmrSize = 10 = b01010
    peakSize = (1 << 4) - 1
    => 16 - 1 = 15
    peakMap = 0

    (1) peakSize=15 > 0 => true
    peakMap = 0 <= 0
    (2) pos >= peakSize
        => 10 >= 15 => false
    peakSize >>=1
    => 15 >> 1 = 7

    (1) peakSize=7 > 0 => true
    peakMap = 0 <= 0
    (2) pos >= peakSize
        => 10 >= 7 => true
        pos -= peakSize
        => pos = 10 - 7 = 3
        peakMap |= 1
        peakSize >>= 1
        => 7 >> 1 = 3

    (1) peakSize=3 > 0 => true
    peakMap = 1 << 1 = b10
    (2) pos >= peakSize
        => 3 >= 3 => true
        pos -= peakSize
        => pos = 3 - 3 = 0
        peakMap |= 1 = b11
        peakSize >>=1
        => 3 >> 1 = 1

    (1) peakSize=1 > 0 => true
    peakMap = b11 << 1 = b110
    (2) pos >= peakSize
        => 0 >= 1 => false
        peakSize >>= 1
        => 1 >> 1 = 0

    return b110 = 6

```
# APPENDIX (x) accumulator validity

MMR(3) i=1, path=[0], A=[2]

MMR(4) i=3, path=[]
MMR(7) i=3, path

MMR(39), i=3
```
03 00 2: MMR(4 3) [] [2, 3][1]=3
06 03 3: MMR(7 3) [4, 2] [6][0]=6
06 04 3: MMR(8 3) [4, 2] [6, 7][0]=6
06 06 3: MMR(10 3) [4, 2] [6, 9][0]=6
06 07 3: MMR(11 3) [4, 2] [6, 9, 10][0]=6
14 11 4: MMR(15 3) [4, 2, 13] [14][0]=14
14 12 4: MMR(16 3) [4, 2, 13] [14, 15][0]=14
14 14 4: MMR(18 3) [4, 2, 13] [14, 17][0]=14
14 15 4: MMR(19 3) [4, 2, 13] [14, 17, 18][0]=14
14 18 4: MMR(22 3) [4, 2, 13] [14, 21][0]=14
14 19 4: MMR(23 3) [4, 2, 13] [14, 21, 22][0]=14
14 21 4: MMR(25 3) [4, 2, 13] [14, 21, 24][0]=14
14 22 4: MMR(26 3) [4, 2, 13] [14, 21, 24, 25][0]=14
30 27 5: MMR(31 3) [4, 2, 13, 29] [30][0]=30
30 28 5: MMR(32 3) [4, 2, 13, 29] [30, 31][0]=30
30 30 5: MMR(34 3) [4, 2, 13, 29] [30, 33][0]=30
30 31 5: MMR(35 3) [4, 2, 13, 29] [30, 33, 34][0]=30
30 34 5: MMR(38 3) [4, 2, 13, 29] [30, 37][0]=30
```

# APPENDIX (2) Example consistency proof

Worked example showing the production of a consistency proof.
The proof shows consistency between the MMR of size 4, with accumulator `A(4)`, and the subsequent MMR of size 11 and its accumulator `A(11)`.

The left axis is the zero based height index `g`, the horizontal axis are the leaf indices `e`.
```
g
4                         30


3              14                       29
             /    \
          /          \
2        6            13           21             28                37
       /   \        /    \
1     2     5      9     12     17     20     24       27       33      36
     / \   / \    / \   /  \   /  \
0   0   1 3   4  7   8 10  11 15  16 18  19 22  23   25   26  31  32   34  35   38
    0 . 1 2 . 3 .4 . 5  6 . 7  8 . 9 10  11 12  13   14   15  16  17   18  19   20 e
```

Both the numbered and the lettered variants of MMR size 11.
```
      g
     / \
    /   \                        7                  111
   /     \                     3   6   10        11     110     1010
  c       f      j            1 2 4 5 8  9 11   1 10 100  101 1000 1001 1011 
 / \     / \    / \
 a b     d e    h i     k
 | |     | |    | |     | 
d0 d1   d2 d3  d4 d5    d6
```

In our treatment above we labeled our accumulators according to the leaf count
as in RFC9162. For correspondence with MMR's lets switch to node counts. A
Consistency Proof for A(3) -> A(7) above is instead MMR(4) -> MRR(11).

The accumulator can be derived directly from the mmr size given access to the
node data and / or the appropriate accumulator covering nodes not locally
present. And is natural for the log implementation to "maintain as it goes"
anyway.

The binary properties the algorithms rely on are most obvious when the nodes
are numbered starting with 1.

```
MMR(4) -> MMR(11)

 3       11
1 2 4   1 10 100

   7                  111
 3   6   10        11     110     1010
1 2 4 5 8  9 11   1 10 100  101 1000 1001 1011
```

Storage access always works with 0 based node indices:

```
   6
 2   5    9
0 1 3 4 7  8 10
```

All algorithms, unless otherwise stated, work using node indices.

`JumpLeaftPerfect` requires a node position as argument.


Listing peak numbers in the accumulator's we get the node index paths:

  `A(4) = [2, 3]`; `A(11) = [6, 9, 10]`


Consistency Proof `A(4)[0]` in `A(11)` = `[5]`
Consistency Proof `A(4)[1]` in `A(11)` = `[4, 2]`

## Consistency Proof `A(4)[0]` in `A(11)`

To show `A(4)[0]` is consistently included in `A(11)`, we compute the inclusion
proof for node 2 in `A(11)` using [IndexProofPath](#IndexProofPath)(11, 2)

### Initialization

```
i = 2
1 = IndexHeight(2) = g
proof = []
```

### Round 0:

```
i = 2 = i
g = IndexHeight(2) = 1

(0) 2 is less than 11

iLocalPeak = 2
IndexHeight(3) = 0

(1) 0 is not greater than 1, take the else branch

iSibling = iLocalPeak + SiblingOffset(0) = 5
  => 2 + ((2 << 1) - 1)
  => 2 + 3 = 5
i = i + 2 << g = 6
  => 2 + 2 << g
  => 2 + 2 << 1 = 6

(3) 5 is not greater than or equal 11

path = [5]
g = 1 + 1 = 2
```

### Round 1:

```
i=6
g=2

(0) 6 is less than 11
iLocalPeak = 6
IndexHeight(7) = 0

(1) 0 is not greater than 1, take the else branch

iSibling = iLocalPeak + SiblingOffset(2) = 13
  => 6 + ((2 << 2) - 1)
  => 6 + 7 = 13
i = i + 2 << g = 14
  => 6 + 2 << 2
  => 6 + 8 = 14

(3) 13 is greater than 11

return [5], iLocalPeak=6, g=2
```

Consistency Proof `A(4)[0]` in `A(11)` = `[5]`

Because `H(2 || 5)` == 6, which is `A(11)[0]`


## Consistency Proof `A(4)[1]` in `A(11)`

  `A(4) = [2, 3]`; `A(11) = [6, 9, 10]`

To show `A(4)[1]` is consistently included in `A(11)`, we compute the inclusion
proof for node 3 in `A(11)` using [IndexProofPath](#IndexProofPath)(11, 3)

### Initialization
```
i = 3
0 = IndexHeight(3) = g
proof = []
```

### Round 0:

```
i = 3
g = IndexHeight(3) = 0

(0) 3 is less than 11

iLocalPeak = 3
IndexHeight(4) = 0

(1) 0 is not greater than 1, take the else branch

iSibling = iLocalPeak + SiblingOffset(0) = 4
  => 3 + ((2 << 0) - 1)
  => 3 + 2 - 1 = 4
i = i + 2 << g = 5
  => 3 + 2 << 0
  => 3 + 2 = 5

(3) 4 is not greater than or equal 11

path = [4]
g = 0 + 1 = 1
```

### Round 1:

```
From round 0
i = 5
g = 1

(0) 5 is less than 11

iLocalPeak = 5
IndexHeight(6) = 1

(1) 2 is greater than 1, take the primary case

iSibling = iLocalPeak - SiblingOffset(g) = 2
  => 5 - ((2 << 1) - 1)
  => 5 - (4 - 1)
  => 2
i = 5 + 1 = 6

(3) 2 is not greater than or equal 11

proof = [4, 2]
g = 1 + 1 = 2
```

### Round 2:

```
From round 1
i = 6
g = 2

(0) 6 is less than 11

iLocalPeak = 6
IndexHeight(7) = 2

(1) 2 is not greater than 2, take the else case

iSibling = iLocalPeak + SiblingOffset(g) = 13
  => 6 + ((2 << 2) - 1)
  => 6 + (8 - 1)
  => 6 + 7
i = i + 2 << g = 14
  => 6 + 2 << 2
  => 6 + 8 = 14

(3) 14 is greater than 11

return [4, 2], 6, 1 << g=2

```

Consistency Proof `A(4)[1]` in `A(11)` = `[4, 2]`

Because,

  `H(3 || 4)` = 5
  H(2 || 5) = 6

Which is, again, `A(11)[0]`

## IndexHeight(2)

node index 2, which is position 3 has an index height of 1
```
IndexHeight(2) == 1
  => 2+1 = 3 = b11 = pos
  => b11 is AllOnes
  BitLength(b11) - 1
  => 1
```

## IndexHeight(3)

node index 3, which is position 4 is a leaf, so has an index height of 0
```
IndexHeight(3) == 0
  => 3+1 = 4 = b100 = pos
  => b100 is !AllOnes
  JumpLeftPerfect(b100) =>
    => b100 - (1 << (BitLength(b100) - 1)) + 1
    => b100 - (1 << (3 - 1)) + 1
    => b100 - (1 << 2) + 1
    => b100 - 4 + 1
    => 1

  => b1 is AllOnes

  BitLength(0) -1
  => 1 - 1 = 0
  
```

## IndexHeight(4)

node index 4, which is posistion 5 and is a leaf index so has height of 0.

Notice that we need two jumps for this node to make it "left most for height"

```
IndexHeight(4) == 0
  => 4+1 = 5 = b101 = pos
  => b101 is !AllOnes
  JumpLeftPerfect(b101) =>
    => b101 - (1 << (BitLength(b101) - 1)) + 1
    => b101 - (1 << (3 - 1)) + 1
    => b101 - (1 << 2) + 1
    => b101 - 4 + 1
    => 2
  => b10 is !AllOnes
  JumpLeftPerfect(b10) =>
    => b10 - (1 << (BitLength(b10) - 1)) + 1
    => b10 - (1 << (2 - 1)) + 1
    => b10 - (1 << 1) + 1
    => b10 - 2 + 1 = 1

  => b1 is AllOnes

  0 = BitLength(0) - 1
```

## IndexHeight(6)

```
TODO
```

## IndexHeight(7)

node index 7, which is position 8 is a leaf, so has an index height of 0

```
  => 7+1 = 8 = b1000
  => b1000 is !AllOnes
  JumpLeftPerfect(b1000) =>
    => b1000 - (1 << (BitLength(b1000) - 1))
    => b1000 - ((1 << (4 - 1)) - 1)
    => b1000 - (8 - 1)
    => b1000 - 7 = 1
  => b1 is AllOnes

  BitLength(0) -1
  => 1 - 1 = 0
```
