import { R, mv, sway, draw } from "./kit.mjs";

const swipe = `${R}40%{transform:translateX(2.6px)}`;
const feed = "0%{transform:translateY(-6px);opacity:0}20%{opacity:1}100%{transform:none}";
const lift = `${R}40%{transform:translateY(-2.2px) rotate(-5deg)}72%{transform:translateY(.3px)}`;
const grow = from => `0%,${from}%{transform:scaleY(0)}${from + 30}%{transform:scaleY(1.12)}${from + 45}%,100%{transform:none}`;

export default [
  { name: "shopping-cart", title: "Shopping Cart", usage: "Point To A Store, A Basket, Or A Checkout Step.", tags: "basket buy store checkout shop",
    motion: "The Cart Rolls Forward With A Slight Tip And Rolls Back.",
    parts: [["b", '<path d="M2.5 3.5H5l2.4 11H18l2-7.5H6"/>'], ["w", '<g><circle cx="9" cy="18.75" r="1.5"/><circle cx="17" cy="18.75" r="1.5"/></g>', 1]],
    anim: { b: [`${R}35%{transform:translateX(2.2px) rotate(-4deg)}70%{transform:translateX(-.5px)}`, 800, "ease-in-out", "13px 17px"], w: [`${R}35%{transform:translateX(2.2px)}70%{transform:translateX(-.5px)}`, 800] } },
  { name: "price-tag", title: "Price Tag", usage: "Mark A Price, An Offer, Or A Discount.", tags: "offer discount sale label cost",
    motion: "The Tag Swings From Its String Hole And Hangs Still.",
    parts: [["t", '<path d="M3 3h8.5l9.2 9.2a1.5 1.5 0 0 1 0 2.1l-6.4 6.4a1.5 1.5 0 0 1-2.1 0L3 11.5z"/>'], ["h", '<circle cx="7.5" cy="7.5" r="1.5"/>', 1]],
    anim: { t: [sway(-13, 9, -4), 850, "ease-in-out", "7.5px 7.5px"] } },
  { name: "credit-card", title: "Credit Card", usage: "Mark A Payment Step Or A Billing Detail.", tags: "payment pay billing checkout bank",
    motion: "The Card Swipes Sideways Through A Reader And Returns.",
    parts: [["f", '<rect x="2.5" y="5" width="19" height="14" rx="2"/>'], ["s", '<path d="M2.5 9.5h19"/>', 1], ["c", '<path d="M6 15h4"/>']],
    anim: { f: [swipe, 650], s: [swipe, 650], c: [swipe, 650] } },
  { name: "gift-box", title: "Gift Box", usage: "Mark A Bonus, A Giveaway, Or A Free Resource.", tags: "bonus present giveaway reward free",
    motion: "The Lid And Bow Lift Off The Box And Drop Back On.",
    parts: [["b", '<path d="M4.5 12v7.5A1.5 1.5 0 0 0 6 21h12a1.5 1.5 0 0 0 1.5-1.5V12M12 12v9"/>'], ["l", '<path d="M4 8h16a1 1 0 0 1 1 1v2a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V9a1 1 0 0 1 1-1zM12 8v4"/>'], ["r", '<path d="M12 8S10.5 3.5 8 3.5A2.25 2.25 0 0 0 8 8zM12 8s1.5-4.5 4-4.5A2.25 2.25 0 0 1 16 8z"/>', 1]],
    anim: { l: [lift, 800, "ease-in-out", "12px 10px"], r: [lift, 800, "ease-in-out", "12px 10px"] } },
  { name: "receipt-slip", title: "Receipt Slip", usage: "Represent An Order Record Or A Proof Of Purchase.", tags: "invoice bill order proof purchase",
    motion: "The Receipt Feeds Downward In Steps Like Paper Leaving A Printer.",
    parts: [["p", '<path d="M5.5 2.5h13v19L16.3 20l-2.15 1.5L12 20l-2.15 1.5L7.7 20l-2.2 1.5z"/>'], ["l", '<path d="M8.5 7.5h7M8.5 11h7M8.5 14.5h4"/>', 1]],
    anim: { p: [feed, 800, "steps(6,end)"], l: [feed, 800, "steps(6,end)"] } },
  { name: "storefront", title: "Storefront", usage: "Represent A Shop, A Brand Page, Or A Seller.", tags: "shop store seller business market",
    motion: "The Awning Ripples And The Door Swings Open And Shut.",
    parts: [["a", '<path d="m3.5 9 1.5-5h14l1.5 5"/>'], ["s", '<path d="M3.5 9a2.83 2.83 0 0 0 5.67 0 2.83 2.83 0 0 0 5.66 0 2.83 2.83 0 0 0 5.67 0"/>', 1], ["w", '<path d="M5 13v7.5h14V13"/>'], ["d", '<path d="M10 20.5V16h4v4.5"/>']],
    anim: { s: [`${R}30%{transform:scaleY(1.5)}60%{transform:scaleY(.8)}`, 800, "ease-in-out", "12px 9px"], d: [`${R}50%{transform:scaleX(.35)}`, 800, "ease-in-out", "10px 18px"] } },
  { name: "wallet-fold", title: "Wallet Fold", usage: "Represent A Balance, Earnings, Or A Payout.", tags: "money balance earnings payout cash",
    motion: "The Clasp Pulls Open To The Side And Snaps Shut.",
    parts: [["b", '<path d="M17 4H5.5a2 2 0 0 0 0 4h13A1.5 1.5 0 0 1 20 9.5V19a1.5 1.5 0 0 1-1.5 1.5h-13a2 2 0 0 1-2-2V6"/>'], ["c", '<path d="M20 12h-3.5a2 2 0 0 0 0 4H20"/>', 1]],
    anim: { c: [`${R}40%{transform:translateX(2px)}75%{transform:translateX(-.5px)}`, 700] } },
  { name: "sales-chart", title: "Sales Chart", usage: "Show Revenue Or Growth Across A Period.", tags: "revenue growth analytics bars trend",
    motion: "The Bars Grow From The Baseline In Turn And The Trend Line Climbs Over Them.",
    parts: [["a", '<path d="M6 20v-4"/>'], ["b", '<path d="M11 20v-6.5"/>'], ["c", '<path d="M16 20v-9"/>'], ["t", '<path pathLength="1" d="m3.5 10 5-3 3.5 1.5 7.5-5.25M16 3h3.75v3.75"/>', 1]],
    anim: { a: [grow(0), 800, "ease-out", "6px 20px"], b: [grow(15), 800, "ease-out", "11px 20px"], c: [grow(30), 800, "ease-out", "16px 20px"], t: [draw(35), 1000, "ease-out"] } }
];
