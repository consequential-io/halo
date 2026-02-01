"""Base Controller - Common agent flow patterns."""

import json
import logging
from typing import Dict, Any, Optional, TypeVar, Generic
from abc import ABC, abstractmethod

try:
    from google.adk.agents import LlmAgent
    from google.adk.runners import Runner
    from google.genai import types
    HAS_ADK = True
except ImportError:
    HAS_ADK = False
    LlmAgent = None  # type: ignore
    Runner = None  # type: ignore
    types = None  # type: ignore

from config.session_manager import get_session_manager

logger = logging.getLogger(__name__)

T = TypeVar('T')


class BaseController(ABC, Generic[T]):
    """
    Base controller for agent execution.

    Provides common patterns for:
    - Agent initialization
    - Session management
    - Error handling
    - Response parsing
    """

    def __init__(self, app_name: str = "agatha"):
        self.app_name = app_name
        self.session_manager = get_session_manager()
        self._agent: Optional[LlmAgent] = None
        self._runner: Optional[Runner] = None

    @property
    @abstractmethod
    def agent_name(self) -> str:
        """Return the agent name."""
        pass

    @property
    @abstractmethod
    def agent_prompt(self) -> str:
        """Return the agent prompt/instruction."""
        pass

    @property
    def agent_description(self) -> str:
        """Return the agent description."""
        return f"{self.agent_name} agent"

    def _initialize_agent(self, model: str) -> None:
        """Initialize the ADK agent and runner."""
        if not HAS_ADK:
            logger.warning(f"ADK not available, {self.agent_name} running in mock mode")
            return

        self._agent = LlmAgent(
            name=self.agent_name,
            model=model,
            description=self.agent_description,
            instruction=self.agent_prompt,
        )

        self._runner = self.session_manager.create_runner(
            agent=self._agent,
            app_name=self.app_name
        )

    async def run_agent_flow(
        self,
        message_content: str,
        user_id: str = "agatha_user",
        session_id: Optional[str] = None,
    ) -> str:
        """
        Run the agent with a message and return the response.

        Args:
            message_content: The message to send to the agent
            user_id: User identifier
            session_id: Optional existing session ID

        Returns:
            The agent's response text
        """
        if not HAS_ADK or self._runner is None:
            logger.warning("ADK not available, returning empty response")
            return ""

        # Create or get session
        if session_id:
            session = await self.session_manager.get_session(
                app_name=self.app_name,
                user_id=user_id,
                session_id=session_id
            )
        else:
            session = await self.session_manager.create_session(
                app_name=self.app_name,
                user_id=user_id
            )

        if session is None:
            logger.error("Failed to create/get session")
            return ""

        # Create message content
        user_message = types.Content(
            role="user",
            parts=[types.Part(text=message_content)]
        )

        # Run the agent
        response_text = ""
        try:
            async for event in self._runner.run_async(
                user_id=user_id,
                session_id=session.id,
                new_message=user_message,
            ):
                if hasattr(event, 'content') and event.content:
                    if hasattr(event.content, 'parts'):
                        for part in event.content.parts:
                            if hasattr(part, 'text') and part.text:
                                response_text += part.text

            logger.debug(f"{self.agent_name} response: {response_text[:200]}...")

        except Exception as e:
            logger.error(f"Agent execution failed: {e}")
            raise

        return response_text

    def parse_json_response(
        self,
        response_text: str,
        default: Optional[T] = None
    ) -> T:
        """
        Parse JSON from agent response.

        Args:
            response_text: Raw response text
            default: Default value if parsing fails

        Returns:
            Parsed JSON object
        """
        try:
            text = response_text.strip()

            # Remove markdown code blocks if present
            if text.startswith("```"):
                lines = text.split("\n")
                json_lines = []
                in_block = False
                for line in lines:
                    if line.startswith("```") and not in_block:
                        in_block = True
                        continue
                    elif line.startswith("```") and in_block:
                        break
                    elif in_block:
                        json_lines.append(line)
                text = "\n".join(json_lines)

            return json.loads(text)

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON response: {e}")
            if default is not None:
                return default
            raise

    @abstractmethod
    async def execute(self, request: Dict[str, Any]) -> T:
        """Execute the controller's main logic."""
        pass
