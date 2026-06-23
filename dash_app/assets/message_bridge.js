// Ingests fossil-click messages posted from inside the map iframe
// (window.parent.postMessage) into the into Dash's dcc.Store 'click-store' dcc.Store.
window.addEventListener('message', function (event) {
  if (event.data && event.data.type === 'fossil-click') {
    window.dash_clientside.set_props('click-store', {
      data: { nearby: event.data.data, selected: null },
    });
  }
});
