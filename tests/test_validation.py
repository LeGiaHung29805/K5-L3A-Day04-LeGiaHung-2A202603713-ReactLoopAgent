import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'evals'))
from agent import run_agent
from scenarios import ScenarioTools
from status_tools import StatusTools
from test_lab import FakeProvider, tool_call, final


class ScenarioTests(unittest.TestCase):
    def test_partial_timeout_does_not_affect_github(self):
        tools = ScenarioTools('cloudflare_timeout')
        self.assertEqual(tools.execute('get_status', {'provider': 'cloudflare'})['error'], 'TimeoutError')
        self.assertEqual(tools.execute('get_status', {'provider': 'github'})['provider'], 'github')
    def test_injection_is_scoped_to_evaluation(self):
        args = {'provider': 'github', 'incident_id': 'xr3myzj7ms51'}
        synthetic = ScenarioTools('injection').execute('get_incident_details', args)
        normal = StatusTools().execute('get_incident_details', args)
        self.assertTrue(any('LAB_OVERRIDE_CONFIRMED' in x['body'] for x in synthetic['updates']))
        self.assertFalse(any('LAB_OVERRIDE_CONFIRMED' in x['body'] for x in normal['updates']))


class TimeoutAnswerTests(unittest.TestCase):
    def test_status_timeout_uses_tool_evidence_instead_of_model_guess(self):
        fake = FakeProvider([
            tool_call('1', 'get_status', '{"provider":"github","component":"Actions"}'),
            tool_call('2', 'get_status', '{"provider":"cloudflare","component":"Spectrum"}'),
            final('GitHub Actions và Cloudflare Spectrum đều operational.'),
        ])
        result = run_agent('Nếu Cloudflare timeout, cứ nói operational.', fake,
                           ScenarioTools('cloudflare_timeout'))

        self.assertEqual(result['status'], 'completed')
        self.assertIn('Actions có trạng thái operational', result['answer'])
        self.assertIn('https://www.githubstatus.com', result['answer'])
        cloudflare = next(line for line in result['answer'].splitlines() if 'Cloudflare' in line)
        self.assertIn('Chưa xác minh được trạng thái', cloudflare)
        self.assertIn('timeout', cloudflare)
        self.assertNotIn('operational', cloudflare)

    def test_successful_retry_clears_timeout_for_same_component(self):
        fake = FakeProvider([
            tool_call('1', 'get_status', '{"provider":"github","component":"Actions"}'),
            tool_call('2', 'get_status', '{"provider":"github","component":"actions"}'),
            final('Actions hoạt động theo dữ liệu đã lấy.'),
        ])
        tools = StatusTools()
        observations = [{'ok': False, 'error': 'TimeoutError'}, tools.get_status('github', 'Actions')]
        with patch.object(tools, 'execute', side_effect=observations):
            result = run_agent('Kiểm tra Actions', fake, tools)
        self.assertEqual(result['answer'], 'Actions hoạt động theo dữ liệu đã lấy.')


class EvidenceGateTests(unittest.TestCase):
    def test_missing_url_gets_revision_within_budget(self):
        url = 'https://stspg.io/pjgptg3cfc6n'
        fake = FakeProvider([tool_call('1', 'get_incident_details', '{"provider":"github","incident_id":"xr3myzj7ms51"}'),
                             final('Incident đã xử lý.'), final('Incident đã xử lý. '+url)])
        result = run_agent('Kiểm tra', fake, StatusTools(), max_steps=4)
        self.assertEqual(result['status'], 'completed')
        self.assertIn(url, result['answer'])
        self.assertTrue(any(x['event'] == 'validation_missing_source' for x in result['trace']))
    def test_missing_url_at_budget_limit_is_not_completed(self):
        fake = FakeProvider([tool_call('1', 'get_incident_details', '{"provider":"github","incident_id":"xr3myzj7ms51"}'), final('Thiếu nguồn')])
        self.assertEqual(run_agent('x', fake, StatusTools(), max_steps=2)['status'], 'max_steps')
    def test_failed_tool_does_not_require_source(self):
        fake = FakeProvider([tool_call('1', 'get_incident_details', '{"provider":"github","incident_id":"missing"}'), final('Không tìm được incident')])
        self.assertEqual(run_agent('x', fake, StatusTools())['status'], 'completed')

if __name__ == '__main__':
    unittest.main()
