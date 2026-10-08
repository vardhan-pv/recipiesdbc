PRAGMA foreign_keys = ON;

CREATE TABLE recipes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  description TEXT NOT NULL DEFAULT '',
  category TEXT NOT NULL DEFAULT 'Other',
  instructions TEXT NOT NULL,
  prep_minutes INTEGER NOT NULL DEFAULT 0 CHECK(prep_minutes >= 0),
  cook_minutes INTEGER NOT NULL DEFAULT 0 CHECK(cook_minutes >= 0),
  servings INTEGER NOT NULL DEFAULT 1 CHECK(servings > 0),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE ingredients (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE COLLATE NOCASE,
  category TEXT NOT NULL DEFAULT 'Other',
  notes TEXT NOT NULL DEFAULT ''
);

CREATE TABLE recipe_ingredients (
  recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
  ingredient_id INTEGER NOT NULL REFERENCES ingredients(id) ON DELETE RESTRICT,
  quantity REAL NOT NULL CHECK(quantity >= 0),
  unit TEXT NOT NULL DEFAULT '',
  PRIMARY KEY(recipe_id, ingredient_id, unit)
);

CREATE INDEX idx_recipe_category ON recipes(category);
CREATE INDEX idx_ingredient_name ON ingredients(name);
CREATE INDEX idx_recipe_ingredient_ingredient ON recipe_ingredients(ingredient_id);
