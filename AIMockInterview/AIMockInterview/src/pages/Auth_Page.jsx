import { useState } from "react";

export default function AuthPage({ onLogin }) {
  const [username, setUsername] = useState("demo");
  const [password, setPassword] = useState("demo");

  function submit(e) {
    e.preventDefault();
    if (typeof onLogin === "function") {
      onLogin({ username });
    }
  }

  return (
    <div style={styles.page}>
      <h1 style={styles.title}>Demo Login</h1>
      <form onSubmit={submit} style={styles.card}>
        <label style={styles.label}>Username</label>
        <input
          style={styles.input}
          value={username}
          onChange={(e) => setUsername(e.target.value)}
        />
        <label style={styles.label}>Password</label>
        <input
          style={styles.input}
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <button style={styles.button} type="submit">
          Login
        </button>
        <div style={styles.hint}>This is a demo. Any credentials work.</div>
      </form>
    </div>
  );
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
  },
  title: {
    color: "white",
    fontSize: 48,
    fontWeight: 800,
    marginBottom: 24,
  },
  card: {
    width: 360,
    background: "rgba(255,255,255,0.08)",
    border: "1px solid rgba(255,255,255,0.18)",
    borderRadius: 14,
    padding: 18,
    color: "white",
    display: "flex",
    flexDirection: "column",
    gap: 10,
    boxShadow: "0 10px 30px rgba(0,0,0,0.4)",
  },
  label: { fontSize: 13, opacity: 0.9 },
  input: {
    padding: "10px 12px",
    borderRadius: 10,
    border: "none",
    outline: "none",
  },
  button: {
    marginTop: 8,
    padding: "12px 14px",
    borderRadius: 10,
    border: "none",
    background: "#4a8cff",
    color: "white",
    fontWeight: 700,
    cursor: "pointer",
  },
  hint: { marginTop: 10, fontSize: 12, opacity: 0.75 },
};
