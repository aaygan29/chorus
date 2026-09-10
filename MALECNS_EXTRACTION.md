# MaleCNS v1.0 central-complex extraction

Extracts a CX subgraph from the MaleCNS v1.0 connectome into the same schema
CHORUS already consumes for FlyWire v783 (data/flywire/cx_real.npz +
cx_nodes.csv, loaded by code/cx_real_dynamics.py `load()`). Script:
code/extract_malecns_cx.py.

## Source data

All CC-BY 4.0, dataset version `male-cns:v1.0`, downloaded from the
neuprint/Janelia MaleCNS release (feather exports, no auth required).

| file | size | sha256 |
|---|---|---|
| body-annotations-male-cns-v1.0-minconf-0.5.feather | 14,483,314 B | 2177e246113e4cfbf1e7772ec37c6da1955ff22e8063d0b1f833101f99a9a3b2 |
| body-neurotransmitters-male-cns-v1.0.feather | 43,282,834 B | 95c9289220663abeb3409f3ad9e5a7f8a53f8093f5139d15502cd08da8879621 |
| connectome-weights-male-cns-v1.0-minconf-0.5.feather | 1,051,241,946 B | e35da783d1c686b2b58b3b87cd6a403ae43bfcfba8bff28e08ef752c1a56afc1 |

## Output schema (matches FlyWire exactly)

- `data/malecns_cx/cx_real_male.npz`: `W` (N x N float32, signed, `W[i,j]` =
  weight from neuron i to neuron j, i.e. row = presynaptic, matching the
  `W.T @ r` convention in `cx_real_dynamics.py`), `root_ids` (N int64).
- `data/malecns_cx/cx_nodes_male.csv`: columns `root_id,cell_type,side,nt`.
- Matched-family variants without FC2 (see below): `cx_real_male_noFC2.npz`,
  `cx_nodes_male_noFC2.csv`.

Confirmed compatible by loading both output pairs through
`cx_real_dynamics.load()` and stepping `RealCX` one tick; no schema errors,
shapes are `(1161,1161)` / `(1161,)` for the with-FC2 set.

## Neuron selection

Same CX cell-type families FlyWire's `cx_nodes.csv` uses, matched by prefix
on the `type` column with parenthetical suffixes stripped (e.g.
`PEN_a(PEN1)` -> `PEN_a`), same convention the existing loader already
applies to `cell_type`. Families: EPG, EPGt, PEN_a, PEN_b, PEG, Delta7, PFL1,
PFL2, PFL3, PFNa, PFNd, PFNm, PFNp, PFNv, PFR, PFGs, IbSpsP, ER1-6, ExR,
LNO1, LNO2, LNOa, LPsP. Restricted to `status` in {Traced, Anchor, Assign}
(excludes Orphan/Glia/Unimportant fragments), one row per `bodyId`.

**FC2 asymmetry.** FlyWire's `cx_nodes.csv` has no FC2 neurons at all
(cell_type is neither `FC2` nor `FC2A/B/C`); MaleCNS has 92 (FC2A/B/C). This
is a real difference between the two connectome node tables, not a filter
artifact. Per instructions, FC2 is included in the primary male extraction,
and a second, FC2-free extraction is emitted for a like-for-like comparison
against FlyWire (`cx_nodes_male_noFC2.csv` / `cx_real_male_noFC2.npz`,
N=1069).

## Neuron counts per family, male vs FlyWire-female

| family | male | flywire-female |
|---|---|---|
| Delta7 | 42 | 42 |
| EPG | 46 | 47 |
| EPGt | 4 | 4 |
| ER1 | 28 | 29 |
| ER2 | 41 | 43 |
| ER3 | 151 | 146 |
| ER4 | 37 | 35 |
| ER5 | 21 | 21 |
| ER6 | 4 | 4 |
| ExR | 26 | 26 |
| FC2 | 92 | 0 |
| IbSpsP | 31 | 30 |
| LNO1 | 4 | 4 |
| LNO2 | 2 | 2 |
| LNOa | 2 | 2 |
| LPsP | 2 | 2 |
| PEG | 18 | 20 |
| PEN_a | 20 | 20 |
| PEN_b | 22 | 22 |
| PFGs | 18 | 28 |
| PFL1 | 14 | 14 |
| PFL2 | 12 | 12 |
| PFL3 | 24 | 24 |
| PFNa | 58 | 55 |
| PFNd | 40 | 40 |
| PFNm | 47 | 83 |
| PFNp | 291 | 244 |
| PFNv | 20 | 21 |
| PFR | 44 | 31 |
| **total** | **1161** (1069 without FC2) | **1051** |

Most families are within a few neurons of FlyWire's counts (proofreading
completeness differences between the two connectomes, not a selection bug).
PFGs (18 vs 28), PFNm (47 vs 83) and PFNp (291 vs 244) are the largest
relative gaps and are flagged as an honest limitation, not adjusted for.

## Neurotransmitter assignment and edge signing

Primary source `consensus_nt`, falling back to `celltype_predicted_nt`, then
`predicted_nt`, skipping any value equal to `unclear`. Within the selected CX
neuron set every neuron resolved to a definite call on at least one of the
three columns (`n_no_nt = 0` for both the with-FC2 and no-FC2 sets), so no
node needed a fallback to "no NT at all".

Node-level `nt` counts (with FC2): acetylcholine 769, gaba 286, glutamate 54,
serotonin 48, dopamine 4.

Edge sign is taken from the presynaptic neuron's NT, exactly as FlyWire's
`top_nt`-based signing:
- gaba, glutamate -> inhibitory (glutamate is inhibitory in the fly CX,
  matching how the FlyWire extraction signs Delta7).
- everything else (acetylcholine, dopamine, serotonin, octopamine, and any
  neuron whose presynaptic NT could not be resolved past "unclear" in *any*
  of the three columns) -> excitatory by default.

**Judgement call, verified against FlyWire's own data rather than assumed.**
The spec names acetylcholine as excitatory and gaba/glutamate as inhibitory
but leaves dopamine/serotonin/octopamine/unclear unspecified. `cx_real.npz`
has exactly 64,909 signed edges with zero unsigned entries (30,294 + 34,615),
so FlyWire's own extraction never dropped an edge for an ambiguous NT call;
checking the actual sign of edges from FlyWire's 33 dopaminergic and 42
serotonergic CX neurons empirically confirms they are signed excitatory
(mean per-neuron edge sign +1.0 for both). The male extraction reproduces
this default-to-excitatory convention instead of dropping those edges, so the
two connectomes are directly comparable. 3,367 of 105,409 with-FC2 edges
(3.2%) rode on this default (presynaptic NT was dopamine, serotonin,
octopamine, or unresolved); this is reported, not hidden.

## Side assignment

`rootSide` (values `L`/`R`/`unknown`/`M`) mapped to `left`/`right`, falling
back to `somaSide` when `rootSide` is `unknown`/missing. Every one of the
1161 (and 1069 no-FC2) selected CX neurons resolved to `left` or `right`;
`n_no_side = 0`.

## Edge counts, male vs FlyWire-female

| | male (with FC2) | male (no FC2) | flywire-female |
|---|---|---|---|
| signed edges | 105,409 | 100,116 | 64,909 |
| excitatory edges | 60,946 | 55,709 | 34,615 |
| inhibitory edges | 44,463 | 44,407 | 30,294 |
| total synapse count (sum of weights) | 1,000,211 | 977,282 | not recomputed from FlyWire raw weights (npz stores only signed weight, not separately the synapse count) |

The male CX subgraph has ~1.6x FlyWire's edge count, consistent with it
having ~1.1x the neurons and MaleCNS generally being more densely traced /
proofread than the FlyWire v783 female connectome release used here.

## Cross-connectome type correspondence (flywireType)

All 1161 male CX neurons carry a `flywireType` annotation (100% coverage) --
this is the strongest available direct link between the two connectomes,
since it is Janelia's own cross-registration of MaleCNS types onto the
FlyWire naming scheme, not a name-matching heuristic. Of 48 distinct
`flywireType` base labels (parenthetical/split-suffix stripped) present in
the male CX set, 37 match a FlyWire-female `cx_nodes.csv` cell_type base
label exactly. The 11 unmatched labels are due to different sub-type
splitting conventions between the two releases (e.g. `ER3d_a,ER3d_c` vs
FlyWire's `ER3d`, `ExR2` vs FlyWire's `ExR2_1`/`ExR2_2`) plus FC2's absence
from FlyWire, not missing neurons. Conversely 7 FlyWire-female base labels
have no male-side flywireType match, for the mirror reason (FlyWire splits
`ER3a`/`ER3p`/`PFR` differently, or the male fork of the split label wasn't
tagged). Net: the correspondence is essentially complete at the family
level and the residual mismatches are sub-type bookkeeping, not real
biological gaps.

## Sanity check: textbook circuit signs (docs/CHORUS_fine_control.md Section 1)

| population | claim | male result | flywire result | agree? |
|---|---|---|---|---|
| EPG | cholinergic / excitatory | 46/46 acetylcholine | 47/47 acetylcholine | yes |
| Delta7 | glutamatergic / inhibitory | 42/42 glutamate | 41/42 glutamate, 1/42 acetylcholine | yes |
| PFL3 | cholinergic / excitatory | 24/24 acetylcholine | 24/24 acetylcholine | yes |

All three textbook signs reproduce independently in MaleCNS. No disagreement
to report here.

## Judgement calls and alternatives (summary)

1. **FC2 inclusion.** Included in the primary extraction (matches the CX
   biology, present in MaleCNS); a matched no-FC2 variant is also emitted
   for direct comparison. Alternative considered: drop FC2 entirely to force
   symmetry -- rejected because it would misrepresent MaleCNS's actual CX
   composition.
2. **NT fallback chain and dopamine/serotonin/octopamine/unclear signing.**
   Adopted `consensus_nt -> celltype_predicted_nt -> predicted_nt`,
   default-to-excitatory for anything not gaba/glutamate, verified against
   FlyWire's actual signed-edge counts (see above) rather than assumed.
   Alternative: drop edges from neurons with non-cholinergic/non-inhibitory
   or unresolved NT -- rejected because FlyWire's own npz shows it did not
   do this (zero unsigned edges), and dropping would break comparability.
3. **Status filter.** Restricted to Traced/Anchor/Assign, excluding
   Orphan/Glia/Unimportant. Alternative: include Orphan bodies (partially
   traced but still assigned a cell type) -- rejected as those are known
   truncated reconstructions and would inflate node count without real
   connectivity.
4. **Side fallback.** `rootSide` primary, `somaSide` fallback. Alternative:
   somaSide-only (used in the annotation table's dominant convention) --
   rejected because `rootSide` is the geometry-based call and closer to
   FlyWire's per-neuron left/right partition semantics; in practice this CX
   neuron set needed no fallback at all (0 unresolved).
5. **Duplicate bodyId handling.** `drop_duplicates('bodyId')` after family
   selection (a body can match more than one family prefix only if its type
   string itself is ambiguous, which did not occur here, but the dedup is
   defensive).

## Secondary deliverable: DN -> VNC -> motor edge list

`data/malecns_cx/dn_vnc_edges.csv`: paths of at most 2 hops from the three
descending neurons CHORUS actuates through (DNa02 x2, DNp09 x2, MDN x4) to
`vnc_motor` neurons (708 present in MaleCNS), either direct (1 hop) or via a
single `vnc_intrinsic` interneuron (2 hops, edge weight = min of the two hop
weights as a conservative bottleneck estimate). Columns: `body_pre`
(descending neuron), `inter_body` (interneuron, empty for direct paths),
`body_post` (motor neuron), `weight`, `dn_type`, `path` (`direct` or
`via_interneuron`), `hops`, `motor_type`.

Counts: 40,320 rows total (129 direct, 40,191 via one interneuron); 695 of
708 motor neurons are reached within 2 hops from at least one of the three
DN types (628 via DNa02, 666 via DNp09, 668 via MDN, counting distinct motor
targets per DN type, overlapping). No modeling was done on top of this; it
is raw material for a future body-model replacement, not itself a body
model.

## Verification run (real output)

```
scanning 151,856,684 connectome rows in batches of 5,000,000
...
filtered edge rows (within CX-with-FC2 body set, both endpoints): 105,409
(with FC2) {'n_neurons': 1161, 'n_no_side': 0, 'n_no_nt': 0, 'n_edges': 105409,
 'nt_counts': {'acetylcholine': 769, 'gaba': 286, 'glutamate': 54, 'serotonin': 48, 'dopamine': 4},
 'n_edges_defaulted_excitatory': 3367, 'excitatory_edges': 60946, 'inhibitory_edges': 44463,
 'total_synapses': 1000211}
_noFC2 {'n_neurons': 1069, 'n_no_side': 0, 'n_no_nt': 0, 'n_edges': 100116,
 'nt_counts': {'acetylcholine': 677, 'gaba': 286, 'glutamate': 54, 'serotonin': 48, 'dopamine': 4},
 'n_edges_defaulted_excitatory': 3046, 'excitatory_edges': 55709, 'inhibitory_edges': 44407,
 'total_synapses': 977282}
done.
```

Loading via `cx_real_dynamics.load()`:

```
W, rid, nodes = load(npz='data/malecns_cx/cx_real_male.npz', csv='data/malecns_cx/cx_nodes_male.csv')
W.shape, rid.shape -> (1161, 1161) (1161,)
nnz(W) -> 105409
RealCX(W, nodes).step() -> runs without error, returns shape (1161,)
```

No fudging: the family-count gaps (PFGs, PFNm, PFNp) and the FC2 asymmetry
are reported as-is, not adjusted by loosening or tightening the selection to
chase a closer match to FlyWire's numbers.
