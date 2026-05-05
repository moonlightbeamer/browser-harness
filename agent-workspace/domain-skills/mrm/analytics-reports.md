# FreeWheel MRM analytics reports

Use for FreeWheel MRM (`mrm*.freewheel.tv`) when creating, running, and exporting Analytics reports.

## Routing

- App URLs include the network id: `/app/<network_id>/...`.
- Saved Analytics reports: `/app/<network_id>/insights/analytics/show`.
- New Analytics builder: `/app/<network_id>/insights/analytics/builder?reportID=-1&mode=default`.
- If redirected to `/system/account/login` or MFA, stop for human/account-specific auth. Never store credentials or OTP seeds in this folder.

## Micro-frontend / shadow DOM

FreeWheel MRM uses web-component micro-frontends. Normal `document.querySelector(...)` often misses the real controls.

Important hosts:

- Top nav / report menu: `fw-microfe-layout` shadow root.
- Analytics saved reports and builder: `fw-insights-analytics` shadow root.

Use a recursive shadow-DOM walker for selectors/text lookup:

```js
function* all(root = document) {
  let nodes = [];
  try { nodes = [...root.querySelectorAll('*')]; } catch (_) {}
  for (const e of nodes) {
    yield e;
    if (e.shadowRoot) yield* all(e.shadowRoot);
  }
}
function text(e) {
  return (e.innerText || e.textContent || e.value || '').trim().replace(/\s+/g, ' ');
}
function byText(exact) {
  return [...all()].find(e => text(e) === exact);
}
```

## Analytics builder field selection

- A new Historic report commonly defaults to `DATE RANGE is Last Full Day (...)` in the site timezone; verify the date chip before running.
- The parameter search input has placeholder `Search Dimensions & Metrics` and is the most reliable way to find fields. Prefer search over scrolling through the accordion list.
- Parameter rows use labels with exact display text. Each label wraps a hidden `input[type="checkbox"]` and a visible fake checkbox whose class contains `input-fake`.
- Click the visible fake checkbox (using its current bounding box), not hard-coded coordinates.

Pattern:

```js
async function setParamSearch(q) {
  const input = [...all()].find(e => e.tagName === 'INPUT' && e.placeholder === 'Search Dimensions & Metrics');
  input.focus();
  Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(input, q);
  input.dispatchEvent(new InputEvent('input', { bubbles: true, composed: true, inputType: 'insertText', data: q }));
  input.dispatchEvent(new Event('change', { bubbles: true, composed: true }));
}

function paramCheckboxPoint(labelText) {
  const label = [...all()].find(e => e.tagName === 'LABEL' && text(e) === labelText);
  if (!label) return null;
  const input = label.querySelector('input[type="checkbox"]');
  const fake = label.querySelector('[class*="input-fake"]') || label;
  const r = fake.getBoundingClientRect();
  return { checked: input.checked, disabled: input.disabled, x: r.x + r.width / 2, y: r.y + r.height / 2 };
}
```

Typical deal-performance fields:

- `Deal ID`
- `Deal Price`
- `Deal Pacing`
- `Delivered Clicks`
- `Net Delivered Impressions`
- `Deal FFDR (%)`

Trap: `Fill Rate (%)` can be disabled after selecting deal-level/programmatic dimensions. Do not silently assume it is selectable; if exact fill rate is required, verify availability or ask whether `Deal FFDR (%)` is acceptable.

## Running and exporting

- Run with the exact-text `Run Report` button.
- While running, the page shows `Your report is running.` Wait until that overlay disappears and either rows or the `No results returned.` empty state appears.
- A report with no rows is still exportable; the CSV will contain report metadata and headers only.
- Export uses a split button: exact-text `Export` opens menu items `Export CSV` and `Export Excel`.
- Before clicking `Export CSV`, set Chrome download behavior with a task-specific download directory:

```python
cdp("Browser.setDownloadBehavior", behavior="allow", downloadPath="/tmp/freewheel_downloads")
```

## Durable UI traps

- Shadow roots are required for reliable element discovery.
- Parameter list content is virtual/accordion-based; searching exact field names is more stable than scroll position.
- Some metrics become disabled based on selected dimensions or inferred sales channel. Check `input.disabled` before clicking.
- The builder may display a note such as `This report reflects data from the 'Programmatic' sales channel.` after deal fields are selected; keep that note in mind when interpreting metrics.
