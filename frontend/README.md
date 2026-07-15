# Kidney-Genetics Database Frontend

The frontend is a Vue 3, TypeScript, Vite SSG application using Tailwind CSS,
Pinia, and typed API clients under `src/api/`.

## Prerequisites and Install

Use Node.js >=22.18.0. From the repository root, install the locked frontend
dependencies with:

```bash
make install-frontend
```

The equivalent component-local command is:

```bash
cd frontend && npm ci
```

`package-lock.json` is the reproducible dependency source for local development
and CI. Commit lockfile changes made when intentionally changing dependencies.

## Run the Development Server

From the repository root:

```bash
make frontend
```

Vite serves the application at <http://localhost:5173>. To use a locally
running backend, set `VITE_API_BASE_URL=http://localhost:8000` in a local,
uncommitted `.env` file and start the backend with `make backend`.

The direct command is:

```bash
cd frontend && npm run dev
```

## Build and Test

Run the complete frontend quality gate from the root:

```bash
make check-frontend
```

It runs ESLint, Prettier verification, the Vite SSG build, and the non-watch
Vitest suite. Focused commands are:

```bash
cd frontend && npm run lint:check
cd frontend && npm run format:check
cd frontend && npm run test:run
cd frontend && npm run build
cd frontend && npm run build:full  # build plus static gene-page generation
```

`npm run lint` and `npm run format` rewrite files; use the check variants for
verification-only work.

## End-to-End Tests

Playwright specifications live in `e2e/` and expect a development server at
<http://localhost:5173>. Start `make frontend` in another terminal, then run:

```bash
cd frontend && npm run test:e2e
```

For interactive debugging, use `npm run test:e2e:ui`. If the Playwright browser
runtime is absent on a new machine, install it with `npx playwright install`.
