import { useEffect, useRef, useState } from "react";
import { ArrowUp } from "lucide-react";
import { api } from "../api.js";
import MealCard from "../components/MealCard.jsx";
import MealForm from "../components/MealForm.jsx";
import "./Chat.css";

function useOnline() {
  const [online, setOnline] = useState(navigator.onLine);
  useEffect(() => {
    const update = () => setOnline(navigator.onLine);
    window.addEventListener("online", update);
    window.addEventListener("offline", update);
    return () => {
      window.removeEventListener("online", update);
      window.removeEventListener("offline", update);
    };
  }, []);
  return online;
}

function Fallback({ query }) {
  const [state, setState] = useState("open");
  if (state === "saved") return <p className="small muted">Saved.</p>;
  if (state === "closed") return null;
  return (
    <MealForm
      title="Add meal"
      initialQuery={query}
      onSubmit={async (meal) => {
        await api.createMeal(meal);
        setState("saved");
      }}
      onCancel={() => setState("closed")}
    />
  );
}

function Message({ message, showCard, onProposal }) {
  if (message.role === "user") {
    return (
      <li className="chat-row chat-row-user">
        <p className="chat-bubble">{message.text}</p>
      </li>
    );
  }
  return (
    <li className="chat-row chat-row-zoro">
      <p className="chat-zoro-name small">Zoro</p>
      <p className="chat-zoro-text">{message.text}</p>
      {showCard && message.proposal.kind !== "workout" && (
        <MealCard proposal={message.proposal} onUpdate={(proposal) => onProposal(proposal)} />
      )}
      {message.fallback_query && <Fallback query={message.fallback_query} />}
    </li>
  );
}

export default function Chat() {
  const [messages, setMessages] = useState([]);
  const [loaded, setLoaded] = useState(false);
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const online = useOnline();
  const endRef = useRef(null);

  useEffect(() => {
    api
      .chatHistory()
      .then(setMessages)
      .catch(() => setError("Can't reach the server."))
      .finally(() => setLoaded(true));
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [messages.length]);

  function replaceProposal(proposal) {
    setMessages((current) =>
      current.map((message) => (message.proposal?.id === proposal.id ? { ...message, proposal } : message))
    );
  }

  async function send(event) {
    event.preventDefault();
    const message = text.trim();
    if (!message || sending) return;
    setSending(true);
    setError("");
    try {
      const replies = await api.sendChat(message);
      // A reply can change an earlier card: a typed "yes" saves it, a new meal replaces it.
      const updated = new Map(replies.filter((m) => m.proposal).map((m) => [m.proposal.id, m.proposal]));
      const opensMealCard = replies.some((m) => m.proposal?.kind === "meal" && m.proposal.status === "pending");
      setMessages((current) => [
        ...current.map((m) => {
          if (!m.proposal) return m;
          if (updated.has(m.proposal.id)) return { ...m, proposal: updated.get(m.proposal.id) };
          if (opensMealCard && m.proposal.status === "pending" && m.proposal.kind !== "workout") {
            return { ...m, proposal: { ...m.proposal, status: "discarded" } };
          }
          return m;
        }),
        ...replies,
      ]);
      setText("");
    } catch (err) {
      setError(err.status ? err.message : "Couldn't send. Check your connection.");
    } finally {
      setSending(false);
    }
  }

  // "Saved." refers back to a card already on screen; show each card once, where it first appeared.
  const firstCardIndex = new Map();
  messages.forEach((message, index) => {
    if (message.proposal && !firstCardIndex.has(message.proposal.id)) firstCardIndex.set(message.proposal.id, index);
  });

  return (
    <section className="chat">
      <header className="page-header">
        <h1 className="page-title">Chat</h1>
      </header>

      <ol className="chat-log" aria-live="polite">
        {loaded && messages.length === 0 && (
          <li className="chat-row chat-row-zoro">
            <p className="chat-zoro-name small">Zoro</p>
            <p className="chat-zoro-text">
              Tell me what you ate, like “two eggs and 200 g of cooked rice”, and I'll make a card for you to check.
            </p>
          </li>
        )}
        {messages.map((message, index) => (
          <Message
            key={message.id}
            message={message}
            showCard={Boolean(message.proposal) && firstCardIndex.get(message.proposal.id) === index}
            onProposal={replaceProposal}
          />
        ))}
        {sending && (
          <li className="chat-row chat-row-zoro">
            <p className="chat-zoro-name small">Zoro</p>
            <p className="chat-zoro-text muted">Reading…</p>
          </li>
        )}
      </ol>
      <div ref={endRef} className="chat-end" />

      <form className="chat-composer" onSubmit={send}>
        {!online && <p className="chat-offline small">You're offline. Messages will send when you reconnect.</p>}
        {error && <p className="error-text">{error}</p>}
        <div className="chat-input-row">
          <label className="chat-input-label">
            <span className="visually-hidden">Message Zoro</span>
            <textarea
              className="input chat-input"
              rows={1}
              maxLength={1000}
              placeholder="What did you eat?"
              value={text}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) send(e);
              }}
            />
          </label>
          <button
            type="submit"
            className="btn btn-primary btn-icon"
            aria-label="Send"
            disabled={!text.trim() || sending || !online}
          >
            <ArrowUp size={20} aria-hidden="true" />
          </button>
        </div>
        <p className="chat-privacy small muted">
          Messages are processed by Google's Gemini API, so don't include personal health details.
        </p>
      </form>
    </section>
  );
}
