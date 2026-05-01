"""工作流引擎测试"""
import asyncio
import pytest
import yaml
from pathlib import Path
from src.agent.workflow import (
    WorkflowEngine, WorkflowStep, StepType, StepContext, ExecutionState
)


@pytest.fixture
def workflow_file(tmp_path):
    wf_path = tmp_path / "test_workflow.yaml"
    wf_path.write_text("""
name: test_loop
start: step_a
steps:
  - id: step_a
    type: prompt
    next: step_b
  - id: step_b
    type: llm_stream
    next: step_c
  - id: step_c
    type: parse
    next: step_d
  - id: step_d
    type: branch
    conditions:
      - if: "len(commands) > 0"
        next: step_e
    default: step_f
  - id: step_e
    type: execute
    next: step_f
  - id: step_f
    type: memory
    next: done
  - id: done
    type: end
""", encoding="utf-8")
    return str(wf_path)


@pytest.fixture
def engine(workflow_file):
    e = WorkflowEngine()
    e.load_from_yaml(workflow_file)
    return e


class TestWorkflowEngine:

    def test_load_yaml(self, engine):
        assert len(engine.steps) == 7
        assert engine.start_step == "step_a"
        assert StepType.PROMPT in [s.type for s in engine.steps.values()]

    @pytest.mark.asyncio
    async def test_linear_execution(self, engine):
        """线性执行: prompt → llm → parse → branch(default) → memory → end"""
        call_order = []

        async def mock_handler(ctx):
            call_order.append(ctx)
            return ctx

        for st in [StepType.PROMPT, StepType.LLM_STREAM, StepType.PARSE,
                    StepType.EXECUTE, StepType.MEMORY]:
            engine.register_handler(st, mock_handler)

        ctx = StepContext(event={"type": "test"})
        result = await engine.run(ctx)

        assert engine.state == ExecutionState.COMPLETED
        assert len(call_order) == 4  # prompt, llm, parse, memory (跳过 execute)

    @pytest.mark.asyncio
    async def test_branch_execution(self, engine):
        """分支执行: 有 commands 时走 execute"""
        call_order = []

        async def mock_parse(ctx):
            ctx.commands = [{"intent": "test", "params": {}}]
            call_order.append("parse")
            return ctx

        async def mock_execute(ctx):
            ctx.command_results = [{"status": "success"}]
            call_order.append("execute")
            return ctx

        async def mock_other(ctx):
            call_order.append("other")
            return ctx

        engine.register_handler(StepType.PROMPT, mock_other)
        engine.register_handler(StepType.LLM_STREAM, mock_other)
        engine.register_handler(StepType.PARSE, mock_parse)
        engine.register_handler(StepType.EXECUTE, mock_execute)
        engine.register_handler(StepType.MEMORY, mock_other)

        ctx = StepContext()
        await engine.run(ctx)

        assert "execute" in call_order

    @pytest.mark.asyncio
    async def test_pause_resume(self, engine):
        """暂停和继续"""
        import asyncio

        async def slow_handler(ctx):
            await asyncio.sleep(0.1)
            return ctx

        for st in [StepType.PROMPT, StepType.LLM_STREAM, StepType.PARSE,
                    StepType.MEMORY]:
            engine.register_handler(st, slow_handler)

        async def run_and_pause():
            task = asyncio.create_task(engine.run(StepContext()))
            await asyncio.sleep(0.05)
            engine.pause()
            assert engine.state == ExecutionState.PAUSED
            await asyncio.sleep(0.1)
            engine.resume()
            result = await task
            return result

        result = await run_and_pause()
        assert engine.state == ExecutionState.COMPLETED

    @pytest.mark.asyncio
    async def test_step_mode(self, engine):
        """单步模式"""
        step_count = 0

        async def counting_handler(ctx):
            nonlocal step_count
            step_count += 1
            return ctx

        for st in [StepType.PROMPT, StepType.LLM_STREAM, StepType.PARSE,
                    StepType.MEMORY]:
            engine.register_handler(st, counting_handler)

        # 启用单步模式
        engine.step_once()

        ctx = StepContext()

        # 在后台运行工作流（单步模式会暂停等待 resume）
        task = asyncio.create_task(engine.run(ctx))

        # 等待一小段时间让第一步执行
        await asyncio.sleep(0.05)

        # 验证已经执行了一步
        assert step_count >= 1
        # 单步模式后状态可能是 STEP_WAITING 或 PAUSED（取决于时机）
        assert engine.state in (ExecutionState.STEP_WAITING, ExecutionState.PAUSED)

        # 继续执行剩余步骤（关闭单步模式）
        engine.resume()
        result = await task

        # 验证最终完成
        assert engine.state == ExecutionState.COMPLETED

    def test_condition_evaluation(self, engine):
        """条件表达式求值"""
        ctx = StepContext(commands=[{"intent": "test"}])
        assert engine._evaluate_condition("len(commands) > 0", ctx) is True
        assert engine._evaluate_condition("len(commands) > 5", ctx) is False

        ctx2 = StepContext(command_results=[{"status": "rejected"}])
        assert engine._evaluate_condition(
            "any(r.get('status') == 'rejected' for r in command_results)", ctx2
        ) is True
