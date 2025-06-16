document.addEventListener('DOMContentLoaded', function () {
  const form = document.getElementById('matrix-form');
  const btn = document.getElementById('submit-btn');
  const loader = document.getElementById('loader');
  const btnText = document.getElementById('btn-text');
  if(form) {
    form.addEventListener('submit', function(){
      btn.disabled = true;
      loader.style.display = 'inline-block';
      btnText.textContent = "Submitting...";
    });
  }
});
// Tooltip bar logic
const tooltipBar = document.getElementById('matrix-tooltip-bar');
function setTooltip(text) { tooltipBar.textContent = text || ""; }
document.querySelectorAll('.matrix-table td[data-tooltip]').forEach(function(cell) {
  cell.addEventListener('mouseenter', function() { setTooltip(cell.getAttribute('data-tooltip')); });
  cell.addEventListener('mouseleave', function() { setTooltip(""); });
  cell.addEventListener('focus', function() { setTooltip(cell.getAttribute('data-tooltip')); });
  cell.addEventListener('blur', function() { setTooltip(""); });
  cell.addEventListener('click', function() { setTooltip(cell.getAttribute('data-tooltip')); });
});