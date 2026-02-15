import { useEffect, useRef, useState } from "react";
import { Room, RoomEvent, createLocalAudioTrack } from "livekit-client";

const LIVEKIT_URL    = "ws://127.0.0.1:7880";
const TOKEN_ENDPOINT = "http://127.0.0.1:8000/livekit/token";

const STAGE_CONFIG = {
  intro: {
    label:    "Stage 1: Intro",
    duration: 60,
    hint:     "Answer both intro questions naturally. The agent will guide you.",
  },
  experience: {
    label:    "Stage 2: Experience",
    duration: 180,
    hint:     "Answer both experience questions naturally. The agent will guide you.",
  },
};

export default function InterviewRoom({ onDone }) {
  const [inCall,    setInCall]    = useState(false);
  const [status,    setStatus]    = useState("idle");
  const [roomName,  setRoomName]  = useState(null);
  const [stage,     setStage]     = useState("intro");
  const [timeLeft,  setTimeLeft]  = useState(STAGE_CONFIG.intro.duration);

  const roomRef           = useRef(null);
  const micTrackRef       = useRef(null);
  const audioContainerRef = useRef(null);
  const startLockRef      = useRef(false);
  const timerIntervalRef  = useRef(null);
  const stageRef          = useRef("intro");

  // ── Timer ──────────────────────────────────────────────────────────────────

  function timerReset(newStage) {
    console.log(`[timerReset] CALLED - resetting timer for stage: ${newStage}`);
    
    // Stop old timer completely
    if (timerIntervalRef.current) {
      clearInterval(timerIntervalRef.current);
      timerIntervalRef.current = null;
      console.log("[timerReset] old timer cleared");
    }
    
    // Update stage state
    console.log(`[timerReset] updating stage from ${stageRef.current} to ${newStage}`);
    stageRef.current = newStage;
    setStage(newStage);
    
    // Get new duration
    const duration = STAGE_CONFIG[newStage].duration;
    console.log(`[timerReset] target duration: ${duration} seconds (${Math.floor(duration/60)}:${(duration%60).toString().padStart(2,'0')})`);
    
    // Set time and start interval together
    console.log("[timerReset] setting timeLeft and starting new timer");
    setTimeLeft(duration);  // Set the display to full duration
    
    timerIntervalRef.current = setInterval(() => {
      setTimeLeft(prev => {
        const newTime = prev <= 1 ? 0 : prev - 1;
        if (newTime === 0 && timerIntervalRef.current) {
          clearInterval(timerIntervalRef.current);
          timerIntervalRef.current = null;
          console.log("[timerReset] timer reached 0, stopped");
        }
        return newTime;
      });
    }, 1000);
    
    console.log(`[timerReset] COMPLETE - timer should now show ${duration}s and be counting down`);
  }

  function startTimer(stageName) {
    if (timerIntervalRef.current) clearInterval(timerIntervalRef.current);
    const duration = STAGE_CONFIG[stageName].duration;
    setTimeLeft(duration);
    timerIntervalRef.current = setInterval(() => {
      setTimeLeft(prev => {
        if (prev <= 1) {
          clearInterval(timerIntervalRef.current);
          timerIntervalRef.current = null;
          // Timer hit 0 — check if we need to reset for next stage
          handleTimerExpired(stageName);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  }

  function handleTimerExpired(currentStage) {
    console.log(`[handleTimerExpired] *** TIMER HIT 0 *** for stage: ${currentStage}`);
    console.log(`[handleTimerExpired] current stageRef.current: ${stageRef.current}`);
    console.log(`[handleTimerExpired] current stage state: ${stage}`);
    
    if (currentStage === "intro") {
      console.log("[handleTimerExpired] *** INTRO TIMER EXPIRED - RESETTING TO EXPERIENCE ***");
      timerReset("experience");
      console.log("[handleTimerExpired] timerReset called");
    } else {
      console.log(`[handleTimerExpired] ${currentStage} timer expired - no action needed`);
    }
  }

  function stopTimer() {
    if (timerIntervalRef.current) {
      clearInterval(timerIntervalRef.current);
      timerIntervalRef.current = null;
    }
  }

  function formatTime(secs) {
    const m = Math.floor(secs / 60).toString().padStart(2, "0");
    const s = (secs % 60).toString().padStart(2, "0");
    return `${m}:${s}`;
  }

  // ── Start call ─────────────────────────────────────────────────────────────

  async function startCall() {
    if (startLockRef.current) return;
    startLockRef.current = true;
    setStatus("connecting");

    const room     = `interview-${crypto.randomUUID().slice(0, 8)}`;
    const identity = `user-${crypto.randomUUID().slice(0, 8)}`;
    setRoomName(room);

    let token;
    try {
      const resp = await fetch(TOKEN_ENDPOINT, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ room, identity }),
      });
      if (!resp.ok) { setStatus("error"); startLockRef.current = false; return; }
      token = (await resp.json()).token;
    } catch {
      setStatus("error"); startLockRef.current = false; return;
    }

    const lkRoom = new Room();
    roomRef.current = lkRoom;

    // Agent audio
    lkRoom.on(RoomEvent.TrackSubscribed, (track, _pub, participant) => {
      if (track.kind !== "audio") return;
      console.log("[room] agent audio from", participant?.identity);
      const el = track.attach();
      el.autoplay    = true;
      el.playsInline = true;
      audioContainerRef.current?.replaceChildren(el);
      el.play().catch(e => console.warn("[room] play blocked", e));
    });

    // Data messages from agent
    lkRoom.on(RoomEvent.DataReceived, (payload) => {
      try {
        const msg = JSON.parse(new TextDecoder().decode(payload));
        console.log("[room] data received:", msg);

        // Agent handed off to experience stage — reset timer + update UI
        if (msg.event === "stage_changed" && msg.stage === "experience") {
          console.log("[room] *** HANDOFF TO EXPERIENCE STAGE ***");
          console.log("[room] calling timerReset('experience')");
          timerReset("experience");
        }

        // Interview fully complete
        if (msg.event === "interview_complete") {
          console.log("[room] interview complete");
          stopTimer();
          handleDone();
        }

      } catch {}
    });

    try {
      await lkRoom.connect(LIVEKIT_URL, token);
      const mic = await createLocalAudioTrack();
      micTrackRef.current = mic;
      await lkRoom.localParticipant.publishTrack(mic);
      setInCall(true);
      setStatus("live");
      startTimer("intro");
    } catch (e) {
      console.error("[room] connect failed", e);
      setStatus("error");
      startLockRef.current = false;
    }
  }

  // ── End call ───────────────────────────────────────────────────────────────

  async function handleDone() {
    stopTimer();
    setStatus("ended");
    try { micTrackRef.current?.stop(); } catch {}
    micTrackRef.current = null;
    try { await roomRef.current?.disconnect(); } catch {}
    roomRef.current = null;
    setInCall(false);
    setRoomName(null);
    startLockRef.current = false;
    if (typeof onDone === "function") onDone();
  }

  // ── Cleanup ────────────────────────────────────────────────────────────────

  useEffect(() => {
    return () => {
      stopTimer();
      try { micTrackRef.current?.stop(); } catch {}
      try { roomRef.current?.disconnect(); } catch {}
    };
  }, []);

  // ── Timer colour ───────────────────────────────────────────────────────────

  const config = STAGE_CONFIG[stage];
  const timerColor =
    timeLeft > config.duration * 0.5 ? "#4ade80" :
    timeLeft > config.duration * 0.2 ? "#facc15" : "#f87171";

  // ── Pre-call screen ────────────────────────────────────────────────────────

  if (!inCall) {
    return (
      <div style={styles.page}>
        <h1 style={styles.title}>Mock Interview</h1>
        <p style={styles.subtitle}>
          You'll go through two stages — an intro and an experience section.<br />
          Stay connected the whole time. The agent will guide you through both.
        </p>
        <button
          style={styles.button}
          onClick={startCall}
          disabled={status !== "idle"}
        >
          {status === "idle" ? "Start Interview" : "Connecting..."}
        </button>
        {status === "error" && (
          <p style={styles.error}>
            Failed to connect. Check LiveKit server, backend, and mic permissions.
          </p>
        )}
      </div>
    );
  }

  // ── In-call screen ─────────────────────────────────────────────────────────

  return (
    <div style={styles.callPage}>

      {/* Timer — top right */}
      <div style={{ ...styles.timer, color: timerColor }}>
        ⏱ {formatTime(timeLeft)}
      </div>

      <div style={styles.callInfo}>
        <div style={styles.liveBadge}>● LIVE</div>
        <div style={styles.stageLabel}>{config.label}</div>
        <div style={styles.roomText}>Room: {roomName}</div>
        <div style={styles.hint}>{config.hint}</div>
      </div>

      <div ref={audioContainerRef} />

      <button style={styles.endCallBtn} onClick={handleDone}>
        ⛔ End Call
      </button>
    </div>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────

const styles = {
  page: {
    minHeight: "100vh",
    background: "linear-gradient(135deg, #0a1a3a, #112b5c)",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    fontFamily: "Arial, sans-serif",
    padding: 24,
  },
  title: {
    color: "white",
    fontSize: 52,
    fontWeight: 800,
    marginBottom: 16,
    letterSpacing: 2,
  },
  subtitle: {
    color: "rgba(255,255,255,0.75)",
    fontSize: 16,
    marginBottom: 32,
    textAlign: "center",
    maxWidth: 460,
    lineHeight: 1.7,
  },
  button: {
    padding: "14px 40px",
    fontSize: 18,
    fontWeight: 700,
    borderRadius: 10,
    border: "none",
    background: "#4a8cff",
    color: "white",
    cursor: "pointer",
    boxShadow: "0 8px 20px rgba(0,0,0,0.4)",
  },
  error: { color: "salmon", marginTop: 16, textAlign: "center" },
  callPage: {
    minHeight: "100vh",
    background: "linear-gradient(135deg, #0a1a3a, #112b5c)",
    padding: 24,
    fontFamily: "Arial, sans-serif",
    boxSizing: "border-box",
    position: "relative",
  },
  timer: {
    position: "fixed",
    top: 20,
    right: 28,
    fontSize: 26,
    fontWeight: 800,
    fontVariantNumeric: "tabular-nums",
    letterSpacing: 1,
    textShadow: "0 2px 8px rgba(0,0,0,0.5)",
  },
  callInfo: {
    marginTop: 60,
    color: "white",
    display: "flex",
    flexDirection: "column",
    gap: 8,
  },
  liveBadge: {
    display: "inline-block",
    background: "#ff3b30",
    color: "white",
    fontSize: 12,
    fontWeight: 800,
    padding: "4px 10px",
    borderRadius: 999,
    width: "fit-content",
    letterSpacing: 1,
  },
  stageLabel: {
    color: "white",
    fontSize: 20,
    fontWeight: 700,
    marginTop: 4,
  },
  roomText: { fontSize: 13, opacity: 0.6 },
  hint: { marginTop: 8, fontSize: 15, opacity: 0.8, maxWidth: 420, lineHeight: 1.6 },
  endCallBtn: {
    position: "fixed",
    left: "50%",
    bottom: 28,
    transform: "translateX(-50%)",
    background: "#ff3b30",
    color: "white",
    border: "none",
    borderRadius: 999,
    padding: "14px 28px",
    fontWeight: 800,
    fontSize: 15,
    cursor: "pointer",
    boxShadow: "0 10px 28px rgba(0,0,0,0.45)",
  },
};