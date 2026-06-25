// Detects when the taxon checklist (built in taxon_filter.py) scrolls
// near its bottom, then pings 'taxon-scroll-trigger' so update_taxon_list()
// reveals the next batch

let lastTriggeredScrollHeight = 0;

document.addEventListener('scroll', function (event) {
  const el = event.target;
  if (!el || el.id !== 'taxon-checklist') {
    return;
  }

  const nearBottom = el.scrollTop + el.clientHeight >= el.scrollHeight - 50;

  // Suppress re-triggering until scrollHeight actually grows (Python
  // has responded with more rows), avoids firing on every scroll tick
  // while sitting at the bottom waiting for a response.
  if (nearBottom && el.scrollHeight !== lastTriggeredScrollHeight) {
    lastTriggeredScrollHeight = el.scrollHeight;
    window.dash_clientside.set_props('taxon-scroll-trigger', { data: Date.now() });
  }
}, true);
