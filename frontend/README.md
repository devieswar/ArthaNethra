# ArthaNethra Frontend

Angular 19 frontend application for the ArthaNethra AI Financial Risk Investigator.

## Tech Stack

- **Angular 19** — Latest Angular framework
- **Tailwind CSS** — Utility-first CSS framework
- **TypeScript** — Type-safe JavaScript
- **Sigma.js** — Graph visualization (to be integrated)
- **ECharts** — Data visualization charts
- **AG Grid** — Data tables
- **ngx-extended-pdf-viewer** — PDF viewing

## Project Structure

```
src/
├── app/
│   ├── components/          # UI Components
│   │   ├── dashboard/       # Landing page
│   │   ├── upload/          # Document upload
│   │   ├── graph/           # Knowledge graph viewer
│   │   ├── chat/            # AI chatbot
│   │   └── risks/           # Risk dashboard
│   ├── services/            # API services
│   │   └── api.service.ts   # Backend API client
│   ├── models/              # TypeScript models
│   │   ├── document.model.ts
│   │   ├── entity.model.ts
│   │   └── risk.model.ts
│   ├── app.component.ts     # Root component
│   └── app.routes.ts        # Routing configuration
├── environments/            # Environment configs
├── assets/                  # Static assets
├── index.html              # HTML entry point
├── main.ts                 # TypeScript entry point
└── styles.scss             # Global styles
```

## Getting Started

### Install Dependencies

```bash
npm install
```

### Development Server

```bash
npm start
# or
ng serve
```

Navigate to `http://localhost:4200/`

### Build

```bash
npm run build
```

### Linting

```bash
npm run lint
```

### Formatting

```bash
npm run format
```

## Components

### Dashboard
Landing page with feature overview and quick stats.

### Upload
Document upload with drag-and-drop, processing pipeline visualization, and status tracking.

### Graph
Interactive knowledge graph visualization (Sigma.js integration pending).

### Chat
AI-powered chatbot interface for querying financial data.

### Risks
Risk dashboard showing detected financial risks with severity levels.

## Services

### ApiService
Handles all HTTP communication with the backend:
- Document upload
- ADE extraction
- Graph queries
- Risk detection
- Chatbot interactions

## Models

### Document
Document lifecycle management and status tracking.

### Entity
Financial entities (Company, Loan, Subsidiary, etc.) and relationships.

### Risk
Risk detection results with severity levels and citations.

## Routing

- `/` — Dashboard
- `/upload` — Document upload
- `/graph` — Knowledge graph
- `/chat` — AI chatbot
- `/risks` — Risk dashboard

## Styling

Uses Tailwind CSS with custom utility classes defined in `src/styles.scss`:
- `.card` — Card container
- `.btn` — Button styles
- `.badge` — Status badges
- `.spinner` — Loading spinner

## TODO

- [ ] Integrate Sigma.js for graph visualization
- [ ] Add ECharts for KPI dashboards
- [ ] Implement AG Grid for data tables
- [ ] Add ngx-extended-pdf-viewer for evidence viewing
- [ ] Add WebSocket support for real-time updates
- [ ] Implement user authentication
- [ ] Add unit tests
- [ ] Add E2E tests

## Development Guidelines

1. **Components** — Use standalone components
2. **State Management** — Use services with RxJS
3. **Styling** — Use Tailwind CSS utilities
4. **Types** — Define interfaces in models/
5. **API Calls** — Use ApiService, not direct HttpClient
6. **Formatting** — Run `npm run format` before committing
7. **Linting** — Run `npm run lint` before committing

## Build for Production

```bash
npm run build
```

Outputs to `dist/arthanethra/`

## Docker

Build and run with Docker:

```bash
docker build -t arthanethra-frontend .
docker run -p 4200:4200 arthanethra-frontend
```

---

Built for Financial AI Hackathon Championship 2025

