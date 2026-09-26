from __future__ import annotations

import json
import threading
import time
import pytest
import uvicorn

from app.main import app
from judge_simulator import JudgeSimulator, LLMProvider, ScoreResult, BotClient

class MockLLMProvider(LLMProvider):
    def name(self) -> str:
        return "Mock Judge LLM"

    def complete(self, prompt: str, system: str = None) -> str:
        if "Say 'ready'" in prompt:
            return "ready"
        return json.dumps({
            "specificity": 9,
            "specificity_reason": "Message contains verifiable grounded numbers and citations.",
            "category_fit": 9,
            "category_fit_reason": "Tone and vocabulary strictly match category rules.",
            "merchant_fit": 9,
            "merchant_fit_reason": "Personalized to merchant identity and catalog offers.",
            "decision_quality": 9,
            "decision_quality_reason": "Trigger payload relevance clearly communicated.",
            "engagement_compulsion": 9,
            "engagement_reason": "Single low-friction call-to-action.",
            "hint": "Baseline compositions perform well."
        })


@pytest.fixture(scope="module", autouse=True)
def run_server():
    server_thread = threading.Thread(
        target=uvicorn.run,
        kwargs={"app": app, "host": "127.0.0.1", "port": 8080, "log_level": "error"},
        daemon=True
    )
    server_thread.start()
    time.sleep(1.0)  # Wait for server startup
    yield


def test_judge_simulator_all_scenarios():
    llm = MockLLMProvider()
    judge = JudgeSimulator(llm)
    judge.client = BotClient("http://127.0.0.1:8080")
    success = judge.run("all")
    assert success is True
