# Atlas Frontend Scaffolding (Look & Feel Replica)

This document captures the frontend scaffolding/signals observable from `https://atlas.subcpartner.com` as of **2026-03-02** and turns them into a reproducible starter setup.

## Scope and confidence

- This is based on the public production HTML/CSS/JS bundles (no authenticated source access).
- Confidence is high for framework, theming system, and core design tokens.
- Confidence is medium for exact internal app architecture beyond what bundle strings expose.

## 1) Identified stack (from live bundle)

- Build tool: **Vite** (`/assets/index-*.js` module entry)
- UI runtime: **React** (`#root` mount)
- Design system: **Mantine**
  - `@mantine/core`
  - `@mantine/dates`
  - `@mantine/notifications`
  - `@mantine/use-form`
  - `@mantine/modals`
  - `@mantine/tiptap`
- Routing: **react-router-dom** (bundle comment also shows `react-router v7.13.0`)
- Date handling present: **dayjs**
- Auth-related libs present: strings for **msal** and **oidc**

Not detected in bundle string fingerprints:
- `@tanstack/*`
- `zustand`
- `redux`
- `axios`

## 2) Global style/theming signals extracted

## Typography

- Global font face present:

```css
@font-face{font-family:Montserrat;src:url(/assets/Montserrat-VariableFont_wght-CiIa1Ne8.ttf)}
:root{font-family:Montserrat}
```

- Mantine base body style active:

```css
body{
  margin:0;
  font-family:var(--mantine-font-family);
  font-size:var(--mantine-font-size-md);
  line-height:var(--mantine-line-height);
  background-color:var(--mantine-color-body);
  color:var(--mantine-color-text);
}
#root{height:100%;width:100%;margin:0}
```

## Mantine sizing rhythm (from css vars)

- Radius default: `md`
- Spacing: `xs=10`, `sm=12`, `md=16`, `lg=20`, `xl=32`
- Font sizes: `xs=12`, `sm=14`, `md=16`, `lg=18`, `xl=20`
- Additional custom size detected: `xxs=10px`
- Breakpoints:
  - `xs: 36em`
  - `sm: 48em`
  - `md: 62em`
  - `lg: 75em`
  - `xl: 88em`

## Color system

Mantine palette exists, but Atlas adds brand aliases:

```js
subCColors = {
  primaryDark: colorsTuple("#01193E"),
  primary: colorsTuple("#32A3FC"),
  primaryLight: colorsTuple("#E5ECF3"),
  primaryBackground: colorsTuple("#F1F6F8")
}
```

Theme core values extracted:

```js
theme = {
  defaultRadius: "md",
  primaryColor: "primaryDark",
  fontFamily: "Montserrat",
  colors: subCColors,
  fontSizes: { xxs: "10px" },
  ...
}
```

Custom variant resolver behavior for `light` variant and primary colors:

```js
variantColorResolver = (input) => {
  const base = defaultVariantColorsResolver(input)
  if (input.variant === "light" && (input.color === "primary" || input.color === "primaryDark")) {
    return {
      ...base,
      background: "var(--mantine-color-primaryLight-6)",
      hover: darken(input.theme.colors.primaryLight[6], 0.02)
    }
  }
  return base
}
```

## Component defaults extracted

From bundle theme extension:

- `Accordion`: `chevronPosition: "left"`
- `DateInput`: `valueFormat: "DD/MM/YY"`
- `Text`: default `size: "xs"`
- `Modal` and `Drawer`:
  - `padding: 24`
  - `scrollAreaComponent: ScrollAreaAutosize`
  - `styles.content.padding = 0`
  - close button icon wrapped in `ThemeIcon` (`size:40`, `radius:20`, `variant:"light"`, `color:"primary"`)
- `NumberInput`:
  - `hideControls: true`
  - `decimalSeparator: ","`
  - `thousandSeparator: "."`
  - `decimalScale: 2`
- `ScrollArea`: `scrollbarSize: 6`

## Notifications/modals behavior signals

- `Notifications` is mounted
- `ModalsProvider` is used
- Notifications store defaults in bundle:
  - `defaultPosition: "bottom-right"`
  - `limit: 5`

## 3) Replica frontend scaffold (recommended)

## Project structure

```text
atlas-clone/
  frontend/
    index.html
    package.json
    vite.config.ts
    tsconfig.json
    src/
      main.tsx
      app/
        AppShell.tsx
        router.tsx
        providers/
          ThemeProvider.tsx
          NotificationsProvider.tsx
          ModalsProvider.tsx
      assets/
        fonts/
          Montserrat-VariableFont_wght.ttf
        logos/
          subc-logo.svg
          subc-short-logo.svg
      theme/
        colors.ts
        logos.ts
        variantResolver.ts
        mantineTheme.ts
      features/
        auth/
          api.ts
          session.ts
          LoginView.tsx
        dashboard/
          DashboardView.tsx
      shared/
        components/
        hooks/
        lib/
          dayjs.ts
          apiClient.ts
      styles/
        global.css
  backend/
    app/
      main.py
      api/
      services/
      auth/
      settings.py
    pyproject.toml
```

## Frontend dependencies

Use this baseline:

```json
{
  "dependencies": {
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "react-router-dom": "^7.13.0",
    "dayjs": "^1.11.13",
    "@mantine/core": "^7.17.0",
    "@mantine/dates": "^7.17.0",
    "@mantine/hooks": "^7.17.0",
    "@mantine/notifications": "^7.17.0",
    "@mantine/modals": "^7.17.0",
    "@mantine/form": "^7.17.0",
    "@mantine/tiptap": "^7.17.0",
    "@tabler/icons-react": "^3.34.0",
    "@tiptap/react": "^2.11.0",
    "@tiptap/starter-kit": "^2.11.0"
  },
  "devDependencies": {
    "vite": "^5.4.0",
    "typescript": "^5.7.0",
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0"
  }
}
```

Notes:
- Mantine package versions should stay aligned to avoid peer mismatch.
- If you need Atlas-like enterprise auth UX later, add `@azure/msal-browser`/`oidc-client-ts` only when needed.

## 4) Exact theme scaffold to copy

`src/theme/colors.ts`

```ts
import { colorsTuple } from "@mantine/core";

export const subCColors = {
  primaryDark: colorsTuple("#01193E"),
  primary: colorsTuple("#32A3FC"),
  primaryLight: colorsTuple("#E5ECF3"),
  primaryBackground: colorsTuple("#F1F6F8"),
};
```

`src/theme/variantResolver.ts`

```ts
import { darken, defaultVariantColorsResolver, type VariantColorsResolver } from "@mantine/core";

export const variantColorResolver: VariantColorsResolver = (input) => {
  const base = defaultVariantColorsResolver(input);

  if (input.variant === "light" && (input.color === "primary" || input.color === "primaryDark")) {
    return {
      ...base,
      background: "var(--mantine-color-primaryLight-6)",
      hover: darken(input.theme.colors.primaryLight[6], 0.02),
    };
  }

  return base;
};
```

`src/theme/mantineTheme.ts`

```ts
import {
  createTheme,
  ScrollAreaAutosize,
  Accordion,
  DateInput,
  Text,
  Modal,
  Drawer,
  NumberInput,
  ScrollArea,
  ThemeIcon,
} from "@mantine/core";
import { IconX } from "@tabler/icons-react";
import { subCColors } from "./colors";
import { variantColorResolver } from "./variantResolver";

export const atlasTheme = createTheme({
  defaultRadius: "md",
  primaryColor: "primaryDark",
  fontFamily: "Montserrat, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif",
  colors: subCColors,
  variantColorResolver,
  fontSizes: {
    xxs: "10px",
  },
  components: {
    Accordion: Accordion.extend({
      defaultProps: { chevronPosition: "left" },
    }),
    DateInput: DateInput.extend({
      defaultProps: { valueFormat: "DD/MM/YY" },
    }),
    Text: Text.extend({
      defaultProps: { size: "xs" },
    }),
    Modal: Modal.extend({
      defaultProps: {
        padding: 24,
        scrollAreaComponent: ScrollAreaAutosize,
        styles: { content: { padding: 0 } },
        closeButtonProps: {
          icon: (
            <ThemeIcon color="primary" size={40} radius={20} variant="light">
              <IconX />
            </ThemeIcon>
          ),
        },
      },
    }),
    Drawer: Drawer.extend({
      defaultProps: {
        padding: 24,
        scrollAreaComponent: ScrollAreaAutosize,
        styles: { content: { padding: 0 } },
        closeButtonProps: {
          icon: (
            <ThemeIcon color="primary" size={40} radius={20} variant="light">
              <IconX />
            </ThemeIcon>
          ),
        },
      },
    }),
    NumberInput: NumberInput.extend({
      defaultProps: {
        hideControls: true,
        decimalSeparator: ",",
        thousandSeparator: ".",
        decimalScale: 2,
      },
    }),
    ScrollArea: ScrollArea.extend({
      defaultProps: { scrollbarSize: 6 },
    }),
  },
});
```

`src/main.tsx`

```tsx
import "@mantine/core/styles.css";
import "@mantine/dates/styles.css";
import "@mantine/notifications/styles.css";
import "@mantine/tiptap/styles.css";
import "./styles/global.css";

import React from "react";
import ReactDOM from "react-dom/client";
import { MantineProvider } from "@mantine/core";
import { ModalsProvider } from "@mantine/modals";
import { Notifications } from "@mantine/notifications";
import { BrowserRouter } from "react-router-dom";
import { atlasTheme } from "./theme/mantineTheme";
import { AppShell } from "./app/AppShell";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <MantineProvider theme={atlasTheme} defaultColorScheme="light">
      <ModalsProvider>
        <Notifications position="bottom-right" limit={5} />
        <BrowserRouter>
          <AppShell />
        </BrowserRouter>
      </ModalsProvider>
    </MantineProvider>
  </React.StrictMode>
);
```

`src/styles/global.css`

```css
@font-face {
  font-family: "Montserrat";
  src: url("../assets/fonts/Montserrat-VariableFont_wght.ttf") format("truetype");
  font-display: swap;
}

:root {
  font-family: Montserrat;
}

html,
body,
#root {
  width: 100%;
  height: 100%;
  margin: 0;
}
```

## 5) Python backend pairing (so logic is not C#)

Use frontend as above, with Python API behind it.

Recommended backend scaffold:

- Framework: **FastAPI**
- Auth/session: cookie-based session + optional token fallback
- DB: SQLAlchemy + pyodbc (SQL Server)
- Endpoint namespace: `/api/*`

Minimal backend tree:

```text
backend/app/
  main.py
  settings.py
  db.py
  models.py
  schemas.py
  routers/
    auth.py
    employees.py
    jobs.py
```

Expected frontend service layer shape:

- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/me`
- `GET /api/employees`
- feature endpoints (`/api/jobs`, etc.)

## 6) Brand variants detected in bundle

The bundle includes alternate brand themes built from the same base theme:

- `spGreenTheme`
- `jibFlexBlueTheme`

Detected color sets:

- `spGreenTheme`:
  - `primaryDark: #0E3838`
  - `primary: #096F4E`
  - `primaryLight: #B4FFC3`
  - `primaryBackground: #F1EEEC`
- `jibFlexBlueTheme`:
  - `primaryDark: #1F3666`
  - `primary: #008ACC`
  - `primaryLight: #EEEEF0`
  - `primaryBackground: #F9F7F0`

If you need exact Atlas behavior, keep base theme + runtime brand override support.

## 7) Verification checklist for “same look and feel”

1. Montserrat variable font loaded and used as root/theme font.
2. Mantine theme uses:
   - `defaultRadius: "md"`
   - `primaryColor: "primaryDark"`
   - custom color aliases above.
3. Date and numeric formatting defaults match:
   - Date input `DD/MM/YY`
   - Decimal `,` and thousand `.`
4. Modal/drawer close button style matches ThemeIcon treatment.
5. Notifications shown bottom-right with limit 5.
6. Router + app shell spacing follows Mantine spacing defaults (10/12/16/20/32).

## 8) Known limits

- Exact page-level layouts/components after login cannot be fully recovered from minified bundles alone.
- This document reproduces the platform/theme scaffold and interaction primitives that drive the visual identity.

