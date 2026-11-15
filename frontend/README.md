# HydroGraph frontend

The crew dashboard: vitals with history charts, the 3D biometric body scan and the
health findings, all live from the backend's event stream (`/api/stream/`, shapes in
`../docs/json-shape.md`).

From the repo root: `make sync` once, then `make dev` (backend, this frontend on
http://127.0.0.1:5173 and the simulator together). On its own: `make frontend`. The
browser connects straight to the backend's stream on http://127.0.0.1:8000 (override
with `VITE_BACKEND_URL`); a Vite proxy would buffer the stream.

The header's mission environment dropdown switches the environment for every open
dashboard and for a running simulator (`PUT /api/environment/`); the background palette
follows it (`is-environment-<id>` on the dashboard root).

Readings arrive in SI units; `VITALS_DISPLAY_UNITS` in `src/Constants.ts` converts the
displayed ones (bpm, mmHg, °C, mmol/L, %). Evaluations are the backend's
`nominal`/`warning`/`critical`/`unspecified`.

## Credits and acknowledgments

Thank you to the creators and maintainers whose components, assets, libraries,
documentation, and development tools support HydroGraph.

### Borrowed components and assets

- **[React Bits](https://reactbits.dev/), by David Haz** — the
  [Plasma background](https://reactbits.dev/backgrounds/plasma) supplied the basis
  for the animated dashboard background. Its TypeScript and CSS source was
  retrieved through the component registry MCP server and adapted into
  [VitalsDashboardBackground.tsx](./src/components/VitalsDashboardBackground.tsx)
  with native WebGL and HydroGraph's silver theme. The original component is
  [available upstream](https://github.com/DavidHDev/react-bits/tree/main/src/ts-default/Backgrounds/Plasma).
  Its license notice is preserved [below](#react-bits-license).
- **[NASA](https://www.nasa.gov/)** — the NASA insignia appears in the dashboard
  and browser favicon through [space-apps-logo.png](./src/assets/images/space-apps-logo.png).

HydroGraph's body model was created for this project. Its surface is generated
procedurally in [createBodyGeometry.ts](./src/components/model/createBodyGeometry.ts)
using the project's own shape definitions in
[ModelConstants.ts](./src/components/model/ModelConstants.ts).

### MCP servers and component discovery

The project's MCP server configuration lives in [.mcp.json](./.mcp.json).

- **[shadcn/ui MCP server](https://ui.shadcn.com/docs/mcp)** — configured as
  `component-registries`; provided access to the React Bits Plasma source used
  for the background adaptation.
- **[Context7, by Upstash](https://github.com/upstash/context7)** — configured as
  `context7` for library documentation lookup during development.

The component discovery sources configured in [components.json](./components.json)
are [React Bits](https://reactbits.dev/), [Kokonut UI](https://kokonutui.com/), and
[Magic UI](https://magicui.design/). The Plasma adaptation is the confirmed
component reuse documented here.

### Libraries and development tools

Thank you to these projects and their contributors for the foundations used in
HydroGraph. Dependencies are recorded in [package.json](./package.json), with
resolved versions in [package-lock.json](./package-lock.json).

| Project                                                                                                                                                                             | Contribution to HydroGraph                                                       |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| [React and React DOM](https://react.dev/)                                                                                                                                           | Components, hooks, and browser rendering.                                        |
| [TypeScript](https://www.typescriptlang.org/)                                                                                                                                       | Application types and compiler checks.                                           |
| [Vite](https://vite.dev/) and [its React plugin](https://github.com/vitejs/vite-plugin-react)                                                                                       | Development server, React integration, and production bundling.                  |
| [React Compiler](https://react.dev/learn/react-compiler), [Babel](https://babeljs.io/), and [Rolldown's Babel plugin](https://github.com/rolldown/plugins/tree/main/packages/babel) | The React compilation pipeline configured in [vite.config.ts](./vite.config.ts). |
| [Zustand](https://zustand.docs.pmnd.rs/)                                                                                                                                            | Shared vital readings, history, and request state.                               |
| [Recharts](https://recharts.org/)                                                                                                                                                   | Vital-history charts and tooltips.                                               |
| [Lucide](https://lucide.dev/)                                                                                                                                                       | Dashboard and status icons through `lucide-react`.                               |
| [Three.js](https://threejs.org/)                                                                                                                                                    | Body geometry, materials, MarchingCubes, and OrbitControls.                      |
| [React Three Fiber](https://r3f.docs.pmnd.rs/)                                                                                                                                      | React integration for the body visualization's Three.js scene.                   |
| [Tailwind CSS](https://tailwindcss.com/)                                                                                                                                            | Utility styles and Vite integration alongside the application's CSS.             |
| [Oxc](https://oxc.rs/) and [tsgolint](https://github.com/oxc-project/tsgolint)                                                                                                      | Oxlint, Oxfmt, and type-aware linting through `oxlint-tsgolint`.                 |
| [DefinitelyTyped](https://github.com/DefinitelyTyped/DefinitelyTyped)                                                                                                               | Type declarations supplied by the project's `@types` development dependencies.   |

### Design and documentation references

The references recorded in [the design guide](./design.md) also deserve credit:

- **[Apple Human Interface Guidelines: Materials](https://developer.apple.com/design/human-interface-guidelines/materials)**
  — reference for glass materials and visual hierarchy.
- **[Apple Human Interface Guidelines: Typography](https://developer.apple.com/design/human-interface-guidelines/typography)**
  — reference for interface typography and hierarchy.
- **[MDN Web Docs](https://developer.mozilla.org/)** — web platform documentation,
  including the [backdrop-filter reference](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/backdrop-filter)
  cited in the design guide.

### React Bits license

<details>
<summary>License for the adapted Plasma background</summary>

[VitalsDashboardBackground.tsx](./src/components/VitalsDashboardBackground.tsx) adapts [React Bits Plasma](https://github.com/DavidHDev/react-bits/tree/main/src/ts-default/Backgrounds/Plasma). The following text is from the [upstream license](https://github.com/DavidHDev/react-bits/blob/main/LICENSE.md).

MIT + Commons Clause License Condition v1.0

Copyright (c) 2026 David Haz

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, and distribute the Software **as part of an application, website, or product**, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

### Commons Clause Restriction

You may use this Software, including for any commercial purpose, **so long as you do not sell, sublicense, or redistribute the components themselves-whether alone, in a bundle, or as a ported version.**

The same restriction covers the React Bits tools (Background Studio, Texture Lab, Shape Magic, Center Stage, Sound Lab and any tools added later) and the sounds in the sound library. **You may not sell, sublicense, or redistribute the tools or the sounds themselves, or offer the tools or a substantially similar copy of them as a hosted service-whether alone, in a bundle, or as a ported version.**

What you make with the tools is yours to use. You can use exported code, images, videos, and audio files in any personal or commercial application, website, or product, including paid ones. **You may not sell or redistribute the exports on their own, either individually or as the product itself, such as a sound, texture, background, or template pack.**

### No Warranty

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

</details>
