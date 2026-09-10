"""Extract the central-complex (CX) subgraph from MaleCNS v1.0 into the same
schema as data/flywire/cx_real.npz + cx_nodes.csv (see code/cx_real_dynamics.py load()).

Outputs (in --out-dir):
  cx_nodes_male.csv, cx_real_male.npz               (with FC2)
  cx_nodes_male_noFC2.csv, cx_real_male_noFC2.npz   (matched to FlyWire family set)

Usage:
  python code/extract_malecns_cx.py --in-dir data/malecns --out-dir data/malecns_cx
"""
import argparse, re, sys, time
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.feather as feather
import pyarrow.compute as pc

FAMILIES_NOFC2 = [
    'EPGt', 'EPG', 'PEN_a', 'PEN_b', 'PEG', 'Delta7', 'PFL1', 'PFL2', 'PFL3',
    'PFNa', 'PFNd', 'PFNm', 'PFNp', 'PFNv', 'PFR', 'PFGs', 'IbSpsP',
    'ER1', 'ER2', 'ER3', 'ER4', 'ER5', 'ER6', 'ExR', 'LNO1', 'LNO2', 'LNOa', 'LPsP',
]
FAMILIES_WITH_FC2 = FAMILIES_NOFC2 + ['FC2']

EXCITATORY = {'acetylcholine'}
INHIBITORY = {'gaba', 'glutamate'}
# FlyWire's cx_real.npz has zero unsigned edges (30294 + 34615 = 64909): every
# presynaptic neuron got a sign, so dopamine/serotonin/octopamine/unclear must
# have defaulted to excitatory there (confirmed empirically: mean edge sign for
# dopamine and serotonin presynaptic neurons in cx_real.npz is +1.0). We match
# that convention here rather than dropping edges, and report how many edges
# rode on the default.


def strip_paren(s):
    return re.sub(r'\(.*?\)', '', str(s))


def base_family(type_str, families):
    t = strip_paren(type_str)
    for f in families:
        if t.startswith(f):
            return f
    return None


def select_cx_bodies(ann, families):
    base = ann['type'].astype(str).map(strip_paren)
    mask = pd.Series(False, index=ann.index)
    for f in families:
        mask |= base.str.startswith(f)
    sel = ann.loc[mask, ['bodyId', 'type', 'rootSide', 'somaSide', 'flywireType', 'status']].copy()
    return sel


def side_map(row):
    for v in (row['rootSide'], row['somaSide']):
        if v == 'L':
            return 'left'
        if v == 'R':
            return 'right'
    return 'unknown'


def nt_for_bodies(body_ids, nt_df):
    sub = nt_df[nt_df['body'].isin(body_ids)].set_index('body')
    out = {}
    for b in body_ids:
        if b not in sub.index:
            out[b] = None
            continue
        row = sub.loc[b]
        if isinstance(row, pd.DataFrame):
            row = row.iloc[0]
        for col in ('consensus_nt', 'celltype_predicted_nt', 'predicted_nt'):
            v = row[col]
            if pd.notna(v) and v != 'unclear':
                out[b] = v
                break
        else:
            out[b] = None
    return out


def sign_for_nt(nt):
    if nt in INHIBITORY:
        return -1.0
    return 1.0  # acetylcholine, dopamine, serotonin, octopamine, unclear/None: default excitatory, matching FlyWire


def scan_weights_filtered(weights_path, body_set, batch_rows=5_000_000):
    f = feather.read_table(weights_path, memory_map=True)
    n = f.num_rows
    print(f'scanning {n:,} connectome rows in batches of {batch_rows:,}', flush=True)
    body_arr = pa.array(sorted(body_set), type=pa.int64())
    chunks = []
    t0 = time.time()
    for start in range(0, n, batch_rows):
        end = min(start + batch_rows, n)
        batch = f.slice(start, end - start)
        pre_ok = pc.is_in(batch['body_pre'], value_set=body_arr)
        post_ok = pc.is_in(batch['body_post'], value_set=body_arr)
        both = pc.and_(pre_ok, post_ok)
        kept = batch.filter(both)
        if kept.num_rows:
            chunks.append(kept.to_pandas())
        el = time.time() - t0
        print(f'  rows {end:,}/{n:,} ({100*end/n:.1f}%) kept={sum(c.shape[0] for c in chunks):,} elapsed={el:.0f}s', flush=True)
    if not chunks:
        return pd.DataFrame(columns=['body_pre', 'body_post', 'weight'])
    return pd.concat(chunks, ignore_index=True)


def build_extraction(ann, nt_df, edges_all, families, tag, out_dir):
    sel = select_cx_bodies(ann, families)
    sel = sel[sel['status'].isin(['Traced', 'Anchor', 'Assign'])].drop_duplicates('bodyId')
    body_ids = sel['bodyId'].to_numpy()
    n_nosided = 0
    sides = []
    for _, r in sel.iterrows():
        s = side_map(r)
        if s == 'unknown':
            n_nosided += 1
        sides.append(s)
    sel['side'] = sides

    nt_lookup = nt_for_bodies(body_ids, nt_df)
    sel['nt'] = sel['bodyId'].map(nt_lookup)
    n_no_nt = sel['nt'].isna().sum()
    nt_counts = sel['nt'].fillna('none').value_counts().to_dict()

    body_set = set(body_ids.tolist())
    e = edges_all[edges_all['body_pre'].isin(body_set) & edges_all['body_post'].isin(body_set)].copy()
    e['presyn_nt'] = e['body_pre'].map(nt_lookup)
    e['sign'] = e['presyn_nt'].map(sign_for_nt)
    n_edges_defaulted_excitatory = int((~e['presyn_nt'].isin(EXCITATORY | INHIBITORY)).sum())
    e['signed_w'] = e['sign'] * e['weight'].astype(np.float32)

    rid_to_idx = {b: i for i, b in enumerate(body_ids)}
    N = len(body_ids)
    W = np.zeros((N, N), dtype=np.float32)
    pre_idx = e['body_pre'].map(rid_to_idx).to_numpy()
    post_idx = e['body_post'].map(rid_to_idx).to_numpy()
    np.add.at(W, (pre_idx, post_idx), e['signed_w'].to_numpy())

    nodes_out = pd.DataFrame({
        'root_id': body_ids.astype(np.int64),
        'cell_type': sel['type'].to_numpy(),
        'side': sel['side'].to_numpy(),
        'nt': sel['nt'].fillna('unclear').to_numpy(),
    })
    nodes_csv = out_dir / f'cx_nodes_male{tag}.csv'
    nodes_out.to_csv(nodes_csv, index=False)
    npz_path = out_dir / f'cx_real_male{tag}.npz'
    np.savez(npz_path, W=W, root_ids=body_ids.astype(np.int64))

    stats = dict(
        n_neurons=N, n_no_side=n_nosided, n_no_nt=int(n_no_nt),
        n_edges=int((W != 0).sum()), nt_counts=nt_counts,
        n_edges_defaulted_excitatory=n_edges_defaulted_excitatory,
        excitatory_edges=int((W > 0).sum()), inhibitory_edges=int((W < 0).sum()),
        total_synapses=int(e['weight'].sum()),
    )
    print(tag or '(with FC2)', stats)
    return nodes_out, W, body_ids, stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--in-dir', default='data/malecns')
    ap.add_argument('--out-dir', default='data/malecns_cx')
    args = ap.parse_args()

    from pathlib import Path
    in_dir = Path(args.in_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print('loading annotations...', flush=True)
    ann = pd.read_feather(in_dir / 'body-annotations-male-cns-v1.0-minconf-0.5.feather')
    print('loading neurotransmitters...', flush=True)
    nt_df = pd.read_feather(in_dir / 'body-neurotransmitters-male-cns-v1.0.feather')

    sel_with = select_cx_bodies(ann, FAMILIES_WITH_FC2)
    sel_with = sel_with[sel_with['status'].isin(['Traced', 'Anchor', 'Assign'])].drop_duplicates('bodyId')
    body_set_with = set(sel_with['bodyId'].tolist())

    edges_all = scan_weights_filtered(in_dir / 'connectome-weights-male-cns-v1.0-minconf-0.5.feather', body_set_with)
    print(f'filtered edge rows (within CX-with-FC2 body set, both endpoints): {len(edges_all):,}', flush=True)

    results = {}
    results['with_fc2'] = build_extraction(ann, nt_df, edges_all, FAMILIES_WITH_FC2, '', out_dir)
    results['no_fc2'] = build_extraction(ann, nt_df, edges_all, FAMILIES_NOFC2, '_noFC2', out_dir)

    print('done.')
    return results


if __name__ == '__main__':
    main()
