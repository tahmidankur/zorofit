import { useState } from "react";
import { X } from "lucide-react";
import { api } from "../api.js";
import { capitalize, formatKcal, formatTime, round } from "../format.js";
import FoodSearch from "./FoodSearch.jsx";
import "./MealCard.css";

const LABELS = ["breakfast", "lunch", "dinner", "snack"];

function chipPortionText(choice) {
  return choice.unit === "g" ? `${choice.quantity} g` : `${choice.quantity} ${choice.unit}`;
}

function title(proposal) {
  if (proposal.kind === "meal_edit") return "Edit last meal";
  return proposal.label ? `${capitalize(proposal.label)} estimate` : "Meal estimate";
}

function FoodPicker({ item, disabled, onPick }) {
  if (item.alternatives.length === 0) {
    return <p className="meal-card-food">{item.food_name}</p>;
  }
  return (
    <select
      className="input meal-card-select"
      value={item.unmatched ? "" : item.key}
      disabled={disabled}
      aria-label={`Food for ${item.query}`}
      onChange={(e) => e.target.value && onPick(e.target.value)}
    >
      {item.unmatched ? (
        <option value="">Pick a match for “{item.query}”</option>
      ) : (
        <option value={item.key}>{item.food_name}</option>
      )}
      {item.alternatives.map((alt) => (
        <option key={alt.key} value={alt.key}>
          {alt.name}
        </option>
      ))}
    </select>
  );
}

function ItemRow({ item, pending, editing, draft, onDraft, onChange, onRemove }) {
  const [grams, setGrams] = useState("");
  const [searching, setSearching] = useState(false);

  return (
    <li className="meal-card-item">
      <div className="meal-card-item-head">
        <div className="meal-card-item-main">
          <FoodPicker item={item} disabled={!pending} onPick={(key) => onChange({ key })} />
          {!item.needs_portion && (
            <p className="small muted num">
              {item.portion_text === `${round(item.grams)} g` ? item.portion_text : `${item.portion_text} · ${round(item.grams)} g`}
            </p>
          )}
        </div>
        {!item.needs_portion && (
          <div className="meal-card-item-values num">
            <p>{formatKcal(item.kcal)}</p>
            <p className="small muted">{round(item.protein_g)} g protein</p>
          </div>
        )}
        {editing && (
          <button type="button" className="btn btn-ghost btn-icon" aria-label={`Remove ${item.food_name}`} onClick={onRemove}>
            <X size={20} aria-hidden="true" />
          </button>
        )}
      </div>

      {pending && item.unmatched && (
        <div className="meal-card-unmatched">
          {searching ? (
            <FoodSearch initialQuery={item.query} onPick={(food) => onChange({ key: food.key })} />
          ) : (
            <button type="button" className="btn btn-ghost" onClick={() => setSearching(true)}>
              Search foods
            </button>
          )}
        </div>
      )}

      {pending && item.needs_portion && !item.unmatched && (
        <div className="meal-card-portion">
          <p className="small muted">How much?</p>
          <div className="chips">
            {item.portion_choices.map((choice) => (
              <button
                key={choice.label}
                type="button"
                className="chip"
                onClick={() => onChange({ grams: choice.grams, portion_text: chipPortionText(choice) })}
              >
                {choice.label}
              </button>
            ))}
          </div>
          <form
            className="meal-card-grams"
            onSubmit={(e) => {
              e.preventDefault();
              if (Number(grams) > 0) onChange({ grams: Number(grams) });
            }}
          >
            <input
              className="input"
              type="number"
              inputMode="decimal"
              min="0"
              step="any"
              placeholder="Grams"
              aria-label={`Grams of ${item.query}`}
              value={grams}
              onChange={(e) => setGrams(e.target.value)}
            />
            <button type="submit" className="btn">
              Set
            </button>
          </form>
        </div>
      )}

      {editing && !item.needs_portion && (
        <div className="meal-card-edit">
          {[
            ["grams", "Grams"],
            ["kcal", "kcal"],
            ["protein_g", "Protein g"],
          ].map(([key, label]) => (
            <label key={key} className="field">
              <span className="field-label">{label}</span>
              <input
                className="input"
                type="number"
                inputMode="decimal"
                min="0"
                step="any"
                value={draft?.[key] ?? round(item[key])}
                onChange={(e) => onDraft({ ...draft, [key]: e.target.value })}
              />
            </label>
          ))}
        </div>
      )}
    </li>
  );
}

export default function MealCard({ proposal, onUpdate }) {
  const [editing, setEditing] = useState(false);
  const [drafts, setDrafts] = useState({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const pending = proposal.status === "pending";

  async function run(request) {
    setBusy(true);
    setError("");
    try {
      onUpdate(await request());
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  function edit(items, label = proposal.label) {
    return run(() => api.editProposal(proposal.id, { label, items }));
  }

  function changeItem(itemId, changes) {
    edit(proposal.items.map((item) => (item.item_id === itemId ? { item_id: itemId, ...changes } : { item_id: item.item_id })));
  }

  function removeItem(itemId) {
    const rest = proposal.items.filter((item) => item.item_id !== itemId);
    if (rest.length === 0) {
      run(() => api.discardProposal(proposal.id));
      return;
    }
    edit(rest.map((item) => ({ item_id: item.item_id })));
  }

  async function finishEditing() {
    const items = proposal.items.map((item) => {
      const draft = drafts[item.item_id];
      if (!draft) return { item_id: item.item_id };
      const changes = { item_id: item.item_id };
      if (draft.grams !== undefined && Number(draft.grams) > 0) changes.grams = Number(draft.grams);
      if (draft.kcal !== undefined && draft.kcal !== "") changes.kcal = Number(draft.kcal);
      if (draft.protein_g !== undefined && draft.protein_g !== "") changes.protein_g = Number(draft.protein_g);
      return changes;
    });
    await edit(items);
    setDrafts({});
    setEditing(false);
  }

  return (
    <article className={`card meal-card meal-card-${proposal.status}`} aria-label={title(proposal)}>
      <header className="meal-card-head">
        <h3 className="meal-card-title">{title(proposal)}</h3>
        {proposal.status === "confirmed" && <span className="meal-card-status">Saved</span>}
        {proposal.status === "discarded" && <span className="meal-card-status muted">Discarded</span>}
      </header>

      {editing && (
        <label className="field meal-card-label">
          <span className="field-label">Meal</span>
          <select className="input" value={proposal.label ?? ""} onChange={(e) => edit(proposal.items.map((item) => ({ item_id: item.item_id })), e.target.value || null)}>
            <option value="">No label</option>
            {LABELS.map((value) => (
              <option key={value} value={value}>
                {capitalize(value)}
              </option>
            ))}
          </select>
        </label>
      )}

      <ul className="meal-card-items">
        {proposal.items.map((item) => (
          <ItemRow
            key={`${item.item_id}-${item.key}`}
            item={item}
            pending={pending && !busy}
            editing={editing && pending}
            draft={drafts[item.item_id]}
            onDraft={(draft) => setDrafts({ ...drafts, [item.item_id]: draft })}
            onChange={(changes) => changeItem(item.item_id, changes)}
            onRemove={() => removeItem(item.item_id)}
          />
        ))}
      </ul>

      <div className="meal-card-total num">
        <span>{formatKcal(proposal.totals.kcal)}</span>
        <span className="muted">{round(proposal.totals.protein_g)} g protein</span>
      </div>

      {pending && proposal.duplicate_saved_at && (
        <p className="meal-card-note small">
          You saved the same food and amount at {formatTime(proposal.duplicate_saved_at)}. Save it again?
        </p>
      )}
      {error && <p className="error-text">{error}</p>}

      {pending && (
        <div className="btn-row">
          <button
            type="button"
            className="btn btn-primary"
            disabled={!proposal.can_save || busy || editing}
            onClick={() => run(() => api.confirmProposal(proposal.id))}
          >
            {proposal.duplicate_saved_at ? "Save again" : "Save"}
          </button>
          {editing ? (
            <button type="button" className="btn" disabled={busy} onClick={finishEditing}>
              Done
            </button>
          ) : (
            <button type="button" className="btn" disabled={busy} onClick={() => setEditing(true)}>
              Edit
            </button>
          )}
          <button type="button" className="btn btn-ghost" disabled={busy} onClick={() => run(() => api.discardProposal(proposal.id))}>
            Discard
          </button>
        </div>
      )}
    </article>
  );
}
