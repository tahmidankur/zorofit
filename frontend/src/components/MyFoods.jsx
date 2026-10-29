import { useEffect, useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { api } from "../api.js";
import { round } from "../format.js";
import CustomFoodForm from "./CustomFoodForm.jsx";
import "./MyFoods.css";

export default function MyFoods() {
  const [foods, setFoods] = useState([]);
  const [adding, setAdding] = useState(false);

  function load() {
    api.listCustomFoods().then(setFoods).catch(() => setFoods([]));
  }

  useEffect(load, []);

  async function remove(food) {
    await api.deleteCustomFood(food.id);
    load();
  }

  return (
    <div className="card stack">
      <div className="section-header my-foods-head">
        <h2 className="section-title">My foods</h2>
        {!adding && (
          <button type="button" className="btn btn-ghost" onClick={() => setAdding(true)}>
            <Plus size={20} aria-hidden="true" /> Add food
          </button>
        )}
      </div>
      <p className="small muted">For home-cooked and regional dishes the USDA list doesn't have.</p>
      {adding && (
        <CustomFoodForm
          onSaved={() => {
            setAdding(false);
            load();
          }}
          onCancel={() => setAdding(false)}
        />
      )}
      {foods.length > 0 && (
        <ul className="my-foods">
          {foods.map((food) => (
            <li key={food.id} className="my-food">
              <div>
                <p>{food.name}</p>
                <p className="small muted num">
                  {round(food.kcal_100g)} kcal · {round(food.protein_100g)} g protein per 100 g
                  {food.serving_name && ` · 1 ${food.serving_name} = ${round(food.serving_grams)} g`}
                </p>
              </div>
              <button
                type="button"
                className="btn btn-ghost btn-icon"
                aria-label={`Delete ${food.name}`}
                onClick={() => remove(food)}
              >
                <Trash2 size={20} aria-hidden="true" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
