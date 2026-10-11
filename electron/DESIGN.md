---
name: SunXBrowser desktop
description: Familiar Chrome-shaped desktop browsing with Thai interface copy.
colors:
  strip: "#dce6f9"
  surface: "#fff"
  ink: "#202124"
  muted: "#515762"
  hover: "#e8edf7"
  address: "#edf2fa"
  accent: "#1a5ecb"
  rule: "#e0e3e7"
  wordmark: "#2868c7"
  focus: "#2867cf"
  private-strip: "#25282d"
  private-surface: "#303339"
  private-ink: "#edf0f7"
  private-muted: "#c0c6d0"
  private-hover: "#444954"
  private-address: "#40454e"
  private-accent: "#a8c7fa"
  private-rule: "#52565f"
typography:
  display:
    fontFamily: '"Segoe UI", Arial, "Noto Sans Thai", sans-serif'
    fontSize: "57px"
    fontWeight: 600
    letterSpacing: "-1.6px"
  title:
    fontFamily: '"Segoe UI", Arial, "Noto Sans Thai", sans-serif'
    fontSize: "27px"
    fontWeight: 500
    letterSpacing: "-.5px"
  body:
    fontFamily: '"Segoe UI", Arial, "Noto Sans Thai", sans-serif'
    fontSize: "14px"
  label:
    fontFamily: '"Segoe UI", Arial, "Noto Sans Thai", sans-serif'
    fontSize: "12px"
rounded:
  small: "5px"
  shortcut: "8px"
  tab: "11px 11px 0 0"
  omnibox: "20px"
  search: "25px"
  circle: "50%"
spacing:
  toolbar-gap: "4px"
  search-gap: "12px"
  search-inset: "18px"
  content-inset: "36px"
components:
  icon-button:
    rounded: "{rounded.circle}"
    size: "34px"
    padding: "7px"
  omnibox:
    backgroundColor: "{colors.address}"
    rounded: "{rounded.omnibox}"
    height: "36px"
  home-search:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.search}"
    height: "48px"
    width: "min(570px, 90%)"
  tab:
    rounded: "{rounded.tab}"
    width: "222px"
  primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.surface}"
    rounded: "{rounded.small}"
    padding: "10px 20px"
---
# Design System: SunXBrowser desktop

## Overview

**Creative North Star: "User-pinned Chrome form"**

User-pinned Chrome form provides a familiar desktop browsing shell. Pale blue tabs, white surfaces, compact outline controls and pill-shaped search fields keep attention on the address and web content. SunXBrowser uses its existing blue S identity and system typography with Thai fallback.

**Key Characteristics:**
- Compact, fixed browser chrome.
- Blue interaction accents and pale neutral surfaces.
- Restrained shadows on search and floating find controls.

## Colors

### Primary
Accent blue marks primary actions, saved bookmarks and caret feedback; wordmark blue identifies the home page. Focus blue is the observed tab and home-search outline.

### Neutral
Strip, surface, address and hover distinguish browser layers without heavy borders. Ink is primary text; muted supports labels, icons and status copy; rule divides chrome and rows. The private tokens replace the corresponding light tokens in private windows, with dark surfaces and light text.

## Typography

All roles use the shared system stack in the frontmatter. The display role is the home wordmark; the title role serves internal pages. Body is interface and row text; label serves tabs, bookmarks, shortcuts and status. Home search uses a slightly larger size (15px). Internal-page subsection headings use (17px, weight 500). At the compact desktop breakpoint the wordmark becomes (49px).

## Layout

The fixed chrome occupies (118px): tab strip (40px), toolbar (48px), bookmarks (29px), plus divider. Web views and internal-page content begin below it. Tabs shrink from (222px) toward a minimum (96px), truncate labels and scroll horizontally. The omnibox flexes with a minimum width (100px).

Home content is centered with top padding (90px), a search width capped at (570px), wrapping shortcuts, and a quiet DNS footnote. At widths at or below (950px), the mode label hides, tabs cap at (180px), home top padding becomes (65px), and display type reduces. Internal pages cap at (850px) with padding (42px 36px).

Scope is the Electron desktop shell: screenshot evidence at (1280px) and (800px) widths in `test-output/home-1280.png` and `test-output/home-800.png`. The native window starts at (1280 × 820px) and permits a minimum (760 × 540px); mobile behavior is outside this contract.

On macOS, reserve (78px) before tabs for native traffic lights at (14px, 13px); hide custom window controls. Other platforms use frameless windows with custom minimize, maximize and close controls. The strip is draggable while tabs and controls remain interactive non-drag regions.

## Elevation & Depth

Most surfaces are flat, separated by tone and a thin rule. Search has a soft shadow (`0 1px 6px #2021243d`); the floating find bar has a stronger shadow (`0 3px 12px #20212426`) and border. Keep these elevations tied to their existing roles.

## Shapes

Search and address are pills. Icon controls and shortcut marks are circles. Tabs have rounded upper corners and a square bottom edge that joins the active surface. Smaller internal actions and status values use restrained rounded corners.

## Components

Icon buttons reveal a pale hover fill; unavailable actions have opacity (.4). Tabs communicate selection by joining the white page surface. Primary actions use filled accent blue; text actions use accent ink on transparent backgrounds. Shortcuts pair a circular letter mark with a short label.

Keyboard focus uses an accent outline (2px, offset 2px) on buttons, inputs and links. The omnibox uses its enclosing accent border during focus. Home search uses focus blue (2px, offset 3px); tabs use focus blue (2px, inset offset -3px), including their keyboard-operable tab wrappers. Preserve accessible Thai names and selected-tab semantics.

Only tab background transitions (120ms ease-out) and loading rotation (1s linear infinite) are defined. Reduced-motion preference disables transitions and animations globally. Avoid adding decorative movement.

## Do's and Don'ts

### Do:
- Do preserve visible keyboard focus on tabs, buttons and search fields.
- Do preserve the fixed chrome height when positioning web content.
- Do use the private palette consistently throughout private windows.

### Don’t:
- Don’t introduce decorative cards or large marketing sections into the browser shell.
- Don’t hide native macOS window controls behind custom controls.
- Don’t add motion that ignores reduced-motion preferences.
