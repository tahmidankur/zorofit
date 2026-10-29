import { useCallback, useEffect, useState } from "react";
import { api } from "../api.js";
import { formatDay, formatKcal, round } from "../format.js";
import MealList from "../components/MealList.jsx";
import MealForm from "../components/MealForm.jsx";
import "./History.css";

function groupByDay(meals) {
  const days = new Map();
  for (const meal of meals) {
    if (!days.has(meal.local_date)) days.set(meal.local_date, []);
    days.get(meal.local_date).push(meal);
  }
  return [...days.entries()].map(([date, dayMeals]) => ({
    date,
    meals: dayMeals,
    kcal: dayMeals.reduce((sum, meal) => sum + meal.kcal, 0),
    protein: dayMeals.reduce((sum, meal) => sum + meal.protein_g, 0),
  }));
}

export default function History() {
  const [meals, setMeals] = useState(null);
  const [error, setError] = useState("");
  const [editingId, setEditingId] = useState(null);

  const load = useCallback(() => {
    return api
      .listMeals()
      .then((data) => {
        setMeals(data);
        setError("");
      })
      .catch(() => setError("Can't reach the server."));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function saveEdit(id, meal) {
    await api.updateMeal(id, meal);
    setEditingId(null);
    await load();
  }

  async function deleteMeal(meal) {
    await api.deleteMeal(meal.id);
    await load();
  }

  return (
    <section>
      <header className="page-header">
        <h1 className="page-title">History</h1>
      </header>
      {error && <p className="empty">{error}</p>}
      {meals && meals.length === 0 && <p className="empty">Nothing logged yet.</p>}
      {meals &&
        groupByDay(meals).map((day) => (
          <section key={day.date} className="history-day">
            <div className="history-day-head">
              <h2 className="section-title">{formatDay(day.date)}</h2>
              <p className="small muted num">
                {formatKcal(day.kcal)} · {round(day.protein)} g protein
              </p>
            </div>
            <MealList
              meals={day.meals}
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
          </section>
        ))}
    </section>
  );
}
