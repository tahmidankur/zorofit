import { useEffect, useRef, useState } from "react";
import { Search } from "lucide-react";
import { api } from "../api.js";
import { round } from "../format.js";
import CustomFoodForm from "./CustomFoodForm.jsx";
import "./FoodSearch.css";

const DEBOUNCE_MS = 250;

export default function FoodSearch({ onPick, onManual, initialQuery = "", autoFocus = true }) {
  const [query, setQuery] = useState(initialQuery);
  const [results, setResults] = useState([]);
  const [status, setStatus] = useState("idle");
  const [addingCustom, setAddingCustom] = useState(false);
  const latest = useRef(0);

  useEffect(() => {
    const text = query.trim();
    if (!text) {
      setResults([]);
      setStatus("idle");
      return undefined;
    }
    const requestId = ++latest.current;
    const timer = setTimeout(() => {
      setStatus("loading");
      api
        .searchFoods(text)
        .then((foods) => {
          // Typing fast can return responses out of order; keep only the newest.
          if (requestId !== latest.current) return;
          setResults(foods);
          setStatus("done");
        })
        .catch(() => requestId === latest.current && setStatus("error"));
    }, DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [query]);

  if (addingCustom) {
    return (
      <CustomFoodForm
        initialName={query.trim()}
        onSaved={(food) =>
          api.searchFoods(food.name).then((foods) => {
            const match = foods.find((item) => item.custom_food_id === food.id);
            setAddingCustom(false);
            if (match) onPick(match);
          })
        }
        onCancel={() => setAddingCustom(false)}
      />
    );
  }

  return (
    <div className="food-search">
      <label className="food-search-box">
        <Search size={20} aria-hidden="true" className="food-search-icon" />
        <input
          className="input food-search-input"
          type="search"
          value={query}
          placeholder="Search foods, e.g. rice"
          aria-label="Search foods"
          autoFocus={autoFocus}
          onChange={(e) => setQuery(e.target.value)}
        />
      </label>
      {status === "loading" && results.length === 0 && <p className="small muted">Searching…</p>}
      {status === "error" && <p className="error-text">Search failed. Try again.</p>}
      {results.length > 0 && (
        <ul className="food-results" aria-label="Search results">
          {results.map((food) => (
            <li key={food.key}>
              <button type="button" className="food-result" onClick={() => onPick(food)}>
                <span className="food-result-name">{food.name}</span>
                <span className="small muted num">
                  {food.category} · {round(food.kcal_100g)} kcal / 100 g
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
      {status === "done" && results.length === 0 && <p className="small muted">No matches.</p>}
      <div className="btn-row food-search-links">
        <button type="button" className="btn btn-ghost" onClick={() => setAddingCustom(true)}>
          Add your own food
        </button>
        {onManual && (
          <button type="button" className="btn btn-ghost" onClick={onManual}>
            Type values by hand
          </button>
        )}
      </div>
    </div>
  );
}
