# Interface design

The product is a restaurant assistant, so the interface is set like a printed menu rather
than a generic chat or dashboard: serif dish names, dotted leaders to the price, hairline
rules between dishes, and very few boxes.

## Tokens

Defined once in [`frontend/src/index.css`](../frontend/src/index.css).

| Token | Use |
| --- | --- |
| `pine` | header, primary action, the diner's own messages |
| `saffron` | brand name and the current section only |
| `paper`, `card` | page and sheet surfaces |
| `ink`, `muted` | text and secondary text |
| `ember` | spice level and focus outline |
| `alert` | allergens that rule a dish out, safety notices, errors |
| `herb` | reasons a dish suits the diner |
| `notice` | something waiting for the diner's answer |
| Fraunces, Figtree | dish names and headings; everything else |
| 6 px, 10 px | radius of controls and of panels; nothing is pill-shaped |

## Rules

- One primary button in a view. Others are outlined or plain text actions.
- Allergen text is larger and darker than other dish details.
- Colour never carries meaning alone: warnings have an icon and words.
- Controls are at least 44 px tall on touch screens.
- Each section has its own address, so back and bookmarks work.
- Motion is limited to the loading indicator and respects reduced-motion settings.

## How it was reviewed

- UI UX Pro Max supplied the design checklist. Its suggested direction (red, bold block layout, enterprise landing page) was
  rejected as wrong for this product; the existing identity was kept and tightened.
- Impeccable's critique and polish guidance was applied by hand. Its automated detector was
  not run.
- [Vercel's Web Interface Guidelines](https://github.com/vercel-labs/web-interface-guidelines)
  were used as a separate checklist. Two were not followed on purpose: headings and buttons
  stay in sentence case, and the assistant speaks in the first person.

## Not done

No dark theme, no dish photography (the dishes are fictional), and no automated visual or
accessibility tests.
