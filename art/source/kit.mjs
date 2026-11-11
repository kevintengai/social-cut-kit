// Small keyframe helpers shared by the icon source files. Lengths are grid units.
export const R = "0%,100%{transform:none}";
export const mv = (x, y, at = 50) => `${R}${at}%{transform:translate(${x}px,${y}px)}`;
export const rot = (deg, at = 50) => `${R}${at}%{transform:rotate(${deg}deg)}`;
export const scl = (s, at = 50) => `${R}${at}%{transform:scale(${s})}`;
export const sway = (a, b, c = 0) => `${R}25%{transform:rotate(${a}deg)}55%{transform:rotate(${b}deg)}80%{transform:rotate(${c}deg)}`;
export const draw = (from = 0) => `0%,${from}%{stroke-dasharray:1 1;stroke-dashoffset:1;opacity:0}${from + 1}%{opacity:1}100%{stroke-dasharray:1 1;stroke-dashoffset:0}`;
export const drop = (x, y, at = 60) => `0%{transform:translate(${x}px,${y}px);opacity:0}${at}%{transform:translate(${-x * 0.12}px,${-y * 0.12}px);opacity:1}100%{transform:none}`;
export const pop = (from = 0) => `0%,${from}%{transform:scale(.3);opacity:0}${from + (100 - from) * 0.65}%{transform:scale(1.15);opacity:1}100%{transform:none}`;
export const blink = (low = 0.15, at = 50) => `0%,100%{opacity:1}${at}%{opacity:${low}}`;
export const appear = (from = 0) => `0%,${from}%{opacity:0}100%{opacity:1}`;
