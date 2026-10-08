document.addEventListener('DOMContentLoaded', () => {
  const rows = document.getElementById('ingredient-rows');
  const add = document.getElementById('add-ingredient');
  if (rows && add) {
    const options = (window.ingredientOptions || []).map((id, i) => `<option value="${id}">${escapeHtml((window.ingredientLabels || [])[i] || '')}</option>`).join('');
    const updateRemove = () => rows.querySelectorAll('.remove-row').forEach(button => {
      button.disabled = rows.querySelectorAll('.ingredient-edit-row').length <= 1;
    });
    const addRow = () => {
      const row = document.createElement('div');
      row.className = 'ingredient-edit-row';
      row.innerHTML = `<select name="ingredient_id[]" required><option value="">Choose ingredient</option>${options}</select><input type="number" name="quantity[]" min="0" step="any" placeholder="Amount" required><input name="unit[]" placeholder="Unit"><button class="remove-row" type="button" aria-label="Remove ingredient">×</button>`;
      rows.appendChild(row); updateRemove();
    };
    add.addEventListener('click', addRow);
    rows.addEventListener('click', event => {
      if (event.target.closest('.remove-row') && rows.querySelectorAll('.ingredient-edit-row').length > 1) {
        event.target.closest('.ingredient-edit-row').remove(); updateRemove();
      }
    });
    updateRemove();
  }

  document.querySelectorAll('.serving-control button').forEach(button => button.addEventListener('click', () => {
    const delta = Number(button.dataset.delta);
    const display = document.getElementById('serving-display');
    const count = document.getElementById('serving-count');
    if (!display || !count) return;
    const base = Number(document.querySelector('.detail-hero')?.dataset.baseServings || count.textContent);
    const current = Number(display.textContent);
    const next = Math.max(1, Math.min(24, current + delta));
    display.textContent = next; count.textContent = next;
    document.querySelectorAll('[data-base]').forEach(el => {
      const val = Number(el.dataset.base) * next / base;
      el.textContent = Number.isInteger(val) ? val : Number(val.toFixed(2));
    });
  }));

  document.querySelectorAll('.ingredient-check').forEach(check => check.addEventListener('click', () => {
    check.classList.toggle('checked'); check.closest('li').classList.toggle('crossed');
  }));
});

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
}
