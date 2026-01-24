function attachRow(row) {
  const qty = row.querySelector('.qty');
  const price = row.querySelector('.price');
  const total = row.querySelector('.line-total');

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

function recalcTotals() {
  let subtotal = 0;
  document.querySelectorAll('.line-total').forEach(input => {
    const v = parseFloat(input.value || 0);
    if (!isNaN(v)) subtotal += v;
  });

  const taxRateInput = document.getElementById('tax_rate');
  const shipInput = document.getElementById('ship_cost');

  const taxRate = parseFloat(taxRateInput.value || 0);
  const ship = parseFloat(shipInput.value || 0);

  const tax = subtotal * (taxRate / 100);
  const grand = subtotal + tax + ship;

  const subtotalEl = document.getElementById('subtotal');
  const grandEl = document.getElementById('grand_total');
  const taxHidden = document.getElementById('tax_hidden');

  if (subtotalEl) subtotalEl.value = subtotal.toFixed(2);
  if (grandEl) grandEl.value = grand.toFixed(2);
  if (taxHidden) taxHidden.value = tax.toFixed(2);
}

document.getElementById('addItem').addEventListener('click', () => {
  const tbody = document.querySelector('#itemsTable tbody');
  const tr = document.createElement('tr');
  tr.innerHTML = `
    <td><input type="text" name="lot_number[]" class="form-control"></td>
    <td><input type="text" name="item[]" class="form-control"></td>
    <td><input type="number" name="qty[]" class="form-control qty" step="0.01"></td>
    <td>
      <select name="units[]" class="form-select">
        <option>Grams</option>
        <option>kg</option>
        <option>Units</option>
      </select>
    </td>
    <td><input type="number" name="unit_price[]" class="form-control price" step="0.01"></td>
    <td><input type="text" class="form-control line-total" readonly></td>
    <td><button type="button" class="btn btn-sm btn-danger removeItem">×</button></td>
  `;
  tbody.appendChild(tr);
  attachRow(tr);
});

document.addEventListener('click', e => {
  if (e.target.classList.contains('removeItem')) {
    const row = e.target.closest('tr');
    if (row) {
      row.remove();
      recalcTotals();
    }
  }
});

document.getElementById('tax_rate').addEventListener('input', recalcTotals);
document.getElementById('ship_cost').addEventListener('input', recalcTotals);

document.querySelectorAll('#itemsTable tbody tr').forEach(attachRow);
recalcTotals();
