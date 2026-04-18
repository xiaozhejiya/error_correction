# Design System Inspiration of Linear

## 1. Visual Theme & Atmosphere

Linear's website is a masterclass in dark-mode-first product design — a near-black canvas (`#08090a`) where content emerges from darkness like starlight. The overall impression is one of extreme precision engineering: every element exists in a carefully calibrated hierarchy of luminance, from barely-visible borders (`rgba(255,255,255,0.05)`) to soft, luminous text (`#f7f8f8`). This is not a dark theme applied to a light design — it is darkness as the native medium, where information density is managed through subtle gradations of white opacity rather than color variation.

The typography system is built entirely on Inter Variable with OpenType features `"cv01"` and `"ss03"` enabled globally, giving the typeface a cleaner, more geometric character. Inter is used at a remarkable range of weights — from 300 (light body) through 510 (medium, Linear's signature weight) to 590 (semibold emphasis). The 510 weight is particularly distinctive: it sits between regular and medium, creating a subtle emphasis that doesn't shout. At display sizes (72px, 64px, 48px), Inter uses aggressive negative letter-spacing (-1.584px to -1.056px), creating compressed, authoritative headlines that feel engineered rather than designed. Berkeley Mono serves as the monospace companion for code and technical labels, with fallbacks to ui-monospace, SF Mono, and Menlo.

The color system is almost entirely achromatic — dark backgrounds with white/gray text — punctuated by a single brand accent: Linear's signature indigo-violet (`#5e6ad2` for backgrounds, `#7170ff` for interactive accents). This accent color is used sparingly and intentionally, appearing only on CTAs, active states, and brand elements. The border system uses ultra-thin, semi-transparent white borders (`rgba(255,255,255,0.05)` to `rgba(255,255,255,0.08)`) that create structure without visual noise, like wireframes drawn in moonlight.

**Key Characteristics:**
- Dark-mode-native: `#08090a` marketing background, `#0f1011` panel background, `#191a1b` elevated surfaces
- Inter Variable with `"cv01", "ss03"` globally — geometric alternates for a cleaner aesthetic
- Signature weight 510 (between regular and medium) for most UI text
- Aggressive negative letter-spacing at display sizes (-1.584px at 72px, -1.056px at 48px)
- Brand indigo-violet: `#5e6ad2` (bg) / `#7170ff` (accent) / `#828fff` (hover) — the only chromatic color in the system
- Semi-transparent white borders throughout: `rgba(255,255,255,0.05)` to `rgba(255,255,255,0.08)`
- Button backgrounds at near-zero opacity: `rgba(255,255,255,0.02)` to `rgba(255,255,255,0.05)`
- Multi-layered shadows with inset variants for depth on dark surfaces
- Success green (`#27a644`, `#10b981`) used only for status indicators

## 2. Color Palette & Roles

### Background Surfaces
- **Marketing Black** (`#010102` / `#08090a`): The deepest background — the canvas for hero sections and marketing pages.
- **Panel Dark** (`#0f1011`): Sidebar and panel backgrounds. One step up from the marketing black.
- **Level 3 Surface** (`#191a1b`): Elevated surface areas, card backgrounds, dropdowns.
- **Secondary Surface** (`#28282c`): The lightest dark surface — used for hover states and slightly elevated components.

### Text & Content
- **Primary Text** (`#f7f8f8`): Near-white with a barely-warm cast. Not pure white, preventing eye strain.
- **Secondary Text** (`#d0d6e0`): Cool silver-gray for body text, descriptions.
- **Tertiary Text** (`#8a8f98`): Muted gray for placeholders, metadata.
- **Quaternary Text** (`#62666d`): The most subdued text — timestamps, disabled states.

### Brand & Accent
- **Brand Indigo** (`#5e6ad2`): Primary brand color — CTA button backgrounds, brand marks.
- **Accent Violet** (`#7170ff`): Brighter variant for interactive elements — links, active states.
- **Accent Hover** (`#828fff`): Lighter variant for hover states on accent elements.

### Border & Divider
- **Border Subtle** (`rgba(255,255,255,0.05)`): Ultra-subtle semi-transparent border — the default.
- **Border Standard** (`rgba(255,255,255,0.08)`): Standard semi-transparent border for cards, inputs.
- **Border Primary** (`#23252a`): Solid dark border for prominent separations.

## 3. Typography Rules

### Font Family
- **Primary**: `Inter Variable` with `"cv01", "ss03"` OpenType features
- **Monospace**: `Berkeley Mono`

### Key Weights
- **400**: Reading text
- **510**: Emphasis/UI (Linear's signature weight)
- **590**: Strong emphasis

### Display Sizes Letter Spacing
- 72px: -1.584px
- 64px: -1.408px
- 48px: -1.056px
- 32px: -0.704px
- Below 16px: normal

## 4. Component Stylings

### Buttons
- **Ghost**: `rgba(255,255,255,0.02)` bg, `1px solid rgb(36,40,44)` border, 6px radius
- **Subtle**: `rgba(255,255,255,0.04)` bg, 6px radius
- **Primary Brand**: `#5e6ad2` bg, white text, 6px radius
- **Pill**: transparent bg, 9999px radius, `1px solid rgb(35,37,42)` border

### Cards & Containers
- Background: `rgba(255,255,255,0.02)` to `rgba(255,255,255,0.05)` (never solid)
- Border: `1px solid rgba(255,255,255,0.08)`
- Radius: 8px (standard), 12px (featured)

### Inputs
- Background: `rgba(255,255,255,0.02)`
- Border: `1px solid rgba(255,255,255,0.08)`
- Radius: 6px

## 5. Layout Principles

### Spacing System
- Base unit: 8px
- Primary rhythm: 8px, 16px, 24px, 32px

### Border Radius Scale
- 2px: Inline badges, toolbar buttons
- 6px: Buttons, inputs
- 8px: Cards, dropdowns
- 12px: Panels, featured cards
- 9999px: Chips, pills

## 6. Depth & Elevation

Surface elevation via background opacity: `rgba(255,255,255, 0.02 -> 0.04 -> 0.05)` — never solid backgrounds on dark.

## 7. Do's and Don'ts

### Do
- Use `#f7f8f8` for primary text — not pure `#ffffff`
- Keep button backgrounds nearly transparent
- Reserve brand indigo for primary CTAs only
- Use semi-transparent white borders

### Don't
- Don't use pure white as primary text
- Don't use solid colored backgrounds for buttons
- Don't use weight 700 (bold) — max is 590
- Don't use drop shadows for elevation on dark surfaces
