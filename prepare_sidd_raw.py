"""Download and link SIDD-CC Bayer inputs to aligned sRGB targets.

The RAW files are black-subtracted and white-level-normalized by SIDD-CC.
This script never subtracts those levels a second time. It keeps downloads under
data/siddcc_rawsource and creates lightweight train/calibration/validation
symlink trees under data/siddcc_bayer, grouped by physical scene number.
"""
from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from huggingface_hub import HfApi, hf_hub_download


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--raw-root', type=Path, default=Path('data/siddcc_rawsource'))
    parser.add_argument('--srgb-root', type=Path, default=Path('data/siddcc_srgb/SRGB'))
    parser.add_argument('--prepared-root', type=Path, default=Path('data/siddcc_bayer'))
    parser.add_argument('--validation-scene', default='001')
    parser.add_argument('--calibration-scene', default='005')
    parser.add_argument('--workers', type=int, default=4)
    args = parser.parse_args()
    if args.workers < 1: parser.error('--workers must be positive')
    if args.validation_scene == args.calibration_scene: parser.error('Validation and calibration scenes must differ')

    api = HfApi()
    remote = list(api.list_repo_tree('MhdMohammadi/SIDD-CC', repo_type='dataset',
                                     path_in_repo='Raw/train/Data', recursive=True))
    noisy_files = sorted(x.path for x in remote if hasattr(x, 'size') and
                         '/Data/' in x.path and '_NOISY_RAW_' in Path(x.path).name and x.path.endswith('.MAT'))
    if not noisy_files: raise FileNotFoundError('No SIDD-CC Raw/train noisy Bayer MAT files found.')

    pairs = []
    for noisy in noisy_files:
        rel = Path(noisy)
        scene_instance = rel.parent.name
        fields = scene_instance.split('_')
        if len(fields) < 2 or not fields[1].isdigit():
            raise ValueError(f'Cannot read physical scene id from {scene_instance}')
        scene_group = fields[1]
        stem = rel.stem
        metadata_name = stem.replace('_NOISY_RAW_', '_METADATA_RAW_') + '.MAT'
        target_name = stem.replace('_NOISY_RAW_', '_GT_SRGB_') + '.PNG'
        target = args.srgb_root / 'train' / 'Data' / scene_instance / target_name
        metadata = rel.parent / metadata_name
        if not target.is_file(): raise FileNotFoundError(f'Missing aligned SIDD-CC sRGB target: {target}')
        pairs.append({'remote_raw': noisy, 'remote_metadata': metadata.as_posix(),
                      'scene_instance': scene_instance, 'scene_group': scene_group,
                      'stem': stem, 'target': target})

    groups = sorted({x['scene_group'] for x in pairs})
    if args.validation_scene not in groups or args.calibration_scene not in groups:
        raise ValueError(f'Unknown split group; available scene groups: {groups}')
    if len(groups) < 3: raise ValueError('Need separate train, calibration, and validation scene groups')

    print(f'Preparing {len(pairs)} aligned RAW→sRGB pairs across {len(groups)} physical scenes; '
          f'validation={args.validation_scene}, calibration={args.calibration_scene}', flush=True)

    def download_pair(item):
        raw_path = hf_hub_download(repo_id='MhdMohammadi/SIDD-CC', filename=item['remote_raw'],
                                   repo_type='dataset', local_dir=args.raw_root)
        meta_path = hf_hub_download(repo_id='MhdMohammadi/SIDD-CC', filename=item['remote_metadata'],
                                    repo_type='dataset', local_dir=args.raw_root)
        return item, Path(raw_path), Path(meta_path)

    downloaded = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(download_pair, item) for item in pairs]
        for index, future in enumerate(as_completed(futures), 1):
            downloaded.append(future.result())
            if index % 10 == 0 or index == len(futures):
                print(f'downloaded {index}/{len(futures)} RAW pairs', flush=True)

    manifest = {'dataset': 'MhdMohammadi/SIDD-CC Raw train + SRGB train',
                'task': 'camera Bayer mosaic to aligned rendered sRGB',
                'raw_note': 'RAW data is already black-subtracted and white-level-normalized; AsShotNeutral and CFA metadata are applied by train.read_pair.',
                'split_unit': 'physical scene number (second token in scene-instance folder)',
                'validation_scene_group': args.validation_scene,
                'calibration_scene_group': args.calibration_scene,
                'train_scene_groups': [], 'validation_scene_instances': [],
                'calibration_scene_instances': [], 'splits': {}}

    for item, raw_path, meta_path in downloaded:
        if item['scene_group'] == args.validation_scene: split = 'validation'
        elif item['scene_group'] == args.calibration_scene: split = 'calibration'
        else: split = 'train'
        base = args.prepared_root / split
        links = [(base / 'input' / f"{item['stem']}.MAT", raw_path),
                 (base / 'target' / f"{item['stem']}.PNG", item['target']),
                 (base / 'metadata' / f"{item['stem']}.MAT", meta_path)]
        for link, source in links:
            link.parent.mkdir(parents=True, exist_ok=True)
            if link.is_symlink(): link.unlink()
            if link.exists() and not link.is_symlink():
                raise FileExistsError(f'Refusing to replace a non-symlink prepared file: {link}')
            if not link.exists(): link.symlink_to(source.resolve())
        manifest['splits'].setdefault(split, []).append({
            'input': item['remote_raw'], 'target': str(item['target']),
            'metadata': item['remote_metadata'], 'scene_instance': item['scene_instance'],
            'physical_scene_group': item['scene_group']})

    for split, rows in manifest['splits'].items():
        manifest['splits'][split] = sorted(rows, key=lambda x: x['input'])
    manifest['train_scene_groups'] = sorted({x['physical_scene_group'] for x in manifest['splits'].get('train', [])})
    manifest['validation_scene_instances'] = sorted({x['scene_instance'] for x in manifest['splits'].get('validation', [])})
    manifest['calibration_scene_instances'] = sorted({x['scene_instance'] for x in manifest['splits'].get('calibration', [])})
    groups_by_split = {split: {x['physical_scene_group'] for x in rows} for split, rows in manifest['splits'].items()}
    if any(groups_by_split[a] & groups_by_split[b] for a, b in [('train', 'validation'), ('train', 'calibration'), ('validation', 'calibration')]):
        raise RuntimeError('Physical scene leakage detected between data splits')
    manifest_path = args.prepared_root / 'manifest.json'
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print('pair counts:', {k: len(v) for k, v in manifest['splits'].items()}, flush=True)
    print('saved', manifest_path, flush=True)


if __name__ == '__main__': main()
