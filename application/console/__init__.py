"""Application workflows for digital employee console and debug surfaces.

These workflows serve employee console surfaces such as the current debug page. They are
separate from the normal MessageEvent flow handled by message_workflow.
"""

from .http_input import EmployeeConsoleHttpIngress, EmployeeConsoleHttpInput
from .config_center import ConfigCenterWorkflow
from .event_log import EventLogConsoleWorkflow
from .monitor import MonitorConsoleWorkflow
from .prompt import PromptConsoleWorkflow
from .session import SessionConsoleWorkflow
from .task import TaskConsoleWorkflow

__all__ = [
    "ConfigCenterWorkflow",
    "EmployeeConsoleHttpIngress",
    "EmployeeConsoleHttpInput",
    "EventLogConsoleWorkflow",
    "MonitorConsoleWorkflow",
    "PromptConsoleWorkflow",
    "SessionConsoleWorkflow",
    "TaskConsoleWorkflow",
]
