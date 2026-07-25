import { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";

type Health = { status: string; version: string };

function App() {
  const [health, setHealth] = useState<Health | null>(null);
  useEffect(() => {
    fetch("http://127.0.0.1:8000/api/v1/health")
      .then((response) => response.json())
      .then(setHealth);
  }, []);
  return <main><h1>CareerPilot</h1><p>API: {health?.status ?? "checking"}</p></main>;
}

createRoot(document.getElementById("root")!).render(<App />);

