import { useState } from "react";
import { api } from "../api.js";
import "./CustomFoodForm.css";

const NUMBER_FIELDS = [
  { key: "kcal_100g", label: "kcal per 100 g", required: true, max: 900 },
  { key: "protein_100g", label: "Protein g per 100 g", required: true, max: 100 },
  { key: "carbs_100g", label: "Carbs g per 100 g", max: 100 },
  { key: "fat_100g", label: "Fat g per 100 g", max: 100 },
];

function emptyForm(name) {
  return { name, kcal_100g: "", protein_100g: "", carbs_100g: "", fat_100g: "", serving_name: "", serving_grams: "" };
}

function validate(form) {
  if (!form.name.trim()) return "Give the food a name.";
  for (const field of NUMBER_FIELDS) {
    const value = form[field.key];
    if (field.required && value === "") return `${field.label} is required.`;
    if (value !== "" && (Number(value) < 0 || Number(value) > field.max)) return `${field.label} must be 0 to ${field.max}.`;
  }
  if (Boolean(form.serving_name.trim()) !== Boolean(form.serving_grams)) {
    return "Give both a serving name and its grams, or leave both empty.";
  }
  return "";
}

export default function CustomFoodForm({ initialName = "", onSaved, onCancel }) {
  const [form, setForm] = useState(emptyForm(initialName));
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  function update(changes) {
    setForm((current) => ({ ...current, ...changes }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    event.stopPropagation();
    const problem = validate(form);
    if (problem) {
      setError(problem);
      return;
    }
    setSaving(true);
    try {
      const saved = await api.createCustomFood({
        name: form.name.trim(),
        kcal_100g: Number(form.kcal_100g),
        protein_100g: Number(form.protein_100g),
        carbs_100g: Number(form.carbs_100g) || 0,
        fat_100g: Number(form.fat_100g) || 0,
        serving_name: form.serving_name.trim() || null,
        serving_grams: form.serving_grams ? Number(form.serving_grams) : null,
      });
      onSaved(saved);
    } catch (err) {
      setError(err.message);
      setSaving(false);
    }
  }

  return (
    <div className="custom-food" role="group" aria-label="Add your own food">
      <p className="custom-food-title">Add your own food</p>
      <p className="small muted">Values per 100 g, from a label or recipe.</p>
      <label className="field">
        <span className="field-label">Name</span>
        <input className="input" value={form.name} maxLength={120} onChange={(e) => update({ name: e.target.value })} />
      </label>
      <div className="custom-food-grid">
        {NUMBER_FIELDS.map((field) => (
          <label key={field.key} className="field">
            <span className="field-label">{field.label}</span>
            <input
              className="input"
              type="number"
              inputMode="decimal"
              min="0"
              step="any"
              value={form[field.key]}
              onChange={(e) => update({ [field.key]: e.target.value })}
            />
          </label>
        ))}
        <label className="field">
          <span className="field-label">Serving name (optional)</span>
          <input
            className="input"
            value={form.serving_name}
            maxLength={40}
            placeholder="plate"
            onChange={(e) => update({ serving_name: e.target.value })}
          />
        </label>
        <label className="field">
          <span className="field-label">Serving grams</span>
          <input
            className="input"
            type="number"
            inputMode="decimal"
            min="0"
            step="any"
            value={form.serving_grams}
            onChange={(e) => update({ serving_grams: e.target.value })}
          />
        </label>
      </div>
      {error && <p className="error-text">{error}</p>}
      <div className="btn-row">
        <button type="button" className="btn btn-primary" disabled={saving} onClick={handleSubmit}>
          {saving ? "Saving…" : "Save food"}
        </button>
        <button type="button" className="btn" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </div>
  );
}
