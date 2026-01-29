// -------------------------------
// Attach logic to a single row
// -------------------------------
function attachRow(row) {
  const qty = row.querySelector('.qty');
  const price = row.querySelector('.price');
  const total = row.querySelector('.line-total');
  const itemSelect = row.querySelector('.item-select');
  const unitsSelect = row.querySelector('.units-select');

  // -------------------------------
  // Detect "+ Add New Item…" option
  // -------------------------------
  if (itemSelect) {
    itemSelect.addEventListener('change', () => {
      if (itemSelect.value === "__add_new_item__") {
        window.location.href = "/invoice/items/add";
        return;
      }

      const selected = itemSelect.options[itemSelect.selectedIndex];
      const defaultUnits = selected.dataset.units || "";
      const defaultPrice = selected.dataset.price || "";

      // Auto-fill units
      if (defaultUnits) {
        unitsSelect.innerHTML = `
          <option value="${defaultUnits}">${defaultUnits}</option>
          <option value="Grams">Grams</option>
          <option value="kg">kg</option>
          <option value="Units">Units</option>
        `;
      }

      // Auto-fill price
      if (defaultPrice) {
        price.value = parseFloat(defaultPrice).toFixed(2);
      }

      recalcLine();
    });
  }

  // -------------------------------
  // Recalculate line total
  // -------------------------------
  function recalcLine() {
    const q = parseFloat(qty.value || 0);
    const p = parseFloat(price.value || 0);
    const line = q * p;
    total.value = line ? line.toFixed(2) : '';
    recalcTotals();
  }

  qty.addEventListener('input', recalcLine);
  price.addEventListener('input', recalcLine);
}

// -------------------------------
// Recalculate totals
// -------------------------------
function recalcTotals() {
  let subtotal = 0;

  document.querySelectorAll('.line-total').forEach(input => {
    const v = parseFloat(input.value || 0);
    if (!isNaN(v)) subtotal += v;
  });

  const taxRate = parseFloat(document.getElementById('tax_rate').value || 0);
  const ship = parseFloat(document.getElementById('ship_cost').value || 0);

  const tax = subtotal * (taxRate / 100);
  const grand = subtotal + tax + ship;

  document.getElementById('subtotal').value = subtotal.toFixed(2);
  document.getElementById('grand_total').value = grand.toFixed(2);
  document.getElementById('tax_hidden').value = tax.toFixed(2);
}

// -------------------------------
// Add new row (FIXED)
// -------------------------------
document.getElementById('addLineItem').addEventListener('click', () => {
  const tbody = document.querySelector('#itemsTable tbody');
  const tr = document.createElement('tr');

  tr.classList.add("item-row");

  tr.innerHTML = `
    <td><input type="text" name="lot_number[]" class="form-control"></td>

    <td>
      <select name="item[]" class="form-select item-select">
        <option value="">Select Item</option>
        ${window.invoiceItems
          .map(it => `
            <option value="${it.name}" data-units="${it.default_units || ''}" data-price="${it.default_price || ''}">
              ${it.name}
            </option>
          `)
          .join('')}
        <option value="__add_new_item__">+ Add New Item…</option>
      </select>
    </td>

    <td><input type="number" name="qty[]" class="form-control qty" step="0.01"></td>

    <td>
      <select name="units[]" class="form-select units-select">
        <option value="">Select Units</option>
        <option value="Grams">Grams</option>
        <option value="kg">kg</option>
        <option value="Units">Units</option>
      </select>
    </td>

    <td><input type="number" name="unit_price[]" class="form-control price" step="0.01"></td>
    <td><input type="text" class="form-control line-total" readonly></td>
    <td><button type="button" class="btn btn-sm btn-danger removeItem">×</button></td>
  `;

  tbody.appendChild(tr);

  attachRow(tr);
  recalcTotals();
});

// -------------------------------
// Remove row
// -------------------------------
document.addEventListener('click', e => {
  if (e.target.classList.contains('removeItem')) {
    const row = e.target.closest('tr');
    if (row) {
      row.remove();
      recalcTotals();
    }
  }
});

// -------------------------------
// Tax + shipping listeners
// -------------------------------
document.getElementById('tax_rate').addEventListener('input', recalcTotals);
document.getElementById('ship_cost').addEventListener('input', recalcTotals);

// -------------------------------
// Initialize existing rows
// -------------------------------
document.querySelectorAll('#itemsTable tbody tr').forEach(attachRow);
recalcTotals();
