import json, tempfile, unittest
from pathlib import Path

from uacf.metric_evidence import verify
from uacf.util import Fault, file_hash


class MetricEvidenceTest(unittest.TestCase):
    def make(self, root, *, token_kind='output_tokens', denominator_kind='active_turn_wall_seconds', value=20):
        source = root/'native.json';source.write_text('{"tokens":200,"seconds":10}',encoding='utf8')
        report = root/'report.html';report.write_text('<p>20 output Token/s</p>',encoding='utf8')
        manifest = root/'metrics.json'
        data=dict(schema='uacf-metric-evidence-1', report=dict(path=str(report),sha256=file_hash(report)),
                  sources=[dict(id='native',path=str(source),sha256=file_hash(source))],
                  metrics=[dict(id='decode',purpose='model_decode_comparison',numerator=200,denominator=10,value=value,
                                denominator_kind=denominator_kind,token_kind=token_kind,source_ids=['native'],meaning='Generated output per active work second')])
        manifest.write_text(json.dumps(data),encoding='utf8')
        return dict(path=str(manifest),sha256=file_hash(manifest))

    def test_active_output_rate(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);self.assertEqual(verify(root,self.make(root))['metrics_checked'],1)

    def test_calendar_denominator_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            with self.assertRaises(Fault) as e:verify(root,self.make(root,denominator_kind='calendar_span_seconds'))
            self.assertEqual(e.exception.code,'METRIC_DENOMINATOR')

    def test_total_tokens_cannot_be_decode_speed(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            with self.assertRaises(Fault) as e:verify(root,self.make(root,token_kind='total_tokens'))
            self.assertEqual(e.exception.code,'METRIC_COMPARABILITY')

    def test_arithmetic_and_stale_report_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            with self.assertRaises(Fault):verify(root,self.make(root,value=2))
            declaration=self.make(root)
            (root/'report.html').write_text('changed',encoding='utf8')
            with self.assertRaises(Fault):verify(root,declaration)


if __name__=='__main__':unittest.main()
