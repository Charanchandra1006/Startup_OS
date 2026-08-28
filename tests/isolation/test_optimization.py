import pytest
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'packages', 'shared-types', 'python'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'services', 'orchestrator'))

from chief_types.llm_client import ContextCompressor
from chief_types.observability import TracingManager, AgentRunSpan
from dispatcher import PredictiveResultCache, Dispatcher
from chief_types.models import AgentOutput, ConfidenceLevel, TaskStatus

def test_context_compressor():
    long_text = "A" * 20000
    compressed = ContextCompressor.compress_context(long_text, max_chars=16000)
    assert len(compressed) <= 16100  # Account for padding/message
    assert "CONTEXT COMPRESSED" in compressed

def test_predictive_cache():
    cache = PredictiveResultCache()
    output = AgentOutput(
        answer="test",
        supporting_data=[],
        confidence=ConfidenceLevel.HIGH,
        model_used="test-model",
        prompt_version="1.0.0"
    )
    cache.set("agent_test:hash1", output)
    
    assert cache.get("agent_test:hash1") == output
    assert cache.get("agent_test:hash2") is None

@pytest.mark.asyncio
async def test_dispatcher_dynamic_concurrency():
    dispatcher = Dispatcher()
    # It should bound between 5 and 20
    assert dispatcher._get_dynamic_concurrency(2) == 5
    assert dispatcher._get_dynamic_concurrency(10) == 10
    assert dispatcher._get_dynamic_concurrency(50) == 20
