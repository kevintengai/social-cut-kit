# Social Cut Kit Icons

A Dependency-Free Library Of 96 Animated Line Icons In Twelve Groups, Plus Six Looping Overlays For Video Layers. Each Icon Is An Ordinary Symbol At Rest. When The Button Or Link That Contains It Is Hovered Or Focused From The Keyboard, The Icon Plays One Short Motion That Acts Out Its Meaning And Settles Back To Its Resting Drawing.

Open [The Gallery](index.html) From The Unzipped Folder To Browse Every Icon By Group Or By Search. It Needs No Server And No Install.

## What Is In The Folder

| File | Purpose |
| --- | --- |
| `icons.js` | The ES Module. It Runs In Browsers, Bundlers, And Node. |
| `icons.css` | The Motion For Every Icon. Link It Once Per Page. |
| `icons.d.ts` | TypeScript Types, Including A Union Of Every Icon Name. |
| `icons.global.js` | The Same API As A Classic Script For Pages Opened Straight From Disk. |
| `icons/NAME.svg` | One Standalone SVG Per Icon For Editors And Design Tools. |
| `motion/NAME.svg` | Six Hand-Authored Looping Overlays For Browser Layers Over Video. |
| `catalog.json` | Titles, Groups, Usage Notes, Motion Sentences, Search Tags, And File Paths. |
| `source/` | The Single Source Description Of Every Icon. |
| `build.mjs` | Regenerates Every Generated File From The Source. |
| `icons.test.mjs` | Offline Checks For The API, The Motion, And The Catalog. |

## Use It On A Web Page

Link The Stylesheet, Mark Where Icons Belong, And Fill Them.

```html
<link rel="stylesheet" href="art/icons.css">

<button type="button">
  <span data-icon="download-tray"></span>
  Download
</button>

<script type="module">
  import { hydrate } from "./art/icons.js";
  hydrate();
</script>
```

Browsers Refuse To Load ES Modules From A Page Opened Directly From Disk. For That Case Use The Classic Script, Which Exposes The Same API On `window.SocialCutIcons`.

```html
<script src="art/icons.global.js"></script>
<script>SocialCutIcons.hydrate();</script>
```

## Use It With A Bundler

Import The Module And The Stylesheet From Wherever You Copied The Folder. The Module Has No Imports Of Its Own.

```js
import { icon } from "./art/icons.js";
import "./art/icons.css";

saveButton.innerHTML = icon("save-bookmark", { size: 20 }) + " Save";
```

## Use It In A Component Framework

`icon()` Returns A String Of SVG Markup, So Any Framework That Can Insert Trusted Markup Can Render It. The Markup Comes Only From This Library. Pass Names And Labels From Your Own Code.

```jsx
import { icon } from "./art/icons.js";
import "./art/icons.css";

export function Icon({ name, size = 24, label }) {
  return <span dangerouslySetInnerHTML={{ __html: icon(name, { size, label }) }} />;
}

export function DeleteButton() {
  return <button type="button"><Icon name="trash-bin" /> Delete</button>;
}
```

In Vue Use `v-html="icon(name)"`. In Svelte Use `{@html icon(name)}`. On A Server, Call `icon()` While Rendering And Send The Markup With The Page.

## API

| Export | What It Does |
| --- | --- |
| `icon(name, options)` | Returns SVG Markup For One Icon. Throws A `RangeError` For An Unknown Name. |
| `hydrate(root)` | Fills Every Element Under `root` That Carries A `data-icon` Attribute And Returns How Many It Filled. `root` Defaults To The Document. |
| `icons` | A Frozen Map From Icon Name To Inner SVG Markup. |
| `motions` | A Frozen Map From Icon Name To One Sentence Describing What Its Motion Shows. |
| `groups` | The Groups In Display Order. Each Entry Has A `name` And A List Of `icons`. |

| Option | Default | Meaning |
| --- | --- | --- |
| `size` | `24` | Width And Height. A Number Is Read As Pixels. A String Such As `"1.5em"` Is Used As Written. |
| `strokeWidth` | `1.5` | Stroke Width In Grid Units. |
| `label` | None | An Accessible Name. Without It The Icon Is Decorative. |
| `class` | None | Extra Class Names As A String Or A List. |

`hydrate()` Reads The Same Options From `data-icon-size`, `data-icon-stroke`, `data-icon-label`, And `data-icon-class`. An Invalid Size, Stroke Width, Or Class Name Throws A `TypeError`.

## Color

Icons Are Drawn With `currentColor`, Which Means Each One Inherits Its Container's Text Color. Some Parts Are Marked As Accents. They Match The Rest Of The Icon Unless You Set `--sck-accent` On The Icon Or Any Ancestor.

```css
.toolbar { color: #e7f4ff; --sck-accent: #5ee1c7; }
```

The Standalone Files In `icons/` Carry The Kit’s Light Ink And Mint Accent So They Read On Dark Footage. To Recolor A Copy, Change The `color` Attribute On Its Root And The Accent `stroke` Values.

## Motion

- Motion Plays Once When An Ancestor `a`, `button`, `summary`, `label`, Or An Element With The Role `button`, `link`, `tab`, Or `menuitem` Is Hovered Or Receives Keyboard Focus. Add The Class `sck-trigger` To Make Any Other Element A Trigger.
- To Play A Motion From Script, Add The Class `sck-play` To The Icon’s `svg` Element. Remove The Class And Add It Again To Replay.
- Nothing Moves At Rest, And Every Motion Ends On The Resting Drawing.
- All Motion Sits Inside A `prefers-reduced-motion: no-preference` Query. People Who Ask Their Device For Reduced Motion See Static Icons.
- The Standalone Files In `icons/` Are Static. The Six Files In `motion/` Loop On Their Own And Also Honor Reduced Motion.

## Accessibility

- By Default An Icon Is Decorative. Its Markup Carries `aria-hidden="true"` And `focusable="false"`, So Assistive Technology Skips It And The Text Beside It Names The Control.
- For A Control With No Visible Text, Pass `label`. The Icon Then Carries `role="img"` And An `aria-label`. Label The Action, Such As Delete, Not The Picture.
- Motion Is Decoration Only. No Meaning Depends On Seeing It.
- Icons Inherit Color, So Check Contrast For The Text Color You Give Them. Use At Least 16 Pixels For Small Controls.

## Add An Icon

1. Open The Group File In `source/`, Or Add A New Group File And List It In `source/index.mjs`.
2. Add An Entry With A `name` In Lowercase Words Joined By Hyphens, A `title`, A `usage` Sentence, A `motion` Sentence, Search `tags`, `parts`, And `anim`.
3. Draw On The 24 Unit Grid And Keep Geometry Between 2 And 22. Each Part Is A Key And One SVG Element With Geometry Only. Do Not Add Fill, Stroke, Class, Or Style Attributes. Add `1` As A Third Item To Mark A Part As An Accent.
4. In `anim`, Give Each Moving Part Its Keyframes, A Duration In Milliseconds, And Optionally An Easing, A Transform Origin In Grid Units, And A Delay. End Every Motion On The Resting Drawing. The Build Rejects Two Icons With Identical Motion.
5. Run The Build And The Checks, Then Look At The New Icon In The Gallery At 16 And 24 Pixels.

```js
{ name: "save-bookmark", title: "Save Bookmark", usage: "Point To The Save Action For A Reference Clip.", tags: "favorite keep later ribbon",
  motion: "The Bookmark Drops Into Place And The Plus Mark Confirms The Save.",
  parts: [["r", '<path d="M6 3.5h12V21l-6-4.5L6 21z"/>'], ["p", '<path d="M9 8.5h6M12 5.5v6"/>', 1]],
  anim: { r: [land, 650, "ease-out"], p: [pop(55), 800, "ease-out", "12px 8.5px"] } }
```

## Build And Check

Run These From The Product Root With Node 20 Or Later. They Use Only The Node Standard Library And Work Offline.

```sh
node art/build.mjs
node art/build.mjs --check
node --test art/icons.test.mjs
```

The First Command Regenerates `icons.js`, `icons.global.js`, `icons.css`, `icons.d.ts`, `catalog.json`, And Every File In `icons/`. The Second Exits With A Non-Zero Status When Any Generated File Differs From The Source. The Third Runs The Checks.
