import { useState } from "react";
import { Plus, X } from "lucide-react";
import { formatKcal, round, toLocalInputValue } from "../format.js";
import "./MealForm.css";

const LABELS = ["breakfast", "lunch", "dinner", "snack"];

const NUMBER_FIELDS = [
  { key: "grams", label: "Grams" },
  { key: "kcal", label: "kcal" },
  { key: "protein_g", label: "Protein g" },
];

function emptyRow() {
  return { food_name: "", portion_text: "", grams: "", kcal: "", protein_g: "", carbs_g: 0, fat_g: 0 };
}

function rowFromItem(item) {
  return { ...item, grams: String(item.grams), kcal: String(round(item.kcal)), protein_g: String(item.protein_g) };
}

function rowIsValid(row) {
  return (
    row.food_name.trim() !== "" &&
    Number(row.grams) > 0 &&
    row.kcal !== "" &&
    Number(row.kcal) >= 0 &&
    row.protein_g !== "" &&
    Number(row.protein_g) >= 0
  );
}

function toPayloadItem(row) {
  return {
    food_name: row.food_name.trim(),
    portion_text: row.portion_text.trim(),
    grams: Number(row.grams),
    kcal: Number(row.kcal),
    protein_g: Number(row.protein_g),
    carbs_g: Number(row.carbs_g) || 0,
    fat_g: Number(row.fat_g) || 0,
    fdc_id: row.fdc_id ?? null,
    custom_food_id: row.custom_food_id ?? null,
  };
}

export default function MealForm({ meal, onSubmit, onCancel, title }) {
  const [label, setLabel] = useState(meal?.label ?? "");
  const [eatenAt, setEatenAt] = useState(toLocalInputValue(meal ? new Date(meal.eaten_at) : new Date()));
  const [rows, setRows] = useState(meal ? meal.items.map(rowFromItem) : [emptyRow()]);
  const [showErrors, setShowErrors] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  function updateRow(index, changes) {
    setRows((current) => current.map((row, i) => (i === index ? { ...row, ...changes } : row)));
  }

  function removeRow(index) {
    setRows((current) => current.filter((_, i) => i !== index));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (rows.length === 0 || !rows.every(rowIsValid)) {
      setShowErrors(true);
      return;
    }
    setSaving(true);
    setError("");
    try {
      await onSubmit({
        label: label || null,
        eaten_at: new Date(eatenAt).toISOString(),
        items: rows.map(toPayloadItem),
      });
    } catch (err) {
      setError(err.message);
      setSaving(false);
    }
  }

  const totalKcal = rows.reduce((sum, row) => sum + (Number(row.kcal) || 0), 0);
  const totalProtein = rows.reduce((sum, row) => sum + (Number(row.protein_g) || 0), 0);

  return (
    <form className="card meal-form" onSubmit={handleSubmit} noValidate>
      <h2 className="section-title">{title}</h2>

      <div className="meal-form-meta">
        <label className="field">
          <span className="field-label">Meal</span>
          <select className="input" value={label} onChange={(e) => setLabel(e.target.value)}>
            <option value="">No label</option>
            {LABELS.map((value) => (
              <option key={value} value={value}>
                {value[0].toUpperCase() + value.slice(1)}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span className="field-label">Time</span>
          <input
            className="input"
            type="datetime-local"
            value={eatenAt}
            onChange={(e) => setEatenAt(e.target.value)}
            required
          />
        </label>
      </div>

      <ol className="meal-form-rows">
        {rows.map((row, index) => (
          <li key={index} className="meal-form-row">
            <div className="meal-form-row-head">
              <label className="field meal-form-name">
                <span className="field-label">Food</span>
                <input
                  className="input"
                  value={row.food_name}
                  onChange={(e) => updateRow(index, { food_name: e.target.value })}
                  aria-invalid={showErrors && row.food_name.trim() === ""}
                  placeholder="e.g. Rice, white, cooked"
                />
              </label>
              <button
                type="button"
                className="btn btn-ghost btn-icon"
                onClick={() => removeRow(index)}
                aria-label={`Remove ${row.food_name || "item"}`}
              >
                <X size={20} aria-hidden="true" />
              </button>
            </div>
            <div className="meal-form-numbers">
              <label className="field">
                <span className="field-label">Portion</span>
                <input
                  className="input"
                  value={row.portion_text}
                  onChange={(e) => updateRow(index, { portion_text: e.target.value })}
                  placeholder="1 cup"
                />
              </label>
              {NUMBER_FIELDS.map(({ key, label: fieldLabel }) => (
                <label key={key} className="field">
                  <span className="field-label">{fieldLabel}</span>
                  <input
                    className="input"
                    type="number"
                    inputMode="decimal"
                    min="0"
                    step="any"
                    value={row[key]}
                    onChange={(e) => updateRow(index, { [key]: e.target.value })}
                    aria-invalid={showErrors && !(key === "grams" ? Number(row[key]) > 0 : row[key] !== "")}
                  />
                </label>
              ))}
            </div>
          </li>
        ))}
      </ol>

      <button type="button" className="btn btn-ghost meal-form-add" onClick={() => setRows([...rows, emptyRow()])}>
        <Plus size={20} aria-hidden="true" /> Add item
      </button>

      <div className="meal-form-total num">
        <span>{formatKcal(totalKcal)}</span>
        <span className="muted">{round(totalProtein)} g protein</span>
      </div>

      {showErrors && <p className="error-text">Each item needs a name, grams above 0, kcal, and protein.</p>}
      {error && <p className="error-text">{error}</p>}

      <div className="btn-row">
        <button type="submit" className="btn btn-primary" disabled={saving}>
          {saving ? "Saving…" : "Save meal"}
        </button>
        <button type="button" className="btn" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  );
}
