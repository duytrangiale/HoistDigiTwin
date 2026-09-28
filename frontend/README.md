# HoistDigiTwin dashboard

The frontend for the public dashboard, built with React and Vite. See
`phase7_plan.md` at the repo root for the design behind it, and the main
`README.md` for how this fits into the rest of the project.

## Running locally

```
npm install
npm run dev
```

Talks to the backend at `http://127.0.0.1:8000` by default (see
`src/serve/api.py`). Set `VITE_API_URL` to point at a different backend.
