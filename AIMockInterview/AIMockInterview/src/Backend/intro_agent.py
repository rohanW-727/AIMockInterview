"""
intro_agent.py — Intro stage agent.
"""
import asyncio
import logging
from base_agent import BaseInterviewAgent, _session_lock

logger = logging.getLogger(__name__)

GREETING = "Hi, welcome to your mock interview. What's your name, and what are you hoping to get out of this interview?"
ACK_Q1   = "Got it, thank you. Tell me about one project you built that you're proud of, and what you personally contributed."
ACK_Q2   = "Thanks for sharing that."
NUDGE_Q1 = "Feel free to take your time."
NUDGE_Q2 = "Whenever you're ready."
REASK_Q1 = "No problem — what's your name, and what are you hoping to get out of this interview?"

STAGE_TIMEOUT = 60.0


class IntroAgent(BaseInterviewAgent):
    GREETING = GREETING
    ACK_Q1   = ACK_Q1
    ACK_Q2   = ACK_Q2
    NUDGE_Q1 = NUDGE_Q1
    NUDGE_Q2 = NUDGE_Q2
    REASK_Q1 = REASK_Q1

    def __init__(self) -> None:
        super().__init__(stage_timeout=STAGE_TIMEOUT)

    async def on_exit(self) -> None:
        logger.info(f"[IntroAgent] on_exit — holds_lock={self._holds_lock}")
        if self._idle_task:  self._idle_task.cancel()
        if self._stage_task: self._stage_task.cancel()
        if self._holds_lock:
            self._holds_lock = False
            _session_lock.release()
            logger.info("[IntroAgent] lock released in on_exit")

    async def _on_q2_answered(self) -> None:
        logger.info("[IntroAgent] _on_q2_answered called")
        if self._transitioning:
            logger.info("[IntroAgent] already transitioning, abort")
            return
        logger.info("[IntroAgent] calling handoff")
        await self._handoff()

    async def _on_both_answered_idle(self) -> None:
        pass

    async def _on_stage_timeout(self) -> None:
        logger.info("[IntroAgent] _on_stage_timeout triggered")
        await self._handoff()

    async def _handoff(self) -> None:
        if self._transitioning:
            return
        self._transitioning = True
        if self._idle_task:  self._idle_task.cancel()
        if self._stage_task: self._stage_task.cancel()
        logger.info("[IntroAgent] handoff → ExperAgent")
        logger.info("[IntroAgent] releasing lock before update_agent")
        if self._holds_lock:
            self._holds_lock = False
            _session_lock.release()
        logger.info("[IntroAgent] calling update_agent(ExperAgent)")
        from exper_agent import ExperAgent
        self.session.update_agent(ExperAgent())  # CHANGED: Removed send_data call before this
        logger.info("[IntroAgent] handoff complete")