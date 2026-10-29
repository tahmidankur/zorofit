import { useCallback, useEffect, useState } from "react";
import { Plus } from "lucide-react";
import { api } from "../api.js";
import { formatDay } from "../format.js";
import ProgressBar from "../components/ProgressBar.jsx";
import MealList from "../components/MealList.jsx";
import MealForm from "../components/MealForm.jsx";

export default function Today() {
  const [today, setToday] = useState(null);
  const [error, setError] = useState("");
  const [adding, setAdding] = useState(false);
  const [editingId, setEditingId] = useState(null);

  const load = useCallback(() => {
    return api
      .getToday()
      .then((data) => {
        setToday(data);
        setError("");
      })
      .catch(() => setError("Can't reach the server."));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function addMeal(meal) {
    await api.createMeal(meal);
    setAdding(false);
    await load();
  }

  async function saveEdit(id, meal) {
    await api.updateMeal(id, meal);
    setEditingId(null);
    await load();
  }

  async function deleteMeal(meal) {
    await api.deleteMeal(meal.id);
    await load();
  }

  if (error && !today) {
    return (
      <section>
        <header className="page-header">
          <h1 className="page-title">Today</h1>
        </header>
        <p className="empty">{error}</p>
      </section>
    );
  }

  if (!today) {
    return (
      <section>
        <header className="page-header">
          <h1 className="page-title">Today</h1>
          <p className="page-subtitle">Loading…</p>
        </header>
      </section>
    );
  }

  return (
    <section>
      <header className="page-header">
        <h1 className="page-title">Today</h1>
        <p className="page-subtitle">{formatDay(today.date)}</p>
      </header>

      <div className="card">
        <ProgressBar label="Calories" value={today.totals.kcal} target={today.targets.kcal} unit="kcal" />
        <ProgressBar label="Protein" value={today.totals.protein_g} target={today.targets.protein_g} unit="g" />
      </div>

      <div className="section">
        <div className="section-header">
          <h2 className="section-title">Meals</h2>
          {!adding && (
            <button type="button" className="btn btn-ghost" onClick={() => setAdding(true)}>
              <Plus size={20} aria-hidden="true" /> Add meal
            </button>
          )}
        </div>
        <div className="stack">
          {adding && <MealForm title="Add meal" onSubmit={addMeal} onCancel={() => setAdding(false)} />}
          {today.meals.length === 0 && !adding && <p className="empty">No meals logged yet.</p>}
          <MealList
            meals={today.meals}
            editingId={editingId}
            onEdit={(meal) => setEditingId(meal.id)}
            onDelete={deleteMeal}
            renderEditor={(meal) => (
              <MealForm
                title="Edit meal"
                meal={meal}
                onSubmit={(body) => saveEdit(meal.id, body)}
                onCancel={() => setEditingId(null)}
              />
            )}
          />
        </div>
      </div>
    </section>
  );
}
