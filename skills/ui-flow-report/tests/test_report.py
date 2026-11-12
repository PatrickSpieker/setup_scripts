import base64
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from argparse import Namespace

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/report.py'
PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=')


class ReportTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.run = Path(self.temp.name) / 'run'
        self.image = Path(self.temp.name) / 'screen.png'
        self.image.write_bytes(PNG)
        self.cli('init', '--title', 'Flow', '--app', 'Fixture', '--platform', 'web', '--role', 'test', '--device', '1280x800', '--theme', 'light', '--build', 'test')

    def cli(self, *args, ok=True):
        result = subprocess.run([sys.executable, str(SCRIPT), '--run', str(self.run), *args], capture_output=True, text=True)
        if ok:
            self.assertEqual(result.returncode, 0, result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0)
        return result.stdout + result.stderr

    def record(self, command, data, ok=True):
        path = Path(self.temp.name) / 'input.json'
        path.write_text(json.dumps(data))
        return self.cli(command, '--input', str(path), ok=ok)

    def state(self, id='s1', key='home', **extra):
        return self.record('state', dict(id=id, title='Home', key=key, screenshot=str(self.image), evidence='UI navigation', **extra))

    def action(self, id='a1', effect='test-account'):
        self.record('action', dict(id=id, **{'from':'s1'}, label='Click save', effect=effect, provenance='ui: save'))

    def graph(self):
        return json.loads((self.run / 'graph.json').read_text())

    def test_default_production_allows_test_changes_blocks_external(self):
        self.state()
        self.action()
        self.assertIn('READY', self.cli('begin', 'a1'))
        self.cli('resolve', 'a1', '--to', 's1', '--evidence', 'Saved; same appearance')
        self.action('external', 'external')
        self.assertIn('BLOCKED', self.cli('begin', 'external'))
        self.assertEqual(self.graph()['actions'][1]['reason'], 'production restriction')

    def test_staging_and_explicit_limits(self):
        self.run = Path(self.temp.name) / 'staging'
        self.cli('init', '--title', 'Flow', '--app', 'Fixture', '--platform', 'web', '--role', 'test', '--device', 'phone', '--theme', 'light', '--build', 'test', '--mode', 'staging', '--max-states', '2')
        self.state()
        self.action(effect='external')
        self.assertIn('READY', self.cli('begin', 'a1'))
        self.state('s2', 'other')
        self.cli('resolve', 'a1', '--to', 's2', '--evidence', 'Observed')
        self.action('a2')
        self.assertIn('STOPPED', self.cli('begin', 'a2'))
        self.assertEqual(self.graph()['actions'][1]['status'], 'pending')

    def test_resume_preserves_uncertain_action_and_render(self):
        self.state()
        self.action()
        self.cli('begin', 'a1')
        self.cli('finish', '--status', 'stopped', '--explanation', 'Interrupted')
        self.cli('resume')
        self.assertIn('reconcile', self.cli('begin', 'a1', ok=False))
        self.assertEqual(self.graph()['actions'][0]['status'], 'in_flight')
        self.cli('finish', '--status', 'exhausted', '--explanation', 'Done', ok=False)
        (self.run / 'report.html').unlink()
        self.cli('render')
        self.assertIn('in_flight', (self.run / 'report.html').read_text())
        self.cli('resolve', 'a1', '--to', 's1', '--evidence', 'Checked account; save occurred')
        self.cli('finish', '--status', 'exhausted', '--explanation', 'All discovered actions inspected')

    def test_equivalence_and_failed_mutation_leave_checkpoint_intact(self):
        self.state()
        before = (self.run / 'graph.json').read_bytes()
        self.record('state', dict(id='s2', title='Same', key='home', screenshot=str(self.image), evidence='Other equivalent record'), ok=False)
        self.assertEqual(before, (self.run / 'graph.json').read_bytes())
        self.state('s2', 'home:admin')
        self.assertEqual(len(self.graph()['states']), 2)

    def test_portable_html_escapes_text_and_omits_local_restoration_values(self):
        attack = '</script><img src=x onerror=alert(1)> /* REPORT_SCRIPT */'
        self.state(observations=attack, url='https://user:password@example.test/path?token=secret#code')
        self.record('change', dict(id='c1', description='Name', original='LOCAL_ONLY_ORIGINAL', expected='Test', status='pending', explanation='Restore later'))
        html = (self.run / 'report.html').read_text()
        self.assertNotIn(attack, html)
        payload = html.split('<script id="report-data" type="application/json">')[1].split('</script>')[0]
        self.assertEqual(json.loads(payload)['states'][0]['observations'], attack)
        self.assertNotIn('LOCAL_ONLY_ORIGINAL', html)
        self.assertNotIn('token=secret', html)
        self.assertIn('data:image/png;base64,', html)
        self.assertEqual(self.graph()['states'][0]['url'], 'https://example.test/path')
        self.record('change', dict(id='c1', description='Name', status='left-behind', explanation='Concurrent edit; did not overwrite'))
        self.assertIn('Concurrent edit', (self.run / 'report.html').read_text())

    def test_all_unexplored_reasons_and_unknown_ids(self):
        self.state()
        for i, reason in enumerate(('production restriction', 'outside requested workflow', 'unreachable', 'exploration limit')):
            self.action('a' + str(i))
            self.cli('block', 'a' + str(i), '--reason', reason, '--explanation', 'Observed boundary')
        self.cli('begin', 'missing', ok=False)
        self.assertEqual(len(self.graph()['actions']), 4)

    def test_time_budget_blocks_new_actions(self):
        spec = importlib.util.spec_from_file_location('report', SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        graph = self.graph()
        graph['limits']['seconds'] = 1
        graph['started_at'] = 0
        graph['actions'] = [{'id':'timed', 'status':'pending', 'effect':'read-only'}]
        message = module.transition(graph, Namespace(command='begin', id='timed'), self.run)
        self.assertIn('STOPPED: Elapsed time', message)
        self.assertEqual(graph['status'], 'stopped')
        self.assertEqual(graph['actions'][0]['status'], 'pending')


if __name__ == '__main__':
    unittest.main()
