"""Tests for the Lambda handler code (deepagents-based).

These tests validate the handler string by executing it with mocked deepagents
imports — no real LLM calls are made.
"""
import json
import os
import sys
from unittest.mock import MagicMock, patch


def _make_mock_deepagents():
    """Build mock modules for ``deepagents`` and ``langchain_aws`` so the handler can import them."""
    mock_agent = MagicMock()
    mock_agent.invoke.return_value = {
        "messages": [MagicMock(content="Agent completed monitoring run.")]
    }

    mock_create = MagicMock(return_value=mock_agent)
    mock_backend_cls = MagicMock()
    mock_chat_bedrock = MagicMock()

    # Module stubs
    deepagents_mod = MagicMock()
    deepagents_mod.create_deep_agent = mock_create

    backends_mod = MagicMock()
    local_shell_mod = MagicMock()
    local_shell_mod.LocalShellBackend = mock_backend_cls

    langchain_aws_mod = MagicMock()
    langchain_aws_mod.ChatBedrockConverse = mock_chat_bedrock

    bootstrap_mod = MagicMock()

    return {
        "bootstrap": bootstrap_mod,
        "deepagents": deepagents_mod,
        "deepagents.backends": backends_mod,
        "deepagents.backends.local_shell": local_shell_mod,
        "langchain_aws": langchain_aws_mod,
        "mock_create": mock_create,
        "mock_backend_cls": mock_backend_cls,
        "mock_chat_bedrock": mock_chat_bedrock,
        "mock_agent": mock_agent,
    }


def _exec_handler():
    """Compile and return the handler function from LAMBDA_HANDLER_CODE."""
    from stacks.lambda_stack import LAMBDA_HANDLER_CODE

    handler_globals = {}
    exec(LAMBDA_HANDLER_CODE, handler_globals)  # noqa: S102
    return handler_globals["handler"]


def test_handler_returns_200():
    """Handler returns statusCode 200 with run_time and result."""
    mocks = _make_mock_deepagents()
    handler = _exec_handler()

    mock_context = MagicMock()
    mock_context.get_remaining_time_in_millis.return_value = 900_000

    with patch.dict(
        sys.modules,
        {
            "langchain_aws": mocks["langchain_aws"],
            "deepagents": mocks["deepagents"],
            "deepagents.backends": mocks["deepagents.backends"],
            "bootstrap": mocks["bootstrap"],
            "deepagents.backends.local_shell": mocks["deepagents.backends.local_shell"],
        },
    ):
        os.environ["AGENT_MOUNT_PATH"] = "/tmp/test-agent"
        os.environ["AGENT_MODEL_ID"] = "anthropic.claude-sonnet-4-6-v1"
        os.environ["AGENT_MAX_TOKENS"] = "4096"
        result = handler({}, mock_context)

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert "run_time" in body
    assert "result" in body
    assert body["result"] == "Agent completed monitoring run."


def test_handler_sets_path():
    """Handler prepends /opt/awscli to PATH for the AWS CLI layer."""
    mocks = _make_mock_deepagents()
    handler = _exec_handler()

    mock_context = MagicMock()
    mock_context.get_remaining_time_in_millis.return_value = 900_000

    original_path = os.environ.get("PATH", "")

    with patch.dict(
        sys.modules,
        {
            "langchain_aws": mocks["langchain_aws"],
            "deepagents": mocks["deepagents"],
            "deepagents.backends": mocks["deepagents.backends"],
            "bootstrap": mocks["bootstrap"],
            "deepagents.backends.local_shell": mocks["deepagents.backends.local_shell"],
        },
    ):
        os.environ["AGENT_MOUNT_PATH"] = "/tmp/test-agent"
        handler({}, mock_context)

    assert os.environ["PATH"].startswith("/opt/awscli:")


def test_handler_creates_backend_with_correct_args():
    """LocalShellBackend is created with mount path, virtual_mode=False, etc."""
    mocks = _make_mock_deepagents()
    handler = _exec_handler()

    mock_context = MagicMock()
    mock_context.get_remaining_time_in_millis.return_value = 900_000

    with patch.dict(
        sys.modules,
        {
            "langchain_aws": mocks["langchain_aws"],
            "deepagents": mocks["deepagents"],
            "deepagents.backends": mocks["deepagents.backends"],
            "bootstrap": mocks["bootstrap"],
            "deepagents.backends.local_shell": mocks["deepagents.backends.local_shell"],
        },
    ):
        os.environ["AGENT_MOUNT_PATH"] = "/mnt/agent"
        handler({}, mock_context)

    mocks["mock_backend_cls"].assert_called_once_with(
        root_dir="/mnt/agent",
        virtual_mode=False,
        timeout=120,
        inherit_env=True,
    )


def test_handler_creates_agent_with_skills_and_memory(tmp_path):
    """create_deep_agent receives skills and memory paths from the mount."""
    mocks = _make_mock_deepagents()
    handler = _exec_handler()

    mock_context = MagicMock()
    mock_context.get_remaining_time_in_millis.return_value = 900_000

    # Create the mount directories so os.path.isdir/isfile checks pass
    mount = str(tmp_path / "agent")
    os.makedirs(os.path.join(mount, "skills"))
    with open(os.path.join(mount, "AGENTS.md"), "w") as f:
        f.write("# Agent Memory\n")

    with patch.dict(
        sys.modules,
        {
            "langchain_aws": mocks["langchain_aws"],
            "deepagents": mocks["deepagents"],
            "deepagents.backends": mocks["deepagents.backends"],
            "bootstrap": mocks["bootstrap"],
            "deepagents.backends.local_shell": mocks["deepagents.backends.local_shell"],
        },
    ):
        os.environ["AGENT_MOUNT_PATH"] = mount
        os.environ["AGENT_MODEL_ID"] = "anthropic.claude-sonnet-4-6-v1"
        os.environ["AGENT_MAX_TOKENS"] = "4096"
        handler({}, mock_context)

    # Model is now a ChatBedrockConverse instance (mock), not a string
    mocks["mock_chat_bedrock"].assert_called_once_with(
        model="anthropic.claude-sonnet-4-6-v1", max_tokens=4096,
    )
    call_kwargs = mocks["mock_create"].call_args
    assert call_kwargs.kwargs["skills"] == [os.path.join(mount, "skills")]
    assert call_kwargs.kwargs["memory"] == [os.path.join(mount, "AGENTS.md")]
    assert call_kwargs.kwargs["model"] == mocks["mock_chat_bedrock"].return_value


def test_handler_prompt_includes_remaining_time():
    """Continuation prompt includes the remaining Lambda time budget."""
    mocks = _make_mock_deepagents()
    handler = _exec_handler()

    mock_context = MagicMock()
    mock_context.get_remaining_time_in_millis.return_value = 840_000  # 14 min

    with patch.dict(
        sys.modules,
        {
            "langchain_aws": mocks["langchain_aws"],
            "deepagents": mocks["deepagents"],
            "deepagents.backends": mocks["deepagents.backends"],
            "bootstrap": mocks["bootstrap"],
            "deepagents.backends.local_shell": mocks["deepagents.backends.local_shell"],
        },
    ):
        os.environ["AGENT_MOUNT_PATH"] = "/mnt/agent"
        handler({}, mock_context)

    # Inspect the prompt sent to agent.invoke()
    invoke_call = mocks["mock_agent"].invoke.call_args
    messages = invoke_call[0][0]["messages"]
    prompt_content = messages[0]["content"]
    assert "Remaining Lambda time: 840s" in prompt_content
    assert "Quota Monitoring Run" in prompt_content


def test_handler_truncates_long_result():
    """Handler truncates agent output to 1000 chars."""
    mocks = _make_mock_deepagents()
    long_content = "x" * 2000
    mocks["mock_agent"].invoke.return_value = {
        "messages": [MagicMock(content=long_content)]
    }
    handler = _exec_handler()

    mock_context = MagicMock()
    mock_context.get_remaining_time_in_millis.return_value = 900_000

    with patch.dict(
        sys.modules,
        {
            "langchain_aws": mocks["langchain_aws"],
            "deepagents": mocks["deepagents"],
            "deepagents.backends": mocks["deepagents.backends"],
            "bootstrap": mocks["bootstrap"],
            "deepagents.backends.local_shell": mocks["deepagents.backends.local_shell"],
        },
    ):
        os.environ["AGENT_MOUNT_PATH"] = "/tmp/test-agent"
        result = handler({}, mock_context)

    body = json.loads(result["body"])
    assert len(body["result"]) == 1000
