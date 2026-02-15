import asyncio
import logging
import json
import time
from collections.abc import AsyncIterable
from livekit.agents import Agent, ModelSettings
from livekit.agents.llm import ChatChunk

logger = logging.getLogger(__name__)

# ─── Timings ───────────────────────────────────────────────────────────────────

IDLE_TIMEOUT        = 10.0  # seconds of silence before nudge (increased from 10.0)
Q1_SKIP_TIMEOUT     = 40.0  # re-ask Q1 if unanswered for this long (increased from 35.0)
MIN_ANSWER_WORDS    = 2

# ─── Global lock — only ONE agent active at a time ────────────────────────────

_session_lock = asyncio.Lock()

# ─── Helpers ───────────────────────────────────────────────────────────────────

def extract_transcript(new_message) -> str:
    if new_message and hasattr(new_message, "content"):
        if isinstance(new_message.content, list):
            return " ".join(
                p.text if hasattr(p, "text") else str(p)
                for p in new_message.content
            ).strip()
        return str(new_message.content).strip()
    return ""


async def send_data(agent, payload: dict):
    """Send data via the agent's stored room reference."""
    if not agent._room:
        logger.error("[send_data] agent._room is None, cannot send data")
        return
    
    await agent._room.local_participant.publish_data(
        json.dumps(payload).encode(), reliable=True,
    )
    logger.info(f"[send_data] sent: {payload}")


# ─── Base class ────────────────────────────────────────────────────────────────

class BaseInterviewAgent(Agent):
    """
    All spoken lines are hardcoded strings via session.say().
    llm_node is overridden to return nothing — LLM NEVER auto-speaks.
    Lock is acquired on on_enter and released on on_exit.
    Subclasses set GREETING/ACK_Q1/ACK_Q2/NUDGE_Q1/NUDGE_Q2/REASK_Q1
    and override _on_q2_answered / _on_both_answered_idle / _on_stage_timeout.
    """

    GREETING : str = ""
    ACK_Q1   : str = ""
    ACK_Q2   : str = ""
    NUDGE_Q1 : str = ""
    NUDGE_Q2 : str = ""
    REASK_Q1 : str = ""

    def __init__(self, stage_timeout: float) -> None:
        super().__init__(instructions="You are silent. You never speak on your own.")
        self._stage_timeout = stage_timeout
        self._silence_since = time.time()
        self._agent_busy    = False
        self._q1_answered   = False
        self._q2_answered   = False
        self._processing    = False
        self._idle_task     = None
        self._stage_task    = None
        self._transitioning = False
        self._holds_lock    = False
        self._room          = None  # Will be set in on_enter

    # ── Silence the LLM entirely ───────────────────────────────────────────────

    async def llm_node(
        self,
        chat_ctx,
        tools,
        model_settings: ModelSettings,
    ) -> AsyncIterable[ChatChunk]:
        return
        yield

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    async def on_enter(self) -> None:
        logger.info(f"[{self.__class__.__name__}] on_enter — acquiring lock")
        await _session_lock.acquire()
        self._holds_lock = True
        # Store room reference from activity
        activity = self._get_activity_or_raise()
        if hasattr(activity, '_room'):
            self._room = activity._room
            logger.info(f"[{self.__class__.__name__}] room stored from activity._room")
        elif hasattr(activity, 'room'):
            self._room = activity.room
            logger.info(f"[{self.__class__.__name__}] room stored from activity.room")
        else:
            logger.error(f"[{self.__class__.__name__}] cannot find room in activity")
        logger.info(f"[{self.__class__.__name__}] lock acquired — saying greeting")
        await self.session.say(self.GREETING, allow_interruptions=False)
        # NOW start the silence clock - greeting is done, waiting for user answer
        self._silence_since = time.time()
        logger.info(f"[{self.__class__.__name__}] greeting done — silence clock started at {time.time():.2f}")
        self._idle_task  = asyncio.create_task(self._idle_watchdog())
        self._stage_task = asyncio.create_task(self._stage_timeout_watchdog())

    async def on_exit(self) -> None:
        logger.info(f"[{self.__class__.__name__}] on_exit — releasing lock")
        if self._idle_task:  self._idle_task.cancel()
        if self._stage_task: self._stage_task.cancel()
        # Double release of lock is prevented here
        if self._holds_lock:
            self._holds_lock = False
            _session_lock.release()
            logger.info(f"[{self.__class__.__name__}] lock released")

    # ── Speech tracking ────────────────────────────────────────────────────────

    async def on_agent_speech_started(self) -> None:
        self._agent_busy = True
        logger.info(f"[{self.__class__.__name__}] SPEECH STARTED at {time.time():.2f} — idle watchdog PAUSED")

    
    async def on_agent_speech_ended(self) -> None:
        self._agent_busy = False
        # Don't reset silence clock here - let the question-asking code do it(Prevents constant nudging)
        logger.info(f"[{self.__class__.__name__}] SPEECH ENDED at {time.time():.2f} — agent no longer busy")

    # ── Turn handling ──────────────────────────────────────────────────────────

    async def on_user_turn_completed(self, turn_ctx, new_message) -> None:
        if not self._holds_lock or self._transitioning or self._processing:
            logger.info(f"[{self.__class__.__name__}] turn ignored - holds_lock={self._holds_lock} transitioning={self._transitioning} processing={self._processing}")
            return
        self._processing = True
        try:
            transcript = extract_transcript(new_message)
            word_count = len(transcript.split())
            logger.info(f"[{self.__class__.__name__}] transcript ({word_count}w): {transcript!r}")

            if word_count < MIN_ANSWER_WORDS:
                logger.info(f"[{self.__class__.__name__}] answer too short, ignoring")
                self._silence_since = time.time()
                return

            self._silence_since = time.time()

            if not self._q1_answered:
                self._q1_answered = True
                logger.info(f"[{self.__class__.__name__}] Q1 ANSWERED → saying ACK_Q1")
                await self.session.say(self.ACK_Q1, allow_interruptions=False)
                # NOW reset silence clock - Q2 is being asked, waiting for user answer
                self._silence_since = time.time()
                logger.info(f"[{self.__class__.__name__}] Q2 asked — silence clock reset at {time.time():.2f}")

            elif not self._q2_answered:
                self._q2_answered = True
                logger.info(f"[{self.__class__.__name__}] Q2 ANSWERED → calling _on_q2_answered")
                await self._on_q2_answered()

        finally:
            self._processing = False

    # ── Overrideable hooks ─────────────────────────────────────────────────────

    async def _on_q2_answered(self) -> None:
        await self.session.say(self.ACK_Q2, allow_interruptions=False)

    async def _on_both_answered_idle(self) -> None:
        pass

    async def _on_stage_timeout(self) -> None:
        pass

    # ── Idle watchdog ──────────────────────────────────────────────────────────

    async def _idle_watchdog(self) -> None:
        try:
            last_nudge_at = 0.0
            while True:
                await asyncio.sleep(1.0)
                if self._transitioning or not self._holds_lock:
                    break
                if self._agent_busy or self._processing:
                    self._silence_since = time.time()
                    last_nudge_at = time.time()
                    continue

                silent_for       = time.time() - self._silence_since
                time_since_nudge = (time.time() - last_nudge_at) if last_nudge_at else silent_for

                logger.info(
                    f"[{self.__class__.__name__}/idle] "
                    f"silent={silent_for:.1f}s "
                    f"q1={self._q1_answered} q2={self._q2_answered} "
                    f"busy={self._agent_busy} processing={self._processing}"
                )

                if not self._q1_answered:
                    if silent_for >= Q1_SKIP_TIMEOUT:
                        logger.info(f"[{self.__class__.__name__}] Q1 40s — re-asking")
                        await self.session.say(self.REASK_Q1, allow_interruptions=True)
                        # Reset silence clock AFTER re-asking question
                        self._silence_since = last_nudge_at = time.time()
                    elif silent_for >= IDLE_TIMEOUT and time_since_nudge >= IDLE_TIMEOUT:
                        logger.info(f"[{self.__class__.__name__}] Q1 nudge")
                        await self.session.say(self.NUDGE_Q1, allow_interruptions=True)
                        # Mark nudge time only - don't reset silence clock
                        last_nudge_at = time.time()
                    continue

                if not self._q2_answered:
                    if silent_for >= IDLE_TIMEOUT and time_since_nudge >= IDLE_TIMEOUT:
                        logger.info(f"[{self.__class__.__name__}] Q2 nudge")
                        await self.session.say(self.NUDGE_Q2, allow_interruptions=True)
                        # Mark nudge time only - don't reset silence clock
                        last_nudge_at = time.time()
                    continue

                if silent_for >= IDLE_TIMEOUT:
                    await self._on_both_answered_idle()

        except asyncio.CancelledError:
            pass

    # ── Stage timeout watchdog ─────────────────────────────────────────────────

    async def _stage_timeout_watchdog(self) -> None:
        try:
            await asyncio.sleep(self._stage_timeout)
            if not self._transitioning and self._holds_lock:
                logger.info(f"[{self.__class__.__name__}] stage timeout fired")
                await self._on_stage_timeout()
        except asyncio.CancelledError:
            pass