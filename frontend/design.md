# HydroGraph design guide

## Direction

HydroGraph should feel like a precise health instrument suspended in glass: a neutral charcoal and silver-grey backdrop, visibly translucent panels, crisp white typography, and thin reflective edges. Follow the user's supplied Liquid Glass reference for the material appearance, using grey undertones throughout the theme. The health information should remain clearly readable above that material.

Keep the existing composition. The full-height vitals panel remains on the left; the body scan sits above the assistant on the right. Populate the vitals with the current service's measurements and history. Do not invent metrics, medical interpretations, navigation, or backend behavior.

**Visual signature:** the charcoal and silver-grey backdrop visibly continues through each panel, softened by blur and edged with reflected light. Glass must be apparent at a glance, even while the panel bodies are empty.

## Current baseline and intended changes

The current [dashboard](./src/components/VitalsDashboard.tsx) establishes the spatial structure. Vitals display the five supported metrics with Recharts history, and the procedural body visualization has a region evaluation list. The assistant retains its original empty panel. The [concept image](./src/assets/images/concept_art.png) is a composition reference; its sample readings are not a data contract.

The [theme](./src/assets/css/index.css) and [panel styles](./src/assets/css/VitalsDashboard.css) own this appearance. The earlier pearl canvas and 84% white panel fill looked like solid cards because they obscured almost all backdrop variation. Use an 8% white base fill, a directional reflection, and a richer backdrop so the glass has something visible to transmit.

| Current treatment                          | Target treatment                                                     |
| ------------------------------------------ | -------------------------------------------------------------------- |
| Pale canvas and almost opaque white panels | Charcoal and silver-grey backdrop visible through translucent panels |
| Cyan panel outlines and icon glow          | White edge reflections and small, quiet icons                        |
| Uppercase, widely tracked panel titles     | Sentence case, compact semibold titles                               |
| Flat surface colors                        | Shared backdrop colors transmitted through glass                     |
| Similar emphasis across every panel header | Measurements first, panel titles second, metadata third              |

## Layout and spacing

```text
NASA  HydroGraph

+----------------------------------+-----------------------+
| Vitals                           | Biometric body scan   |
|                                  |                       |
|                                  +-----------------------+
|                                  | Health assistant      |
|                                  |                       |
+----------------------------------+-----------------------+
```

- Preserve the existing `3fr / 2fr` columns, `0.9fr / 1.1fr` right-hand rows, and left panel spanning both rows.
- Preserve the desktop minimum footprint of 1000 × 720 px. Use one desktop composition without breakpoint or device-specific variants.
- Use a 4 px spacing unit. Set outer horizontal and bottom padding to 20 px, panel gaps to 16 px, panel content padding to 24 px, and small related-item gaps to 8 px.
- Keep 16 px above the application header. The main panel's tab bar is 60 px tall; the body-scan and assistant panels have no header. Align tabs and content to the same inset.
- Keep the NASA asset and product identity. Use a 56 px logo height and a 12 px brand gap. Keep the header free of a subtitle and a prominent divider.
- Left-align titles, labels, and prose. Right-align comparable numeric columns when future vitals rows are implemented. Center only the body visualization within its own region.
- Use 14 px radii for the three primary panels, 8–10 px for fields and contained controls, and 4 px for status tags. Avoid capsule shapes. Tabs are plain text with a 2 px underline on the active tab.

## Color system

Define these HydroGraph theme values centrally in the existing [theme stylesheet](./src/assets/css/index.css). Components consume tokens; they do not repeat palette literals. The backdrop colors establish the glass material, while the accent identifies interactive and selected content.

| Token                       | Name             | Value     | Role                                            |
| --------------------------- | ---------------- | --------- | ----------------------------------------------- |
| `--color-background`        | Charcoal         | `#242424` | Canvas base and shadow source                   |
| `--color-backdrop-graphite` | Graphite         | `#3C3C3C` | Broad grey light bands                          |
| `--color-backdrop-silver`   | Silver grey      | `#555555` | Soft side lighting                              |
| `--color-backdrop-mist`     | Mist grey        | `#737373` | Upper-right light                               |
| `--color-surface`           | Reflection white | `#FFFFFF` | Transparent fills and highlights                |
| `--color-surface-opaque`    | Smoke grey       | `#484848` | Fallback when backdrop filtering is unavailable |
| `--color-text`              | Soft white       | `#F7F7F7` | Main text and measurements                      |
| `--color-text-secondary`    | Light grey       | `#DEDEDE` | Labels, units, and supporting copy              |
| `--color-accent`            | Platinum         | `#E7E7E7` | Actions and selection                           |

All base palette values are neutral greys with equal red, green, and blue channels. Do not introduce blue or teal undertones into the canvas, glass, text, or interaction accents. The existing NASA logo retains its original colors.

Status colors live in the same theme: normal and optimal use `--color-status-normal` (`#83D4AC`), unusual uses `--color-status-unusual` (`#EDB65B`), and critical uses `--color-status-critical` (`#FF9C9C`). Use those colors only for evaluations supplied by the application. A missing reading must never be presented as healthy.

Chart colors identify labeled series, independently of evaluation: heart rate `#EF8585`, systolic pressure `#C6A4EB`, diastolic pressure `#88BCE8`, blood sugar `#83D4AC`, temperature `#EDC576`, and sleep `#9BB3EC`. Define these as `--color-chart-*` tokens in the theme. Keep the canvas, glass, icons, and interaction accents neutral.

Derive supporting treatments from these tokens with the project's existing `color-mix(in srgb, ...)` convention:

| Treatment       | Recipe                          |
| --------------- | ------------------------------- |
| Accent wash     | Accent 12%, transparent 88%     |
| Glass fill      | Surface 8%, transparent 92%     |
| Glass tint      | Background 80%, transparent 20% |
| Border          | Surface 28%, transparent 72%    |
| Divider         | Surface 16%, transparent 84%    |
| Soft shadow ink | Background 30%, transparent 70% |

Keep ordinary text neutral white. Vital icons take their chart series color; tab icons and the environment icon each take one chart color. The backdrop supplies tonal variation; panel outlines should read as reflections rather than neon strokes. Use the platinum accent for selection and actions. Label each chart series explicitly; reserve semantic text colors for evaluation statuses.

## Materials and light

Apple's materials guidance distinguishes functional Liquid Glass from content materials. This web design deliberately follows the user's supplied reference more closely by extending visible glass to the three panel shells. Keep future dense data and messages readable within those shells, without stacking additional blur layers.

Use three material levels:

1. **Canvas:** a 125-degree sweep of charcoal, graphite, and silver grey, with broad silver-grey light from the left and mist grey from the upper right. Layer the locally adapted React Bits Plasma effect over this base: broad silver folds, slow continuous motion, soft highlights, and no grain or cursor tracking. Read the effect color from the existing silver theme token. The light bands must cross panel boundaries so their transmission is visible. Keep the backdrop smooth and free of fine detail. Retain the static sweep when WebGL is unavailable and show a quiet status message.
2. **Panel glass:** a glass-tint layer under an 8% white base fill, with no reflection gradient. Use `backdrop-filter: blur(20px)` without saturation enhancement, so the Plasma folds stay visible through the glass. The tint keeps text at WCAG AA contrast over the brightest environment backdrops; status labels sit on a glass-tint fill.
3. **Edges and depth:** a 1 px translucent white border and a `0 8px 24px` shadow using the shadow token. No inset edge highlights. Keep divider lines quieter than outer edges. Future inner controls should use simple fills rather than another backdrop filter.

Apply transparency to the background color, never to a whole panel's `opacity`; text and icons must retain their intended color. Use backdrop filtering rather than `filter: blur(...)`, which would blur the content itself.

Provide the smoke-grey opaque surface as the default and enhance it inside a feature-based `@supports` rule. If backdrop filtering is unavailable, white text must remain readable. This is a capability fallback, not a viewport variant. CSS blur, reflections, and transparency approximate glass; they do not reproduce Apple's native refraction system.

Keep edge reflections thin and neutral. The Plasma canvas is the single animated backdrop; panel edges remain still. Avoid cyan icon glow, thick luminous outlines, scan beams, grain textures, and refraction shaders.

## Typography

Use Apple's UI font throughout: `-apple-system, BlinkMacSystemFont, "SF Pro Text", "SF Pro Display", "Helvetica Neue", system-ui, sans-serif`. It uses the platform's interface font, including Apple's system face where available, without downloading or redistributing San Francisco. The same hierarchy and layout apply across platforms; glyph shapes depend on the installed system font.

The improvement comes from size, weight, spacing, and contrast. Avoid introducing a display face, a futuristic font, or monospace styling for ordinary labels.

| Role                            | Size / line height | Weight                | Tracking   |
| ------------------------------- | ------------------ | --------------------- | ---------- |
| Product name                    | 22 / 28 px         | 600                   | `-0.03em`  |
| Panel title                     | 17 / 24 px         | 600                   | `-0.015em` |
| Primary measurement, when added | 32 / 36 px         | 600                   | `-0.03em`  |
| Body and control text           | 14 / 21 px         | 400; 500 for controls | Normal     |
| Supporting label                | 13 / 18 px         | 400                   | Normal     |
| Timestamp or compact metadata   | 12 / 16 px         | 400                   | Normal     |

Use sentence case for tab labels: “Vitals,” “All measurements,” “Trends,” and “Advice.” Remove uppercase and wide tracking utilities. Use secondary text tokens instead of lowering opacity on whole text groups. Set numeric readings to tabular numerals so updates retain their alignment; units stay smaller and secondary.

## Component treatment

### Vitals

The [vitals panel](./src/components/VitalsPanel.tsx) is the primary reading surface. Use a soft-white Activity icon at 20 px with a consistent 1.75 px stroke and the shared panel-title treatment. Keep its interior visually quiet.

Use aligned rows with light separators and generous space around each measurement. Show heart rate, blood pressure, blood sugar, body temperature, and daily sleep from their existing stores. Keep labels, units, timestamps, and status meanings distinct. Pair systolic and diastolic measurements in one row and label both history series. Show actual measurement dates separately from history timestamps; the service's current samples do not all share a measurement date.

Use fine Recharts strokes with restrained fills and hover details. The history store owns the requested interval, shared history, loading state, and error state. Keep the Vitals tab free of time-range buttons; period selection belongs to the Trends tab. Distinguish unavailable readings from normal evaluations. Do not add decorative footer copy such as “Sample data” or “Recorded history · Times shown locally.” Avoid a separate glowing card, colored icon disc, and circular gauge for every reading. Those additions would compete with the data.

### Biometric body scan

The [body-scan panel](./src/components/BodyScan.tsx) contains a procedural faceless human with soft mineral shading and a relaxed stance. It has no header and uses the same glass material as the main panel. Dragging rotates the figure; there is no automatic animation.

The body uses `--color-body-neutral` (`#A6A6A6`). Explicit unusual evaluations use `--color-status-unusual` (`#EDB65B`) and critical evaluations use `--color-status-critical` (`#FF9C9C`) on their named surface regions. Normal, optimal, and unmeasured regions remain grey; grey alone does not establish that a measurement exists. The current service supplies sample readings. Define all palette values in the theme stylesheet, and keep region geometry and lighting settings in [ModelConstants.ts](./src/components/model/ModelConstants.ts).

Keep labels on a stable reading surface beside the model. Group supplied evaluations into head and neck, upper body, arms, lower body, and joints; show the highest supplied severity for each group, or “No reading” when none is supplied. These are reading-linked regions, not new diagnoses. Avoid holographic rings, a neon floor, and decorative scanning motion. Organs and anatomical diagnostic detail are outside the current model.

### Health assistant

The [assistant panel](./src/components/HealthAssistant.tsx) should feel like a calm conversation surface. It has no header.

Keep the findings and conversation in one independently scrolling surface, with the header and 40 px composer fixed within the panel. Use a thin neutral scrollbar and contain wheel scrolling within the transcript. Follow new replies while the reader is near the bottom; preserve their position when they scroll up, with a “Latest message” control to resume following. Initial findings must remain visible without moving the dashboard viewport.

Use translucent smoke-grey assistant messages and a faint accent wash for user messages. Starter, latest-message, and send buttons use neutral white text, translucent fills, thin reflective borders, and visible keyboard focus. Keep the disabled send state readable without lowering the opacity of the whole control. Do not add demonstration conversations or unsupported health claims as part of a visual restyle.

### Mission environment

Use the shared glass fill, directional reflection, edge highlight, and blur for the environment container. The selector uses a translucent fill, a neutral chevron, and a 40 px height. Enhance the native select with `appearance: base-select` where supported so its open picker also uses glass, softly rounded options, and a quiet selection wash. Preserve native keyboard navigation and use the smoke-grey surface as the fallback for browsers without customizable selects or backdrop filtering.

### Interaction and state

Use color, border, and small shadow changes for interactive controls. Keep transitions to 160 ms with an ease-out curve. Panels are containers and should not lift or scale on hover. Keep looping motion confined to the slow Plasma backdrop; pause rendering when the page is hidden. Avoid independent entrance animations on each panel.

Selected controls use the accent wash and accent text; primary actions use solid accent with charcoal text. Disabled, loading, empty, and failed states must remain distinguishable. Show loading and failure through explicit content rather than decorative color alone. Do not turn the current empty panel bodies into invented live readings.

## Implementation boundaries

- This guide specifies the active visual target and must stay aligned with the implemented theme.
- Update existing theme tokens and shared panel rules first, then adjust conflicting utilities in the dashboard and panel components. Do not pile overrides onto the old neon treatments.
- Keep component styles scoped under `.vitals-dashboard` and its existing BEM-like classes. Use explicit classes for inner elements and retain existing component boundaries.
- Keep visual tokens in CSS. Place any new application configuration in the existing [constants module](./src/Constants.ts). Do not introduce another theme system or constants file.
- [VitalsDashboardBackground.tsx](./src/components/VitalsDashboardBackground.tsx) adapts the React Bits Plasma volume and composite shaders to this fixed dashboard treatment. It uses native WebGL with capped rendering resolution and releases its animation frame, observer, event listeners, and GPU resources on teardown. Its speed, scale, lighting, and rendering limits live in `VITALS_BACKGROUND` in the constants module.
- The installed stack already includes plain CSS, Tailwind, and Lucide icons. This direction requires no new component library, font package, motion dependency, or image asset.
- Retain the fixed desktop composition. Follow [project instructions](./AGENTS.md) for CSS scope, state ownership, effects, and permitted checks.

## Visual review criteria

- The original three-panel arrangement is immediately recognizable.
- The first impression is transparent glass over a neutral charcoal and silver-grey backdrop, with crisp white text.
- Every tab label uses the same sentence case, scale, and inset.
- Text and numeric readings remain crisp over the lightest and darkest parts of the backdrop.
- Backdrop light bands remain visible through the panel interiors; panels must not resemble opaque painted cards.
- Bright upper edges and softer lower edges make the material thickness apparent without a neon glow.
- Dividers recede and the old cyan outlines and glows are gone.
- The NASA identity remains present without dominating the health information.
- The opaque fallback retains the same hierarchy and geometry.
- Plasma remains neutral silver, moves slowly behind the glass, and does not intercept body-model dragging. If the animation cannot render, the static backdrop remains visible with a status message.
- Review the actual rendered page before describing the implemented design as verified. This document alone does not establish browser appearance or performance.

## References

- [React Bits Plasma](https://reactbits.dev/backgrounds/plasma) — source for the adapted background shaders; see the [React Bits license](./README.md#react-bits-license).
- [Apple Human Interface Guidelines: Materials](https://developer.apple.com/design/human-interface-guidelines/materials) — functional glass and content-material hierarchy.
- [Apple Human Interface Guidelines: Typography](https://developer.apple.com/design/human-interface-guidelines/typography) — interface typography and hierarchy.
- [MDN: backdrop-filter](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/backdrop-filter) — transparency requirements, backdrop roots, and browser support.

The palette, dimensions, type scale, and CSS material recipes above are HydroGraph design decisions, not copied Apple specifications.
