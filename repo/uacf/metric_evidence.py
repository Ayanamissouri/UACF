"""Check the source and denominator of derived work-rate claims in UACF reports.

This checks declared arithmetic and provenance, not the semantic truth of a report.
"""
import json
from pathlib import Path

from .util import Fault, file_hash

SCHEMA = 'uacf-metric-evidence-1'
ACTIVE_SECONDS = {'active_turn_wall_seconds', 'model_response_seconds'}
TOKEN_KINDS = {'total_tokens', 'input_tokens', 'cached_input_tokens', 'output_tokens'}


def verify(root, declaration):
    root = Path(root).resolve()
    if not isinstance(declaration, dict) or set(declaration) != {'path', 'sha256'}:
        raise Fault('METRIC_EVIDENCE', 'metric manifest path and hash required')
    path = Path(declaration['path']).resolve()
    if not path.is_relative_to(root) or not path.is_file() or file_hash(path) != declaration['sha256']:
        raise Fault('METRIC_EVIDENCE', 'metric manifest outside workspace, absent or changed')
    data = json.loads(path.read_text(encoding='utf8'))
    if data.get('schema') != SCHEMA or not isinstance(data.get('metrics'), list) or not data['metrics']:
        raise Fault('METRIC_EVIDENCE', 'nonempty typed metric manifest required')
    report = data.get('report') or {}
    report_path = Path(report.get('path', '')).resolve()
    if not report_path.is_relative_to(root) or not report_path.is_file() or file_hash(report_path) != report.get('sha256'):
        raise Fault('METRIC_EVIDENCE', 'report changed after metric evidence freeze')
    sources = data.get('sources') or []
    ids = set()
    for source in sources:
        source_path = Path(source.get('path', '')).resolve()
        if source.get('id') in ids or not source_path.is_relative_to(root) or not source_path.is_file() or file_hash(source_path) != source.get('sha256'):
            raise Fault('METRIC_EVIDENCE', 'source identity missing, duplicated or changed')
        ids.add(source['id'])
    if not ids:
        raise Fault('METRIC_EVIDENCE', 'at least one immutable source required')
    seen = set()
    for metric in data['metrics']:
        key = metric.get('id')
        if not isinstance(key, str) or not key or key in seen:
            raise Fault('METRIC_EVIDENCE', 'unique metric ID required')
        seen.add(key)
        try:
            numerator = float(metric['numerator'])
            denominator = float(metric['denominator'])
            result = float(metric['value'])
        except (KeyError, ValueError, TypeError):
            raise Fault('METRIC_EVIDENCE', 'numeric numerator, denominator and value required')
        if denominator <= 0 or abs(numerator / denominator - result) > max(0.02, abs(result) * 1e-5):
            raise Fault('METRIC_EVIDENCE', 'derived metric does not recalculate')
        if not isinstance(metric.get('source_ids'), list) or not metric['source_ids'] or any(x not in ids for x in metric['source_ids']):
            raise Fault('METRIC_EVIDENCE', 'metric lacks declared source')
        purpose = metric.get('purpose')
        basis = metric.get('denominator_kind')
        tokens = metric.get('token_kind')
        if purpose in ('work_throughput', 'model_decode_comparison'):
            if basis not in ACTIVE_SECONDS or tokens not in TOKEN_KINDS:
                raise Fault('METRIC_DENOMINATOR', 'work rate needs active wall or response time and typed tokens')
        if purpose == 'model_decode_comparison' and tokens != 'output_tokens':
            raise Fault('METRIC_COMPARABILITY', 'local decode rate only compares to output tokens')
        if purpose == 'quota_calibration' and (not metric.get('snapshot_at') or not metric.get('alignment')):
            raise Fault('METRIC_ALIGNMENT', 'quota calibration needs a timestamp and alignment explanation')
        if not isinstance(metric.get('meaning'), str) or not metric['meaning']:
            raise Fault('METRIC_EVIDENCE', 'state what the ratio means')
    return {'ok': True, 'metrics_checked': len(seen), 'source_ids': sorted(ids), 'report_sha256': report['sha256']}
