function oneDecimal(value) {
  return Math.round(value * 10) / 10;
}

export function scaleFood(food, grams) {
  const factor = grams / 100;
  return {
    kcal: oneDecimal(food.kcal_100g * factor),
    protein_g: oneDecimal(food.protein_100g * factor),
    carbs_g: oneDecimal(food.carbs_100g * factor),
    fat_g: oneDecimal(food.fat_100g * factor),
  };
}

// Portion choices from the API end with "100 g"; the UI offers plain grams instead.
export function unitOptions(food) {
  const portions = food.portions.filter((portion) => portion.unit !== "g");
  return [...portions.map((portion) => ({ unit: portion.unit, gramsEach: portion.grams })), { unit: "g", gramsEach: 1 }];
}

export function portionText(quantity, unit) {
  return `${quantity} ${unit}`;
}
