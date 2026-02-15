import { useState } from "react";
import AuthPage from "./pages/Auth_Page";
import InterviewRoom from "./pages/Stage_Intro";

export default function App() {
  const [stage, setStage] = useState("login");

  if (stage === "login")     return <AuthPage onLogin={() => setStage("interview")} />;
  if (stage === "interview") return <InterviewRoom onDone={() => setStage("done")} />;

  if (stage === "done") {
    return (
      <div style={styles.page}>
        <div style={styles.checkmark}>✓</div>
        <h2 style={styles.title}>Interview Complete</h2>
        <p style={styles.sub}>
          Thank you for completing the mock interview.<br />
          Best of luck — we'll be in touch soon!
        </p>
      </div>
    );
  }

  return null;
}

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
    textAlign: "center",
  },
  checkmark: {
    width: 72,
    height: 72,
    borderRadius: "50%",
    background: "#4ade80",
    color: "white",
    fontSize: 36,
    fontWeight: 800,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 24,
    boxShadow: "0 8px 24px rgba(74,222,128,0.4)",
  },
  title: { color: "white", fontSize: 42, fontWeight: 800, marginBottom: 12 },
  sub:   { color: "rgba(255,255,255,0.75)", fontSize: 18, lineHeight: 1.7 },
};