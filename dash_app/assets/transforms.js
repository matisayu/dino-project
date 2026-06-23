// Referenced via tooltip={'transform': 'name'} in app.py.
// Overrides dcc.RangeSlider's tooltip raw numeric `value` with
// the actual Ma boundary label for display.
window.dccFunctions = window.dccFunctions || {};

window.dccFunctions.geoAgeLabel = function (value) {
  const boundaries = [
    '251.9 Ma', '247.2 Ma', '237.0 Ma', '201.3 Ma', '174.1 Ma',
    '163.5 Ma', '145.0 Ma', '100.5 Ma', '66.0 Ma',
  ];
  return boundaries[value];
};
