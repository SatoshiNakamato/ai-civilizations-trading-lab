import tempfile
import unittest
from pathlib import Path

from civilizations.you_gateway import ResearchRequest, YouIntelligenceGateway


class FakeManager:
    def __init__(self):
        self.calls = 0

    def authorize(self, agent_id, task):
        self.calls += 1
        return {'allowed': True, 'remaining': 9}

    def credential_for(self, provider):
        return 'test-key'

    def snapshot(self):
        return {'usage': {}}


class YouGatewayTests(unittest.TestCase):
    def test_non_assigned_agent_is_blocked_without_spending(self):
        with tempfile.TemporaryDirectory() as d:
            manager = FakeManager()
            gateway = YouIntelligenceGateway(manager, Path(d) / 'cache.json')
            result = gateway.research(ResearchRequest('A001', 'test'))
            self.assertFalse(result.ok)
            self.assertEqual(result.error, 'agent_not_assigned')
            self.assertEqual(manager.calls, 0)

    def test_invalid_effort_is_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            manager = FakeManager()
            gateway = YouIntelligenceGateway(manager, Path(d) / 'cache.json')
            result = gateway.research(ResearchRequest('A002', 'test', effort='bad'))
            self.assertFalse(result.ok)
            self.assertEqual(result.error, 'invalid_research_effort')
            self.assertEqual(manager.calls, 0)

    def test_cache_key_changes_with_effort(self):
        a = ResearchRequest('A002', 'same', effort='lite')
        b = ResearchRequest('A002', 'same', effort='deep')
        self.assertNotEqual(YouIntelligenceGateway._key(a), YouIntelligenceGateway._key(b))


if __name__ == '__main__':
    unittest.main()
