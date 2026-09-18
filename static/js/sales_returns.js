(function () {
  'use strict';

  document.querySelectorAll('input[type="number"][name^="quantity_"]').forEach(function (input) {
    input.addEventListener('change', function () {
      var maximum = Number(input.max || 0);
      var value = Number(input.value || 0);
      if (maximum && value > maximum) {
        input.value = maximum;
      }
      if (value < 0) {
        input.value = 0;
      }
    });
  });
})();
