import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { CalendarCheck, ClipboardCheck, MessageSquare } from "lucide-react";
import { api } from "../api.js";
import { round } from "../format.js";
import stacked from "../assets/brand/zorofit-stacked-green.svg";
import "./Home.css";

const STEPS = [
  { Icon: MessageSquare, title: "Tell Zoro", text: "“Two eggs and 200 g of rice” or “I have 30 minutes.”" },
  { Icon: ClipboardCheck, title: "Check the card", text: "Foods, grams, and calories from USDA data. Edit anything." },
  { Icon: CalendarCheck, title: "Track the day", text: "Today adds up calories, protein, and your workout." },
];

function TodaySummary({ today }) {
  const workout = today.workout;
  return (
    <Link to="/today" className="card home-summary">
      <p className="home-summary-label small muted">Today so far</p>
      <div className="home-summary-numbers num">
        <p>
          <span className="home-summary-value">≈ {round(today.totals.kcal)}</span>
          <span className="muted"> / {round(today.targets.kcal)} kcal</span>
        </p>
        <p>
          <span className="home-summary-value">≈ {round(today.totals.protein_g)}</span>
          <span className="muted"> / {round(today.targets.protein_g)} g protein</span>
        </p>
      </div>
      <p className="small muted">
        {workout
          ? `${workout.minutes_planned}-minute workout · ${workout.status === "planned" ? "planned" : workout.status}`
          : "Rest day"}
      </p>
    </Link>
  );
}

export default function Home() {
  const [today, setToday] = useState(null);
  const [hasHistory, setHasHistory] = useState(true);
  const [loadingDemo, setLoadingDemo] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    // Home still works without the API (offline, or the free server waking up); the summary just waits.
    api.getToday().then(setToday).catch(() => setToday(null));
    // An empty today is normal after midnight; only offer sample data to someone who has logged nothing at all.
    api
      .listMeals(1)
      .then((meals) => setHasHistory(meals.length > 0))
      .catch(() => setHasHistory(true));
  }, []);

  async function loadDemo() {
    setLoadingDemo(true);
    try {
      await api.loadDemoData();
      navigate("/today");
    } finally {
      setLoadingDemo(false);
    }
  }

  return (
    <section className="home">
      <div className="home-hero">
        <img src={stacked} alt="ZoroFit" className="home-logo" width="217" height="165" />
        <h1 className="home-title">Log meals and plan workouts by chatting.</h1>
        <p className="home-lead muted">
          Zoro reads what you type. You check the card before anything is saved.
        </p>
        <div className="home-actions">
          <Link to="/today" className="btn btn-primary">
            Open Today
          </Link>
          <Link to="/chat" className="btn">
            <MessageSquare size={20} aria-hidden="true" /> Chat with Zoro
          </Link>
        </div>
      </div>

      {today && <TodaySummary today={today} />}

      <ol className="home-steps">
        {STEPS.map(({ Icon, title, text }) => (
          <li key={title} className="home-step">
            <Icon size={20} aria-hidden="true" className="home-step-icon" />
            <div>
              <p className="home-step-title">{title}</p>
              <p className="small muted">{text}</p>
            </div>
          </li>
        ))}
      </ol>

      {!hasHistory && (
        <div className="home-demo">
          <p className="small muted">Just looking around? Fill the past week with sample meals and workouts.</p>
          <button type="button" className="btn btn-ghost" disabled={loadingDemo} onClick={loadDemo}>
            {loadingDemo ? "Loading…" : "Load a sample week"}
          </button>
        </div>
      )}

      <p className="home-credit small muted">Nutrition data: USDA FoodData Central.</p>
    </section>
  );
}
