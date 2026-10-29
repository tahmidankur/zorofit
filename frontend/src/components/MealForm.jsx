import { useState } from "react";
import { Plus, X } from "lucide-react";
import { formatKcal, round, toLocalInputValue } from "../format.js";
import { portionText, scaleFood, unitOptions } from "../nutrition.js";
import FoodSearch from "./FoodSearch.jsx";
import "./MealForm.css";

const LABELS = ["breakfast", "lunch", "dinner", "snack"];

function manualRow() {
  return { food: null, food_name: "", portion_text: "", grams: "", kcal: "", protein_g: "", carbs_g: 0, fat_g: 0 };
}

function withPortion(row, quantity, unitIndex) {
  const option = row.options[unitIndex];
  const grams = Math.round(Number(quantity) * option.gramsEach * 10) / 10;
  const values = scaleFood(row.food, grams || 0);
  return {
    ...row,
    quantity,
    unitIndex,
    grams: String(grams || ""),
    portion_text: quantity ? portionText(quantity, option.unit) : "",
    kcal: String(values.kcal),
    protein_g: String(values.protein_g),
    carbs_g: values.carbs_g,
    fat_g: values.fat_g,
  };
}

function foodRow(food) {
  const options = unitOptions(food);
  const base = {
    food,
    options,
    food_name: food.name,
    fdc_id: food.fdc_id,
    custom_food_id: food.custom_food_id,
  };
  const quantity = options[0].unit === "g" ? "100" : "1";
  return withPortion(base, quantity, 0);
}

function rowFromItem(item) {
  return {
    ...item,
    food: null,
    grams: String(item.grams),
    kcal: String(round(item.kcal)),
    protein_g: String(item.protein_g),
  };
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
    portion_text: (row.portion_text || "").trim(),
    grams: Number(row.grams),
    kcal: Number(row.kcal),
    protein_g: Number(row.protein_g),
    carbs_g: Number(row.carbs_g) || 0,
    fat_g: Number(row.fat_g) || 0,
    fdc_id: row.fdc_id ?? null,
    custom_food_id: row.custom_food_id ?? null,
  };
}

function NumberField({ label, value, onChange, invalid }) {
  return (
    <label className="field">
      <span className="field-label">{label}</span>
      <input
        className="input"
        type="number"
        inputMode="decimal"
        min="0"
        step="any"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        aria-invalid={invalid}
      />
    </label>
  );
}

function ItemRow({ row, index, showErrors, onChange, onRemove }) {
  const removeButton = (
    <button
      type="button"
      className="btn btn-ghost btn-icon"
      onClick={onRemove}
      aria-label={`Remove ${row.food_name || "item"}`}
    >
      <X size={20} aria-hidden="true" />
    </button>
  );
  const numberInvalid = (key) => showErrors && !(key === "grams" ? Number(row[key]) > 0 : row[key] !== "");

  if (row.food) {
    return (
      <li className="meal-form-row">
        <div className="meal-form-row-head">
          <div className="meal-form-food">
            <p className="meal-form-food-name">{row.food.name}</p>
            <p className="small muted">{row.food.category}</p>
          </div>
          {removeButton}
        </div>
        <div className="meal-form-portion">
          <NumberField
            label="Amount"
            value={row.quantity}
            invalid={showErrors && !(Number(row.quantity) > 0)}
            onChange={(value) => onChange(withPortion(row, value, row.unitIndex))}
          />
          <label className="field">
            <span className="field-label">Unit</span>
            <select
              className="input"
              value={row.unitIndex}
              onChange={(e) => {
                const unitIndex = Number(e.target.value);
                const quantity = row.options[unitIndex].unit === "g" ? "100" : "1";
                onChange(withPortion(row, quantity, unitIndex));
              }}
            >
              {row.options.map((option, optionIndex) => (
                <option key={option.unit} value={optionIndex}>
                  {option.unit === "g" ? "grams" : `${option.unit} (${round(option.gramsEach)} g)`}
                </option>
              ))}
            </select>
          </label>
        </div>
        <div className="meal-form-values">
          <NumberField
            label="Grams"
            value={row.grams}
            invalid={numberInvalid("grams")}
            onChange={(value) => onChange(withPortion(row, value, row.options.length - 1))}
          />
          <NumberField label="kcal" value={row.kcal} invalid={numberInvalid("kcal")} onChange={(kcal) => onChange({ ...row, kcal })} />
          <NumberField
            label="Protein g"
            value={row.protein_g}
            invalid={numberInvalid("protein_g")}
            onChange={(protein_g) => onChange({ ...row, protein_g })}
          />
        </div>
      </li>
    );
  }

  return (
    <li className="meal-form-row">
      <div className="meal-form-row-head">
        <label className="field meal-form-name">
          <span className="field-label">Food</span>
          <input
            className="input"
            value={row.food_name}
            onChange={(e) => onChange({ ...row, food_name: e.target.value })}
            aria-invalid={showErrors && row.food_name.trim() === ""}
            placeholder={index === 0 ? "e.g. Chicken curry" : ""}
          />
        </label>
        {removeButton}
      </div>
      <div className="meal-form-numbers">
        <label className="field">
          <span className="field-label">Portion</span>
          <input
            className="input"
            value={row.portion_text}
            onChange={(e) => onChange({ ...row, portion_text: e.target.value })}
            placeholder="1 bowl"
          />
        </label>
        <NumberField label="Grams" value={row.grams} invalid={numberInvalid("grams")} onChange={(grams) => onChange({ ...row, grams })} />
        <NumberField label="kcal" value={row.kcal} invalid={numberInvalid("kcal")} onChange={(kcal) => onChange({ ...row, kcal })} />
        <NumberField
          label="Protein g"
          value={row.protein_g}
          invalid={numberInvalid("protein_g")}
          onChange={(protein_g) => onChange({ ...row, protein_g })}
        />
      </div>
    </li>
  );
}

export default function MealForm({ meal, onSubmit, onCancel, title, initialQuery = "" }) {
  const [label, setLabel] = useState(meal?.label ?? "");
  const [eatenAt, setEatenAt] = useState(toLocalInputValue(meal ? new Date(meal.eaten_at) : new Date()));
  const [rows, setRows] = useState(meal ? meal.items.map(rowFromItem) : []);
  const [searching, setSearching] = useState(!meal);
  const [showErrors, setShowErrors] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  function updateRow(index, next) {
    setRows((current) => current.map((row, i) => (i === index ? next : row)));
  }

  function addRow(row) {
    setRows((current) => [...current, row]);
    setSearching(false);
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

      {rows.length > 0 && (
        <ol className="meal-form-rows">
          {rows.map((row, index) => (
            <ItemRow
              key={index}
              row={row}
              index={index}
              showErrors={showErrors}
              onChange={(next) => updateRow(index, next)}
              onRemove={() => setRows((current) => current.filter((_, i) => i !== index))}
            />
          ))}
        </ol>
      )}

      {searching ? (
        <FoodSearch
          initialQuery={initialQuery}
          autoFocus={!meal}
          onPick={(food) => addRow(foodRow(food))}
          onManual={() => addRow(manualRow())}
        />
      ) : (
        <button type="button" className="btn btn-ghost meal-form-add" onClick={() => setSearching(true)}>
          <Plus size={20} aria-hidden="true" /> Add item
        </button>
      )}

      <div className="meal-form-total num">
        <span>{formatKcal(totalKcal)}</span>
        <span className="muted">{round(totalProtein)} g protein</span>
      </div>

      {showErrors && rows.length === 0 && <p className="error-text">Add at least one item.</p>}
      {showErrors && rows.length > 0 && <p className="error-text">Each item needs a name, grams above 0, kcal, and protein.</p>}
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
