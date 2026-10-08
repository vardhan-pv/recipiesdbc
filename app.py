from __future__ import annotations

import os
import sqlite3
from itertools import zip_longest
from pathlib import Path
from typing import Any

from flask import Flask, abort, flash, g, redirect, render_template, request, url_for

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("RECIPE_DB_PATH", BASE_DIR / "instance" / "recipes.db"))
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "local-development-key-change-me")
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024


@app.context_processor
def inject_nav_counts() -> dict[str, int]:
    try:
        db = get_db()
        return {"nav_recipe_count": db.execute("SELECT COUNT(*) FROM recipes").fetchone()[0],
                "nav_ingredient_count": db.execute("SELECT COUNT(*) FROM ingredients").fetchone()[0]}
    except sqlite3.OperationalError:
        return {"nav_recipe_count": 0, "nav_ingredient_count": 0}

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS recipes (
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
CREATE TABLE IF NOT EXISTS ingredients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE COLLATE NOCASE,
    category TEXT NOT NULL DEFAULT 'Other',
    notes TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS recipe_ingredients (
    recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    ingredient_id INTEGER NOT NULL REFERENCES ingredients(id) ON DELETE RESTRICT,
    quantity REAL NOT NULL CHECK(quantity >= 0),
    unit TEXT NOT NULL DEFAULT '',
    PRIMARY KEY(recipe_id, ingredient_id, unit)
);
CREATE INDEX IF NOT EXISTS idx_recipe_category ON recipes(category);
CREATE INDEX IF NOT EXISTS idx_ingredient_name ON ingredients(name);
CREATE INDEX IF NOT EXISTS idx_recipe_ingredient_ingredient ON recipe_ingredients(ingredient_id);
"""

SEED_INGREDIENTS = [
    ("Tomato", "Vegetables", "Ripe tomatoes work best."), ("Onion", "Vegetables", ""),
    ("Garlic", "Vegetables", ""), ("Olive oil", "Pantry", ""), ("Pasta", "Grains", ""),
    ("Basil", "Herbs", "Fresh or dried."), ("Salt", "Spices", ""), ("Black pepper", "Spices", ""),
    ("Rice", "Grains", ""), ("Chicken breast", "Protein", ""), ("Coconut milk", "Pantry", ""),
    ("Curry powder", "Spices", ""), ("Ginger", "Vegetables", ""), ("Lemon", "Fruit", ""),
    ("Egg", "Dairy & eggs", ""), ("All-purpose flour", "Baking", ""), ("Milk", "Dairy & eggs", ""),
    ("Butter", "Dairy & eggs", ""), ("Cheddar cheese", "Dairy & eggs", ""), ("Spinach", "Vegetables", ""),
    ("Chickpeas", "Pantry", ""), ("Cumin", "Spices", ""), ("Yogurt", "Dairy & eggs", ""),
]
SEED_RECIPES = [
    ("Tomato Basil Pasta", "A quick, comforting pasta with a bright tomato sauce.", "Dinner", "1. Cook pasta in salted water until just tender.\n2. Warm olive oil; soften onion and garlic.\n3. Add chopped tomatoes and simmer for 15 minutes.\n4. Toss with pasta, basil, salt and pepper.", 10, 20, 2,
     [("Tomato", 400, "g"), ("Onion", 1, "piece"), ("Garlic", 2, "cloves"), ("Olive oil", 1, "tbsp"), ("Pasta", 200, "g"), ("Basil", 8, "leaves"), ("Salt", 1, "tsp"), ("Black pepper", .25, "tsp")]),
    ("Coconut Chicken Curry", "A gently spiced curry served with steamed rice.", "Dinner", "1. Cook rice according to its package instructions.\n2. Sauté onion, garlic and ginger in a little oil.\n3. Add chicken and curry powder; cook until browned.\n4. Pour in coconut milk and simmer until chicken is cooked through.\n5. Finish with lemon and serve over rice.", 15, 30, 3,
     [("Chicken breast", 450, "g"), ("Coconut milk", 400, "ml"), ("Curry powder", 2, "tbsp"), ("Onion", 1, "piece"), ("Garlic", 2, "cloves"), ("Ginger", 1, "tbsp"), ("Rice", 225, "g"), ("Lemon", .5, "piece")]),
    ("Spinach Omelette", "A simple protein-rich breakfast with fresh spinach.", "Breakfast", "1. Whisk eggs with salt and pepper.\n2. Wilt spinach in a buttered pan.\n3. Pour in eggs and cook gently until nearly set.\n4. Add cheese, fold and serve.", 5, 8, 1,
     [("Egg", 2, "pieces"), ("Spinach", 30, "g"), ("Butter", 1, "tsp"), ("Cheddar cheese", 20, "g"), ("Salt", .25, "tsp"), ("Black pepper", .1, "tsp")]),
    ("Chickpea Salad", "A fresh, tangy salad that works for lunch or meal prep.", "Lunch", "1. Drain and rinse chickpeas.\n2. Combine with chopped tomato and onion.\n3. Dress with lemon juice, olive oil, cumin, salt and pepper.\n4. Serve chilled or at room temperature.", 15, 0, 2,
     [("Chickpeas", 400, "g"), ("Tomato", 2, "pieces"), ("Onion", .5, "piece"), ("Lemon", 1, "piece"), ("Olive oil", 1, "tbsp"), ("Cumin", .5, "tsp")]),
    ("Fluffy Pancakes", "Soft pancakes for an easy weekend breakfast.", "Breakfast", "1. Mix flour, a pinch of salt and milk until smooth.\n2. Beat in the egg and melted butter.\n3. Pour small portions onto a warm pan.\n4. Flip when bubbles appear; cook until golden.", 10, 15, 4,
     [("All-purpose flour", 200, "g"), ("Milk", 250, "ml"), ("Egg", 1, "piece"), ("Butter", 30, "g"), ("Salt", .25, "tsp")]),
]


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_error: BaseException | None = None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    db = get_db()
    db.executescript(SCHEMA)
    if db.execute("SELECT COUNT(*) FROM recipes").fetchone()[0] == 0:
        for name, category, notes in SEED_INGREDIENTS:
            db.execute("INSERT OR IGNORE INTO ingredients(name,category,notes) VALUES(?,?,?)", (name, category, notes))
        for name, description, category, instructions, prep, cook, servings, items in SEED_RECIPES:
            cur = db.execute("INSERT INTO recipes(name,description,category,instructions,prep_minutes,cook_minutes,servings) VALUES(?,?,?,?,?,?,?)",
                             (name, description, category, instructions, prep, cook, servings))
            for ingredient, quantity, unit in items:
                ing = db.execute("SELECT id FROM ingredients WHERE name=? COLLATE NOCASE", (ingredient,)).fetchone()
                db.execute("INSERT INTO recipe_ingredients(recipe_id,ingredient_id,quantity,unit) VALUES(?,?,?,?)",
                           (cur.lastrowid, ing["id"], quantity, unit))
    db.commit()


@app.before_request
def ensure_db() -> None:
    init_db()


def get_recipe(recipe_id: int) -> sqlite3.Row:
    recipe = get_db().execute("SELECT * FROM recipes WHERE id=?", (recipe_id,)).fetchone()
    if recipe is None:
        abort(404)
    return recipe


def recipe_items(recipe_id: int) -> list[sqlite3.Row]:
    return get_db().execute("""SELECT i.id ingredient_id,i.name,i.category,ri.quantity,ri.unit
        FROM recipe_ingredients ri JOIN ingredients i ON i.id=ri.ingredient_id
        WHERE ri.recipe_id=? ORDER BY i.name""", (recipe_id,)).fetchall()


def parse_recipe_form() -> tuple[dict[str, Any], list[tuple[int, float, str]]]:
    name = request.form.get("name", "").strip()
    instructions = request.form.get("instructions", "").strip()
    if not name or not instructions:
        raise ValueError("Recipe name and instructions are required.")
    try:
        prep = max(0, int(request.form.get("prep_minutes", "0")))
        cook = max(0, int(request.form.get("cook_minutes", "0")))
        servings = max(1, int(request.form.get("servings", "1")))
    except ValueError:
        raise ValueError("Prep time, cook time and servings must be whole numbers.")
    data = {"name": name, "description": request.form.get("description", "").strip(),
            "category": request.form.get("category", "Other").strip() or "Other",
            "instructions": instructions, "prep_minutes": prep, "cook_minutes": cook, "servings": servings}
    selected: list[tuple[int, float, str]] = []
    rows = zip_longest(request.form.getlist("ingredient_id[]"), request.form.getlist("quantity[]"), request.form.getlist("unit[]"), fillvalue="")
    for i_id, amount, unit in rows:
        if not i_id and not amount:
            continue
        try:
            ingredient_id, quantity = int(i_id), float(amount)
        except (ValueError, TypeError):
            raise ValueError("Choose an ingredient and enter a valid quantity for every ingredient row.")
        if quantity < 0:
            raise ValueError("Ingredient quantities cannot be negative.")
        selected.append((ingredient_id, quantity, unit.strip()))
    if not selected:
        raise ValueError("Add at least one ingredient to the recipe.")
    if len({(i, u.lower()) for i, _, u in selected}) != len(selected):
        raise ValueError("Each ingredient and unit combination can appear only once.")
    return data, selected


def save_recipe(data: dict[str, Any], selected: list[tuple[int, float, str]], recipe_id: int | None = None) -> None:
    db = get_db()
    valid = {row[0] for row in db.execute("SELECT id FROM ingredients")}
    if any(i_id not in valid for i_id, _, _ in selected):
        raise ValueError("One selected ingredient no longer exists. Refresh and try again.")
    fields = (data["name"], data["description"], data["category"], data["instructions"], data["prep_minutes"], data["cook_minutes"], data["servings"])
    try:
        if recipe_id is None:
            cur = db.execute("INSERT INTO recipes(name,description,category,instructions,prep_minutes,cook_minutes,servings) VALUES(?,?,?,?,?,?,?)", fields)
            recipe_id = cur.lastrowid
        else:
            db.execute("UPDATE recipes SET name=?,description=?,category=?,instructions=?,prep_minutes=?,cook_minutes=?,servings=? WHERE id=?", (*fields, recipe_id))
            db.execute("DELETE FROM recipe_ingredients WHERE recipe_id=?", (recipe_id,))
        db.executemany("INSERT INTO recipe_ingredients(recipe_id,ingredient_id,quantity,unit) VALUES(?,?,?,?)",
                       [(recipe_id, i_id, qty, unit) for i_id, qty, unit in selected])
        db.commit()
    except sqlite3.IntegrityError as exc:
        db.rollback()
        if "recipes.name" in str(exc):
            raise ValueError("A recipe with that name already exists.")
        raise ValueError("Could not save this recipe. Check the ingredient selections.")


@app.route("/")
def dashboard():
    db = get_db()
    stats = {"recipes": db.execute("SELECT COUNT(*) FROM recipes").fetchone()[0],
             "ingredients": db.execute("SELECT COUNT(*) FROM ingredients").fetchone()[0],
             "categories": db.execute("SELECT COUNT(DISTINCT category) FROM recipes").fetchone()[0]}
    recent = db.execute("SELECT r.*,COUNT(ri.ingredient_id) ingredient_count FROM recipes r LEFT JOIN recipe_ingredients ri ON ri.recipe_id=r.id GROUP BY r.id ORDER BY r.created_at DESC,r.id DESC LIMIT 4").fetchall()
    category_counts = db.execute("SELECT category,COUNT(*) count FROM recipes GROUP BY category ORDER BY count DESC,category").fetchall()
    return render_template("dashboard.html", stats=stats, recent=recent, categories=category_counts)


@app.route("/recipes")
def recipes():
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    sql = "SELECT r.*,COUNT(ri.ingredient_id) ingredient_count FROM recipes r LEFT JOIN recipe_ingredients ri ON ri.recipe_id=r.id WHERE 1=1"
    args: list[Any] = []
    if q:
        sql += " AND (r.name LIKE ? OR r.description LIKE ? OR EXISTS (SELECT 1 FROM recipe_ingredients x JOIN ingredients i ON i.id=x.ingredient_id WHERE x.recipe_id=r.id AND i.name LIKE ?))"
        args.extend([f"%{q}%"] * 3)
    if category:
        sql += " AND r.category=?"; args.append(category)
    sql += " GROUP BY r.id ORDER BY r.name COLLATE NOCASE"
    rows = get_db().execute(sql, args).fetchall()
    cats = [r[0] for r in get_db().execute("SELECT DISTINCT category FROM recipes ORDER BY category")]
    return render_template("recipes.html", recipes=rows, q=q, category=category, categories=cats)


@app.route("/recipes/new", methods=["GET", "POST"])
def recipe_new():
    if request.method == "POST":
        try:
            data, selected = parse_recipe_form(); save_recipe(data, selected)
            flash("Recipe added successfully.", "success"); return redirect(url_for("recipes"))
        except ValueError as exc:
            flash(str(exc), "error")
    return render_template("recipe_form.html", recipe=None, items=[], ingredients=get_db().execute("SELECT * FROM ingredients ORDER BY name").fetchall(), categories=["Breakfast", "Lunch", "Dinner", "Snack", "Dessert", "Other"])


@app.route("/recipes/<int:recipe_id>")
def recipe_detail(recipe_id: int):
    recipe = get_recipe(recipe_id)
    return render_template("recipe_detail.html", recipe=recipe, items=recipe_items(recipe_id))


@app.route("/recipes/<int:recipe_id>/edit", methods=["GET", "POST"])
def recipe_edit(recipe_id: int):
    recipe = get_recipe(recipe_id)
    if request.method == "POST":
        try:
            data, selected = parse_recipe_form(); save_recipe(data, selected, recipe_id)
            flash("Recipe updated.", "success"); return redirect(url_for("recipe_detail", recipe_id=recipe_id))
        except ValueError as exc:
            flash(str(exc), "error")
    return render_template("recipe_form.html", recipe=recipe, items=recipe_items(recipe_id), ingredients=get_db().execute("SELECT * FROM ingredients ORDER BY name").fetchall(), categories=["Breakfast", "Lunch", "Dinner", "Snack", "Dessert", "Other"])


@app.post("/recipes/<int:recipe_id>/delete")
def recipe_delete(recipe_id: int):
    get_recipe(recipe_id)
    get_db().execute("DELETE FROM recipes WHERE id=?", (recipe_id,)); get_db().commit()
    flash("Recipe deleted.", "success"); return redirect(url_for("recipes"))


@app.route("/ingredients")
def ingredients():
    q = request.args.get("q", "").strip()
    sql = "SELECT i.*,COUNT(DISTINCT ri.recipe_id) recipe_count FROM ingredients i LEFT JOIN recipe_ingredients ri ON ri.ingredient_id=i.id"
    args: list[Any] = []
    if q:
        sql += " WHERE i.name LIKE ? OR i.category LIKE ?"; args = [f"%{q}%", f"%{q}%"]
    sql += " GROUP BY i.id ORDER BY i.name COLLATE NOCASE"
    return render_template("ingredients.html", ingredients=get_db().execute(sql, args).fetchall(), q=q)


@app.route("/ingredients/new", methods=["GET", "POST"])
def ingredient_new():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Ingredient name is required.", "error")
        else:
            try:
                get_db().execute("INSERT INTO ingredients(name,category,notes) VALUES(?,?,?)", (name, request.form.get("category", "Other").strip() or "Other", request.form.get("notes", "").strip()))
                get_db().commit(); flash("Ingredient added.", "success"); return redirect(url_for("ingredients"))
            except sqlite3.IntegrityError:
                flash("That ingredient already exists.", "error")
    return render_template("ingredient_form.html", ingredient=None)


@app.route("/ingredients/<int:ingredient_id>/edit", methods=["GET", "POST"])
def ingredient_edit(ingredient_id: int):
    db = get_db(); ingredient = db.execute("SELECT * FROM ingredients WHERE id=?", (ingredient_id,)).fetchone()
    if ingredient is None: abort(404)
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name: flash("Ingredient name is required.", "error")
        else:
            try:
                db.execute("UPDATE ingredients SET name=?,category=?,notes=? WHERE id=?", (name, request.form.get("category", "Other").strip() or "Other", request.form.get("notes", "").strip(), ingredient_id))
                db.commit(); flash("Ingredient updated.", "success"); return redirect(url_for("ingredients"))
            except sqlite3.IntegrityError: flash("An ingredient with that name already exists.", "error")
    return render_template("ingredient_form.html", ingredient=ingredient)


@app.post("/ingredients/<int:ingredient_id>/delete")
def ingredient_delete(ingredient_id: int):
    db = get_db()
    try:
        db.execute("DELETE FROM ingredients WHERE id=?", (ingredient_id,)); db.commit()
        flash("Ingredient deleted.", "success")
    except sqlite3.IntegrityError:
        db.rollback(); flash("This ingredient is used in a recipe. Remove it from those recipes first.", "error")
    return redirect(url_for("ingredients"))


@app.route("/shopping-list", methods=["GET", "POST"])
def shopping_list():
    db = get_db()
    all_recipes = db.execute("SELECT id,name FROM recipes ORDER BY name").fetchall()
    selected_ids = [int(x) for x in request.form.getlist("recipe_ids") if x.isdigit()] if request.method == "POST" else []
    list_items = []
    if selected_ids:
        placeholders = ",".join("?" for _ in selected_ids)
        rows = db.execute(f"SELECT i.name,ri.unit,SUM(ri.quantity) quantity,COUNT(DISTINCT ri.recipe_id) recipe_count FROM recipe_ingredients ri JOIN ingredients i ON i.id=ri.ingredient_id WHERE ri.recipe_id IN ({placeholders}) GROUP BY i.id,ri.unit ORDER BY i.name,ri.unit", selected_ids).fetchall()
        list_items = rows
    return render_template("shopping_list.html", recipes=all_recipes, selected_ids=selected_ids, items=list_items)


@app.route("/database")
def database_info():
    db = get_db()
    tables = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()
    return render_template("database.html", tables=tables)


@app.errorhandler(404)
def not_found(_error):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1", host="127.0.0.1", port=int(os.environ.get("PORT", 5000)))
