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
  // Detect new item typed by user (Select2 tags)
  // -------------------------------
  $(itemSelect).on('select2:select', function (e) {
    const data = e.params.data;

    // If user typed a new item (tag)
    if (data.id === data.text && !data.element) {
      const newItemName = data.text.trim();

      if (newItemName && confirm(`Add "${newItemName}" to item list?`)) {
        fetch('/invoice/items/add', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name: newItemName,
            default_units: '',
            default_price: 0
          })
        })
        .then(r => r.json())
        .then(res => {
          if (res.success) {
            alert('Item added to list!');

            // Add to window.invoiceItems so future rows include it
            window.invoiceItems.push({
              name: newItemName,
              default_units: '',
              default_price: 0
            });
          }
        });
      }
    }
  });

  // -------------------------------
  // Auto-fill units + price when item selected
  // -------------------------------
  if (itemSelect) {
    itemSelect.addEventListener('change', () => {
      const selected = itemSelect.options[itemSelect.selectedIndex];
      const defaultUnits = selected.dataset.units || "";
      const defaultPrice = selected.dataset.price || "";

      // Auto-fill units (Option C)
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
// Add new row
// -------------------------------
document.getElementById('addItem').addEventListener('click', () => {
  const tbody = document.querySelector('#itemsTable tbody');
  const tr = document.createElement('tr');

  tr.innerHTML = `
    <td><input type="text" name="lot_number[]" class="form-control"></td>

    <td>
      <select name="item[]" class="form-select item-select" data-tags="true">
        <option value="">Select Item</option>
        ${window.invoiceItems
          .map(it => `
            <option value="${it.name}" data-units="${it.default_units || ''}" data-price="${it.default_price || ''}">
              ${it.name}
            </option>
          `)
          .join('')}
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

  // Re-init Select2 for new dropdowns
  $(tr).find('select').each(function () {
    const enableTags = $(this).data('tags') === true;
    $(this).select2({
      width: '100%',
      theme: 'bootstrap-5',
      tags: enableTags
    });
  });

  attachRow(tr);
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
