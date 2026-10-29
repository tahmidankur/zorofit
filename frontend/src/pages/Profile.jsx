import { useEffect, useState } from "react";
import { api, browserTimezone } from "../api.js";
import Chips from "../components/Chips.jsx";
import MyFoods from "../components/MyFoods.jsx";
import "./Profile.css";

const GOALS = [
  { value: "lose", label: "Lose fat" },
  { value: "maintain", label: "Maintain" },
  { value: "gain", label: "Gain muscle" },
  { value: "strength", label: "Strength" },
];

const DIET_PREFS = [
  { value: "vegetarian", label: "Vegetarian" },
  { value: "vegan", label: "Vegan" },
  { value: "pescatarian", label: "Pescatarian" },
  { value: "halal", label: "Halal" },
  { value: "dairy_free", label: "Dairy-free" },
  { value: "gluten_free", label: "Gluten-free" },
];

const EQUIPMENT = [
  { value: "dumbbells", label: "Dumbbells" },
  { value: "barbell", label: "Barbell" },
  { value: "rack", label: "Squat rack" },
  { value: "bench", label: "Bench" },
  { value: "kettlebell", label: "Kettlebell" },
  { value: "pull_up_bar", label: "Pull-up bar" },
  { value: "bands", label: "Bands" },
  { value: "cable", label: "Cable" },
  { value: "machines", label: "Machines" },
];

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((label, value) => ({
  value,
  label: label[0],
  ariaLabel: label,
}));

const LIMITS = {
  calorie_target: [1200, 5000],
  protein_target_g: [30, 300],
  session_minutes: [15, 90],
};

function rangeError(form) {
  for (const [field, [min, max]] of Object.entries(LIMITS)) {
    const value = Number(form[field]);
    if (!Number.isInteger(value) || value < min || value > max) return field;
  }
  return null;
}

export default function Profile() {
  const [form, setForm] = useState(null);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const timezone = browserTimezone();

  useEffect(() => {
    api
      .getProfile()
      .then(setForm)
      .catch(() => setError("Can't reach the server."));
  }, []);

  function update(changes) {
    setForm((current) => ({ ...current, ...changes }));
    setStatus("");
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (rangeError(form)) {
      setError("Check the highlighted values.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      const saved = await api.saveProfile({
        ...form,
        calorie_target: Number(form.calorie_target),
        protein_target_g: Number(form.protein_target_g),
        session_minutes: Number(form.session_minutes),
        timezone,
      });
      setForm(saved);
      setStatus("Saved.");
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  if (!form) {
    return (
      <section>
        <header className="page-header">
          <h1 className="page-title">Profile</h1>
          {error ? <p className="empty">{error}</p> : <p className="page-subtitle">Loading…</p>}
        </header>
      </section>
    );
  }

  const invalid = rangeError(form);

  return (
    <section>
      <header className="page-header">
        <h1 className="page-title">Profile</h1>
      </header>

      <form className="profile-form" onSubmit={handleSubmit} noValidate>
        <div className="card stack">
          <label className="field">
            <span className="field-label">Name</span>
            <input
              className="input"
              value={form.display_name}
              maxLength={60}
              onChange={(e) => update({ display_name: e.target.value })}
            />
          </label>
          <div className="field">
            <span className="field-label">Goal</span>
            <div className="chips" role="radiogroup" aria-label="Goal">
              {GOALS.map((goal) => (
                <button
                  key={goal.value}
                  type="button"
                  className="chip"
                  role="radio"
                  aria-checked={form.goal === goal.value}
                  aria-pressed={form.goal === goal.value}
                  onClick={() => update({ goal: goal.value })}
                >
                  {goal.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="card stack">
          <h2 className="section-title">Daily targets</h2>
          <div className="profile-pair">
            <label className="field">
              <span className="field-label">Calories (1,200–5,000)</span>
              <input
                className="input"
                type="number"
                inputMode="numeric"
                min="1200"
                max="5000"
                value={form.calorie_target}
                aria-invalid={invalid === "calorie_target"}
                onChange={(e) => update({ calorie_target: e.target.value })}
              />
            </label>
            <label className="field">
              <span className="field-label">Protein g (30–300)</span>
              <input
                className="input"
                type="number"
                inputMode="numeric"
                min="30"
                max="300"
                value={form.protein_target_g}
                aria-invalid={invalid === "protein_target_g"}
                onChange={(e) => update({ protein_target_g: e.target.value })}
              />
            </label>
          </div>
          <div className="field">
            <span className="field-label">Diet</span>
            <Chips
              label="Diet"
              options={DIET_PREFS}
              selected={form.diet_prefs}
              onChange={(diet_prefs) => update({ diet_prefs })}
            />
          </div>
        </div>

        <div className="card stack">
          <h2 className="section-title">Training</h2>
          <div className="field">
            <span className="field-label">Training days</span>
            <Chips
              label="Training days"
              className="chips profile-days"
              options={DAYS}
              selected={form.training_days}
              onChange={(days) => update({ training_days: [...days].sort() })}
            />
          </div>
          <label className="field profile-minutes">
            <span className="field-label">Usual session, minutes (15–90)</span>
            <input
              className="input"
              type="number"
              inputMode="numeric"
              min="15"
              max="90"
              step="5"
              value={form.session_minutes}
              aria-invalid={invalid === "session_minutes"}
              onChange={(e) => update({ session_minutes: e.target.value })}
            />
          </label>
          <div className="field">
            <span className="field-label">Equipment (bodyweight is always included)</span>
            <Chips
              label="Equipment"
              options={EQUIPMENT}
              selected={form.equipment}
              onChange={(equipment) => update({ equipment })}
            />
          </div>
        </div>

        <p className="small muted">Time zone: {timezone}, from this browser.</p>

        {error && <p className="error-text">{error}</p>}
        <div className="btn-row profile-actions">
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? "Saving…" : "Save profile"}
          </button>
          <span className="muted" role="status">
            {status}
          </span>
        </div>
      </form>

      <div className="section">
        <MyFoods />
      </div>
    </section>
  );
}
