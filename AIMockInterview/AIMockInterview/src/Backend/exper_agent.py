"""
exper_agent.py — Experience stage agent.
Questions:
  Q1: Can you tell me about your work experience so far?
  Q2: What was the biggest challenge you've faced in your work, and how did you handle it?
"""
import asyncio
import logging
from base_agent import BaseInterviewAgent, send_data

logger = logging.getLogger(__name__)

# ─── Experience spoken lines ───────────────────────────────────────────────────

GREETING = "Great, now let's move to the experience section. Can you tell me about your work experience so far?"
ACK_Q1   = "Thanks for sharing. What was the biggest challenge you've faced in your work, and how did you handle it?"
ACK_Q2   = "Thank you, really appreciate that."
NUDGE_Q1 = "Feel free to take your time."
NUDGE_Q2 = "Whenever you're ready."
REASK_Q1 = "No problem — can you tell me about your work experience so far?"

# Closing lines
CLOSE_Q2   = "Thank you so much for your time today — it was a pleasure speaking with you. Best of luck with everything, and we'll be in touch soon. Take care! Please press End Call"
CLOSE_IDLE = "That's everything from me — please click End Call whenever you're ready."
CLOSE_TOUT = "I'm sorry to interrupt — we've run out of time. Thank you so much for your time today. Best of luck. Take care!"

STAGE_TIMEOUT = 180.0


class ExperAgent(BaseInterviewAgent):

    GREETING = GREETING
    ACK_Q1   = ACK_Q1
    ACK_Q2   = ACK_Q2
    NUDGE_Q1 = NUDGE_Q1
    NUDGE_Q2 = NUDGE_Q2
    REASK_Q1 = REASK_Q1

    def __init__(self) -> None:
        logger.info("[ExperAgent] __init__ called")
        super().__init__(stage_timeout=STAGE_TIMEOUT)
        logger.info("[ExperAgent] __init__ complete")

    async def on_enter(self) -> None:
        # First do normal on_enter (acquire lock, say greeting, store room)
        await super().on_enter()
        # Then send stage_changed event so frontend updates timer
        logger.info("[ExperAgent] sending stage_changed event")
        await send_data(self, {"event": "stage_changed", "stage": "experience"})
        logger.info("[ExperAgent] stage_changed sent")

    async def _on_q2_answered(self) -> None:
        # Override to say closing line instead of just ACK_Q2
        logger.info("[ExperAgent] _on_q2_answered called")
        if self._transitioning:
            logger.info("[ExperAgent] already transitioning, abort")
            return
        logger.info("[ExperAgent] Q2 answered → saying closing line and completing interview")
        await self._close(CLOSE_Q2)

    async def _on_both_answered_idle(self) -> None:
        # Both answered + idle → close with idle message
        logger.info("[ExperAgent] _on_both_answered_idle triggered")
        await self._close(CLOSE_IDLE)

    async def _on_stage_timeout(self) -> None:
        # Timer expired → close with timeout message
        logger.info("[ExperAgent] _on_stage_timeout triggered")
        await self._close(CLOSE_TOUT)

    async def _close(self, line: str) -> None:
        if self._transitioning:
            return
        self._transitioning = True
        if self._idle_task:  self._idle_task.cancel()
        if self._stage_task: self._stage_task.cancel()
        logger.info(f"[ExperAgent] closing — {line[:50]}...")
        await self.session.say(line, allow_interruptions=False)
        logger.info("[ExperAgent] sending interview_complete event")
        await send_data(self, {"event": "interview_complete"})
        logger.info("[ExperAgent] interview_complete sent")