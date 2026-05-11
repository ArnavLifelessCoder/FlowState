# FlowState Frontend

Next.js dashboard for the FlowState adaptive intelligence platform.

## Implemented UI

- JWT-backed login/register flow with token refresh.
- Live dashboard gauges for cognitive load, frustration, and attention.
- Measurement guide explaining behavior-only estimates, score interpretation, sample count, and research references.
- Behavior tracking for keypress, sampled mouse movement, clicks, and focus changes.
- Adaptive UI states driven by `/adaptation/config/{session_id}` for minimal/normal/advanced complexity, sparse/normal/dense density, and slow/normal/fast pace.
- Timeline view with an SVG stress curve, attention/load overlays, session summary metrics, and intervention playback.
- Dashboard attention heatmap with bounded pointer/click points, primary zone detection, and confidence stats.
- Session history, notification gating tester, and team analytics screens.
- Responsive dark dashboard design system in `src/app/globals.css`.

## Local development

```bash
npm install
npm run dev
```

The app expects the API at `NEXT_PUBLIC_API_URL`, defaulting to `http://localhost:8000`.

## Verification

```bash
npm run lint
npm run build
```

Latest verification also included a Playwright smoke check for the auth page, measurement guide, mocked dashboard heatmap render, and minimal/advanced adaptive UI modes.
