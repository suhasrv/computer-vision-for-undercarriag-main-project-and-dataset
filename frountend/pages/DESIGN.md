# Design System Specification: The Obsidian Lens

## 1. Overview & Creative North Star
**Creative North Star: "The Precise Observer"**

This design system is engineered to bridge the gap between industrial machine precision and high-end editorial clarity. Moving away from the "dashboard fatigue" of typical data-heavy interfaces, we embrace a philosophy of **Tactile Futurism**. 

The system breaks the standard "grid-of-boxes" template by utilizing intentional asymmetry, deep tonal layering, and "breathing" data visualizations. We treat the interface not as a flat screen, but as a high-precision optical instrument. Transitions are fluid, surfaces are layered like stacked lens elements, and the contrast between the obsidian void of the background and the electric cyan highlights creates a sense of immediate, high-stakes focus.

---

## 2. Colors & Surface Philosophy

The palette is rooted in a "Deep Obsidian" foundation, utilizing cold grays and blacks to create a void where data can truly shine.

### The Color Tokens
*   **Background / Surface:** `#131313` (The Obsidian Void)
*   **Primary (Accent):** `#e9feff` (Glacial White) / `#00dce5` (Electric Cyan) — Used exclusively for critical data points, defects, and "active" states.
*   **Error:** `#ffb4ab` — Reserved for critical system failures or high-priority defects.
*   **Neutral Tones:** Slate grays (`#c6c6c9`, `#454749`) provide structural hierarchy without breaking the dark mode immersion.

### The "No-Line" Rule
To maintain a premium, industrial feel, **1px solid borders are prohibited for sectioning.** 
*   **Boundary Definition:** Use background color shifts. A `surface-container-low` (`#1c1b1b`) section sitting on a `surface` (`#131313`) background is enough to define a boundary.
*   **Tonal Nesting:** UI elements are layered like physical materials. An inner card should use `surface-container-highest` (`#353534`) to "float" above a `surface-container` background.

### Signature Textures
*   **The Glass & Gradient Rule:** Use Glassmorphism for floating panels. Apply `surface` colors at 60% opacity with a `24px` backdrop blur.
*   **Bespoke Gradients:** Primary actions should use a subtle linear gradient from `primary_fixed` (`#63f7ff`) to `primary_fixed_dim` (`#00dce5`) at a 135-degree angle to simulate the glow of a high-tech HUD.

---

## 3. Typography: The Editorial Scale

We utilize a dual-font approach to balance industrial precision (Manrope) with functional clarity (Inter).

*   **Display & Headlines (Manrope):** These are our "Hero" moments. Use `display-lg` (3.5rem) with tight letter-spacing (-0.02em) to create a bold, cinematic impact in hero sections.
*   **Body & Labels (Inter):** Geometric and neutral. `body-md` (0.875rem) is the workhorse for data visualization descriptions. 
*   **Editorial Intent:** Use extreme contrast in scale. A `display-sm` headline paired with a `label-sm` technical timestamp creates an "Intelligence Report" aesthetic that feels authoritative and precise.

---

## 4. Elevation & Depth: Tonal Layering

We reject traditional drop shadows in favor of **Tonal Elevation**.

*   **The Layering Principle:** Depth is achieved by stacking the surface-container tiers.
    1.  **Level 0 (Base):** `surface_dim` (`#131313`)
    2.  **Level 1 (Sections):** `surface_container_low` (`#1c1b1b`)
    3.  **Level 2 (Cards):** `surface_container_high` (`#2a2a2a`)
    4.  **Level 3 (Floating Modals):** `surface_bright` (`#3a3939`) + Glassmorphism.
*   **The Ghost Border:** If a visual separator is strictly required for accessibility, use the `outline_variant` token at 15% opacity. It should feel like a faint reflection on a glass edge, not a stroke.
*   **Ambient Shadows:** For high-level modals, use a "Color-Tinted Glow" instead of a black shadow. Use `surface_tint` (`#00dce5`) at 5% opacity with a `48px` blur.

---

## 5. Components

### Large Hero Sections
Hero sections must feature a "Precision Scan" aesthetic. Combine `display-lg` typography with a background featuring a subtle radial gradient (from `surface_container_low` to `surface`).

### Data Visualization Cards
*   **Rule:** Forbid divider lines. Use `0.75rem` (xl) roundedness and vertical white space to separate metrics.
*   **Styling:** Use `surface_container_highest` for the card body. Metrics should be rendered in `primary_fixed` to draw the eye immediately to the "findings."

### Buttons
*   **Primary:** High-gloss gradient (`primary_fixed` to `primary_fixed_dim`). Text in `on_primary_fixed` (Deep Teal).
*   **Secondary:** Ghost style. No background, `outline` border at 20%, text in `secondary_fixed`.
*   **Tertiary:** Text-only, capitalized `label-md` with 1px letter spacing for a technical, "coded" look.

### Input Fields
*   **State:** Default state uses `surface_container_lowest`. On focus, the background remains dark, but a 1px "Ghost Border" of `primary` at 40% appears, mimicking an active sensor.

### New Component: The "Defect Chip"
A specialized high-contrast pill used for CV highlights.
*   **Background:** `error_container` (`#93000a`) at 20% opacity.
*   **Stroke:** 1px `error` (`#ffb4ab`) at 50% opacity.
*   **Text:** `label-sm` in `error` color.

---

## 6. Do’s and Don’ts

### Do:
*   **Use Asymmetry:** Place a large metric in the top-left and a small, high-detail list in the bottom-right of a container to create a "scanning" visual flow.
*   **Embrace the Void:** Use generous padding (32px+) between containers to let the obsidian background act as a separator.
*   **Animate the Reveal:** Use "mask-reveal" transitions for data cards (sliding up with a subtle opacity fade).

### Don’t:
*   **Don’t use 100% White:** Never use `#FFFFFF`. Use `primary` (`#e9feff`) or `on_surface` (`#e5e2e1`) to avoid "retina burn" in dark environments.
*   **Don’t use Sharp Corners:** Always adhere to the Roundedness Scale (default `0.25rem` for small UI, `0.75rem` for cards). Sharp corners feel "cheap" and "digital"; subtle rounds feel "machined."
*   **Don’t use Solid Dividers:** Vertical spacing is your divider. If the content feels cluttered, increase the spacing scale rather than adding a line.