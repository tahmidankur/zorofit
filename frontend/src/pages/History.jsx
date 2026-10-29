import { useCallback, useEffect, useState } from "react";
import { api } from "../api.js";
import { formatDay, formatKcal, round } from "../format.js";
import MealList from "../components/MealList.jsx";
import MealForm from "../components/MealForm.jsx";
import WorkoutCard from "../components/WorkoutCard.jsx";
import "./History.css";

function groupByDay(meals, workouts) {
  const days = new Map();
  const day = (date) => {
    if (!days.has(date)) days.set(date, { date, meals: [], workouts: [] });
    return days.get(date);
  };
  meals.forEach((meal) => day(meal.local_date).meals.push(meal));
  workouts.forEach((workout) => day(workout.local_date).workouts.push(workout));
  return [...days.values()]
    .sort((a, b) => (a.date < b.date ? 1 : -1))
    .map((group) => ({
      ...group,
      kcal: group.meals.reduce((sum, meal) => sum + meal.kcal, 0),
      protein: group.meals.reduce((sum, meal) => sum + meal.protein_g, 0),
    }));
}

export default function History() {
  const [meals, setMeals] = useState(null);
  const [workouts, setWorkouts] = useState([]);
  const [error, setError] = useState("");
  const [editingId, setEditingId] = useState(null);

  const load = useCallback(() => {
    return Promise.all([api.listMeals(), api.listWorkouts()])
      .then(([mealData, workoutData]) => {
        setMeals(mealData);
        setWorkouts(workoutData);
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
      {meals && meals.length === 0 && workouts.length === 0 && <p className="empty">Nothing logged yet.</p>}
      {meals &&
        groupByDay(meals, workouts).map((day) => (
          <section key={day.date} className="history-day">
            <div className="history-day-head">
              <h2 className="section-title">{formatDay(day.date)}</h2>
              {day.meals.length > 0 && (
                <p className="small muted num">
                  {formatKcal(day.kcal)} · {round(day.protein)} g protein
                </p>
              )}
            </div>
            {day.workouts.map((workout) => (
              <div key={workout.id} className="history-workout">
                <WorkoutCard
                  plan={workout.exercises}
                  title={`${workout.minutes_planned}-minute session`}
                  status={workout.status}
                />
              </div>
            ))}
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
