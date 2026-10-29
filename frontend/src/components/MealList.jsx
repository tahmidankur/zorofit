import { useState } from "react";
import { Pencil, Trash2 } from "lucide-react";
import { capitalize, formatKcal, formatTime, round } from "../format.js";
import "./MealList.css";

function MealRow({ meal, onEdit, onDelete }) {
  const [confirming, setConfirming] = useState(false);

  return (
    <li className="card meal">
      <div className="meal-head">
        <div>
          <p className="meal-title">{capitalize(meal.label) || "Meal"}</p>
          <p className="small muted num">{formatTime(meal.eaten_at)}</p>
        </div>
        <div className="meal-sum num">
          <p>{formatKcal(meal.kcal)}</p>
          <p className="small muted">{round(meal.protein_g)} g protein</p>
        </div>
      </div>
      <ul className="meal-items">
        {meal.items.map((item) => (
          <li key={item.id} className="meal-item">
            <span className="meal-item-name">
              {item.food_name}
              <span className="muted"> · {item.portion_text || `${round(item.grams)} g`}</span>
            </span>
            <span className="muted num">{round(item.kcal)} kcal</span>
          </li>
        ))}
      </ul>
      {(onEdit || onDelete) && (
        <div className="btn-row meal-actions">
          {onEdit && (
            <button type="button" className="btn btn-ghost" onClick={() => onEdit(meal)}>
              <Pencil size={18} aria-hidden="true" /> Edit
            </button>
          )}
          {onDelete && !confirming && (
            <button type="button" className="btn btn-ghost" onClick={() => setConfirming(true)}>
              <Trash2 size={18} aria-hidden="true" /> Delete
            </button>
          )}
          {onDelete && confirming && (
            <>
              <button type="button" className="btn btn-danger" onClick={() => onDelete(meal)}>
                Delete meal
              </button>
              <button type="button" className="btn" onClick={() => setConfirming(false)}>
                Keep
              </button>
            </>
          )}
        </div>
      )}
    </li>
  );
}

export default function MealList({ meals, onEdit, onDelete, renderEditor, editingId }) {
  return (
    <ul className="meal-list">
      {meals.map((meal) =>
        meal.id === editingId ? (
          <li key={meal.id}>{renderEditor(meal)}</li>
        ) : (
          <MealRow key={meal.id} meal={meal} onEdit={onEdit} onDelete={onDelete} />
        )
      )}
    </ul>
  );
}
