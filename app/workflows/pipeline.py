"""
Workflow pipeline executor.

Reads YAML pipeline definitions and executes them step-by-step.
Each step calls either the agent, a tool, or an internal action.

Pipeline YAML format:
  name: "My Workflow"
  trigger:
    type: manual | scheduled | file_event
    cron: "0 9 * * *"        # only for scheduled
  steps:
    - action: query_agent
      input: "Summarise today's emails"
    - action: log
      message: "Pipeline complete"
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from app.utils.logger import logger


@dataclass
class StepResult:
    step_index: int
    action: str
    success: bool
    output: str = ""
    error: Optional[str] = None


@dataclass
class PipelineResult:
    pipeline_name: str
    success: bool
    step_results: List[StepResult] = field(default_factory=list)
    error: Optional[str] = None


class WorkflowPipeline:
    """Execute a single named workflow pipeline."""

    def __init__(self, definition: Dict[str, Any]) -> None:
        self._def = definition
        self._name = definition.get("name", "unnamed")
        self._steps: List[Dict] = definition.get("steps", [])

    def run(self, session_id: Optional[str] = None) -> PipelineResult:
        logger.info(f"Pipeline '{self._name}' starting ({len(self._steps)} steps)")
        results: List[StepResult] = []
        prev_output: str = ""

        for idx, step in enumerate(self._steps):
            action = step.get("action", "unknown")
            logger.debug(f"  Step {idx+1}: {action}")

            try:
                output = self._execute_step(step, prev_output, session_id)
                results.append(StepResult(idx, action, True, output))
                prev_output = output
                logger.debug(f"  Step {idx+1} OK: {output[:100]}")
            except Exception as e:
                err = str(e)
                results.append(StepResult(idx, action, False, error=err))
                logger.error(f"  Step {idx+1} FAILED ({action}): {err}")
                # Stop on first failure
                return PipelineResult(self._name, False, results, error=err)

        logger.info(f"Pipeline '{self._name}' completed successfully.")
        return PipelineResult(self._name, True, results)

    def _execute_step(
        self, step: Dict, prev_output: str, session_id: Optional[str]
    ) -> str:
        action = step.get("action")

        if action == "query_agent":
            prompt = step.get("input", "").replace("{{prev}}", prev_output)
            return self._query_agent(prompt, session_id)

        elif action == "log":
            msg = step.get("message", prev_output)
            logger.info(f"[Pipeline log] {msg}")
            return msg

        elif action == "http_request":
            return self._http_request(step)

        elif action == "wait":
            import time
            seconds = step.get("seconds", 1)
            time.sleep(seconds)
            return f"Waited {seconds}s"

        else:
            raise ValueError(f"Unknown pipeline action: '{action}'")

    @staticmethod
    def _query_agent(prompt: str, session_id: Optional[str]) -> str:
        from app.agent.core import get_agent

        agent = get_agent()
        resp = agent.chat(prompt, session_id=session_id)
        return resp.answer

    @staticmethod
    def _http_request(step: Dict) -> str:
        import httpx

        url = step.get("url", "")
        method = step.get("method", "GET").upper()
        headers = step.get("headers", {})
        payload = step.get("payload")

        resp = httpx.request(method, url, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        return resp.text[:1000]


# ---------------------------------------------------------------------------
# Pipeline loader
# ---------------------------------------------------------------------------

def load_pipeline_from_file(path: str | Path) -> WorkflowPipeline:
    path = Path(path)
    with path.open("r") as f:
        definition = yaml.safe_load(f)
    return WorkflowPipeline(definition)


def list_pipelines(pipeline_dir: str = "./workflows") -> List[Path]:
    return [
        p for p in Path(pipeline_dir).glob("*.yaml")
        if p.name != "scheduled_jobs.yaml"
    ]
