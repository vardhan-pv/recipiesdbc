# Pantry & Plate — Recipe Ingredient Database

A responsive Flask + SQLite application for managing recipes and a reusable ingredient catalog. It is designed as a complete BDA coursework project and includes a relational schema page, sample data, CRUD operations, search, serving scaling and shopping list generation.

## Features

- Overview dashboard with recipe, ingredient and category counts
- Add, browse, search, filter, edit and delete recipes
- Maintain a normalized, reusable ingredient catalog
- Recipe instructions, categories, prep/cook times and serving counts
- Many-to-many recipe/ingredient relationship with quantity and unit
- Scale ingredient amounts on the recipe page
- Build a combined shopping list from selected recipes
- Schema page explaining tables, keys, relationships, normalization and constraints
- Five sample recipes and a starter ingredient catalog on first launch
- SQLite database created locally at `instance/recipes.db`

## Run locally

Python 3.10 or newer is recommended.

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open <http://127.0.0.1:5000>. The database and sample records are initialized automatically. To start with a clean database, stop the server and delete `instance/recipes.db`; the next launch recreates it.

For a different database location, set `RECIPE_DB_PATH`. For example, in PowerShell:

```powershell
$env:RECIPE_DB_PATH = "C:\data\recipes.db"
python app.py
```

## Database design

The schema has three core tables:

1. `recipes` stores the recipe description, method, category, time and servings.
2. `ingredients` stores each reusable ingredient once.
3. `recipe_ingredients` joins recipes and ingredients and stores the amount and unit used in that recipe.

The join table has a composite primary key `(recipe_id, ingredient_id, unit)`. Foreign keys enforce valid links, and deleting a recipe cascades to its join rows. Ingredient deletion is restricted while it is used by a recipe. Quantities must be non-negative and serving counts positive.

## Project structure

```text
app.py                 Flask routes, validation, schema and seed data
templates/             Jinja HTML pages
static/style.css       Responsive visual design
static/app.js          Dynamic ingredient rows, serving scaler, checkboxes
requirements.txt       Python dependencies
instance/recipes.db    Generated SQLite database (created at runtime)
```

## BDA demonstration outline

1. Start the app and show the seeded dashboard.
2. Create an ingredient, then use it in a new recipe.
3. Search by recipe name or ingredient and filter by category.
4. Open a recipe, scale servings and check off ingredients.
5. Select multiple recipes in Shopping list and build the combined list.
6. Explain the ER model and many-to-many junction table on Schema & relationships.

## Notes

- The app is intended for local coursework/demo use. Before deploying it for public use, configure a strong `SECRET_KEY`, add authentication and CSRF protection, and run it behind a production WSGI server.
- Shopping quantities are summed only when both ingredient and unit match; conversions between units are intentionally not guessed.
