# SupportAgent UI Refresh

## Goal

Make SupportAgent feel calm, precise, and trustworthy while keeping its identity as an insurance operations product. The refresh takes inspiration from Vesta's restraint and information hierarchy without copying its brand or screen composition.

## Product character

- Calm under operational pressure
- Evidence-first and auditable
- Dense when work requires it, quiet everywhere else
- Professional without looking like a generic admin template

## Design principles

1. One obvious focus per screen.
2. Progressive disclosure for assistant, settings, environment, and technical metadata.
3. One neutral palette, one brand accent, and semantic colors reserved for status.
4. Borders establish structure; shadows are used only for floating layers.
5. Typography and spacing create hierarchy before cards and decoration do.
6. Repeated business objects use shared primitives instead of page-specific styling.

## Target shell

- Compact navigation rail for primary destinations
- Optional expanded navigation for labels and recent work
- Main workspace with a restrained maximum content width where appropriate
- Assistant closed by default and opened as a contextual drawer
- Settings, language, theme, environment, and account controls grouped in one menu
- Mobile navigation and assistant behave as overlays, not compressed columns

## Foundation tokens

- Neutral app background and white primary surface
- Ink, secondary, and tertiary text levels
- Muted indigo brand accent distinct from Vesta's green
- Consistent 8 px spacing rhythm
- Three radii only: control, surface, floating layer
- Monospace reserved for IDs, traces, timestamps, and usage data

## Delivery order

1. Global tokens and application shell
2. Claims index
3. Claim detail and controlled actions
4. Approvals, runs, audit, and integrations
5. Authentication and empty/loading/error states
6. Responsive and dark-theme pass

## Acceptance criteria

- The current route and primary action are identifiable within three seconds.
- No page shows more than one dominant accent-colored action.
- Technical metadata does not compete with the business decision.
- Shared panels, tables, badges, buttons, and empty states look identical across routes.
- Layout remains usable at 1280 px and does not depend on the assistant being open.
- Production build and type checking pass after every milestone.

## Out of scope

- Backend behavior and workflow changes
- Copying Vesta assets, source code, or branding
- Rewriting every page before the shell direction is validated
