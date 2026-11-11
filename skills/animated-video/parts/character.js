// Doodle Character: A Simple Hand-Drawn Figure With Poses, A Walk Cycle, Blinking, And A Mouth That Follows The Voice.
//
// Use It As A Scene Of Its Own, Or Inside Another Draw Function With s.use(c, "Doodle Character", params, box).
// Copy This File Into A Film's Scenes Folder And Register It Under A New Name To Restyle It.
// The Figure Is One Definition: The Proportions Below Are Constants, So It Stays On Model In Every Shot.
//
// Options (All Optional). Any Time Accepts Seconds Or The Name Of A Beat.
//   x         Where The Figure Stands, As A Share Of The Frame Width. Default 0.5.
//   ground    The Height Of The Ground Line, As A Share Of The Frame Height. Default 0.8.
//   size      The Figure's Height As A Share Of The Frame Height. Default 0.5. It Is Reduced When The Frame Is Too Narrow.
//   pose      The Pose Held At The Start: Stand, Wave, Point, Think, Cheer, Shrug, Or Talk. Default "Stand".
//   poses     Pose Changes: [{ "at": 1.2, "pose": "Wave", "duration": 0.4 }]. Each Blends From The Pose Before It.
//   walk      Walks: [{ "at": 0.5, "from": 0.2, "to": 0.75, "duration": 3 }]. from And to Are Shares Of The Frame Width.
//             Feet Stay Planted While They Are On The Ground. Leave Out duration For An Ordinary Pace.
//   talk      true Moves The Mouth With The Voice Level And Closes It Between Words. Default false.
//   mood      The Resting Mouth From -1 (Frown) To 1 (Smile). Default 0.4.
//   look      Where The Eyes Look: [x, y] From -1 To 1. Default [0, 0].
//   brows     Draw Eyebrows. Default true.
//   drawings  Held Drawings Per Second. Motion Steps And The Line Boils At This Rate. 0 Moves Smoothly. Default 12.
//   boil      How Much The Line Shimmers Between Drawings. 0 Is A Steady Line. Default 1.
//   line      A Multiplier For The Line Width. Default 1.
//   shadow    Draw A Soft Shape On The Ground Under The Feet. Default true.
//   colors    Overrides: { ink, body, skin }. By Default Ink Is The Scene Foreground, Body The Accent, And Skin The Background.
//
// Events Declared: walkN-stepM At Each Footfall (Kind "step") And poseN-Name At Each Pose Change (Kind "pose").
//
// Example Scene:
//   { "mode": "Code Scene", "draw": "Doodle Character", "duration": 5,
//     "params": { "talk": true, "poses": [{ "at": 1, "pose": "Wave" }, { "at": 3, "pose": "Stand" }] } }
(function () {
  "use strict";
  const K = MotionKit;
  // Proportions, In Shares Of The Figure's Height. No Shot Overrides These.
  const HEAD = 0.17, NECK = 0.02, TORSO = 0.32, HIP = 0.2795, THIGH = 0.14, SHIN = 0.14, UPPER = 0.125, FORE = 0.125;
  const SHOULDER = 0.082, HIP_HALF = 0.045, STANCE = 0.05, FOOT = 0.06, HAND = 0.022, STEP = 0.14, LIFT = 0.035, DROP = 0.016, LINE = 0.013;
  // A Pose Is Two Arm Angles Per Side In Degrees (0 Hangs Down, 90 Points Outward, 180 Points Up), Plus Body And Face Values.
  // ls And le Are The Screen-Left Shoulder And Elbow. rs And re Are The Screen-Right Ones.
  const POSES = {
    Stand: { ls: 9, le: 7, rs: 9, re: 7, lean: 0, tilt: 0, shrug: 0, brow: 0, lookX: 0, lookY: 0, wave: 0, gesture: 0, hop: 0 },
    Wave: { ls: 10, le: 8, rs: 128, re: 38, lean: -2, tilt: 7, shrug: 0, brow: 0.6, lookX: 0, lookY: 0, wave: 1, gesture: 0, hop: 0 },
    Point: { ls: 12, le: 10, rs: 86, re: 3, lean: 5, tilt: 3, shrug: 0, brow: 0.2, lookX: 0.8, lookY: 0, wave: 0, gesture: 0, hop: 0 },
    Think: { ls: 16, le: -78, rs: 75, re: 146, lean: -3, tilt: -9, shrug: 0, brow: -0.4, lookX: -0.6, lookY: -0.7, wave: 0, gesture: 0, hop: 0 },
    Cheer: { ls: 128, le: 6, rs: 122, re: 12, lean: 0, tilt: -4, shrug: 0, brow: 1, lookX: 0, lookY: -0.3, wave: 0, gesture: 0, hop: 1 },
    Shrug: { ls: 34, le: 96, rs: 38, re: 92, lean: 0, tilt: 8, shrug: 1, brow: 0.8, lookX: 0, lookY: 0, wave: 0, gesture: 0, hop: 0 },
    Talk: { ls: 11, le: 12, rs: 34, re: 84, lean: 2, tilt: 3, shrug: 0, brow: 0.3, lookX: 0, lookY: 0, wave: 0, gesture: 1, hop: 0 }
  };
  const defaults = { x: 0.5, ground: 0.8, size: 0.5, pose: "Stand", poses: [], walk: [], talk: false, mood: 0.4, look: [0, 0], brows: true, drawings: 12, boil: 1, line: 1, shadow: true, colors: {} };
  const poseNamed = name => {
    if (!POSES[name]) throw new Error("Unknown Pose: " + name + ". Choose From " + Object.keys(POSES).join(", ") + ".");
    return POSES[name];
  };
  const height = s => Math.min(s.height * s.params.size, s.width * s.params.size * 1.7);

  // The Pose Changes And Walks As Plain Times, Shared By The Picture And The Events.
  function plan(s) {
    const p = s.params, H = height(s);
    const changes = (p.poses || []).map(item => ({ at: s.when(item.at, 0), pose: item.pose, duration: Math.max(0.01, item.duration ?? 0.4) })).sort((a, b) => a.at - b.at);
    let x = p.x * s.width;
    const walks = (p.walk || []).map(item => ({ at: s.when(item.at, 0), from: item.from, to: item.to, duration: item.duration })).sort((a, b) => a.at - b.at).map(item => {
      const from = item.from != null ? item.from * s.width : x, to = item.to * s.width, dir = to >= from ? 1 : -1, distance = Math.abs(to - from);
      const steps = Math.max(2, Math.round(distance / (STEP * H)) + 1), stride = distance / (steps - 1);
      const walk = { at: item.at, from, to, dir, steps, stride, duration: Math.max(0.05, item.duration ?? steps * 0.42) };
      // Step j Carries One Foot To land(j). The Last Step Brings The Trailing Foot Level With The Other.
      walk.land = j => from + dir * stride * Math.min(j + 1, steps - 1);
      x = to;
      return walk;
    });
    return { p, H, changes, walks, startX: walks.length ? walks[0].from : p.x * s.width };
  }
  // Where The Two Feet And The Body Are At A Time. Foot 0 Is Screen Left And Foot 1 Is Screen Right.
  function stride(g, T) {
    let base = [g.startX, g.startX], lift = [0, 0], dir = 1, weight = 0;
    for (const walk of g.walks) {
      if (T < walk.at) break;
      dir = walk.dir;
      const first = walk.dir > 0 ? 1 : 0, footOf = j => j % 2 === 0 ? first : 1 - first, each = walk.duration / walk.steps;
      if (T >= walk.at + walk.duration) { base = [walk.to, walk.to]; lift = [0, 0]; weight = 0; continue; }
      const k = Math.min(walk.steps - 1, Math.floor((T - walk.at) / each)), v = K.clamp((T - walk.at - k * each) / each);
      base = [walk.from, walk.from];
      for (let j = 0; j < k; j++) base[footOf(j)] = walk.land(j);
      const moving = footOf(k), glide = K.lerp(v, K.smooth(v), 0.6);
      base[moving] = K.lerp(base[moving], walk.land(k), glide);
      lift = [0, 0]; lift[moving] = Math.sin(Math.PI * v) * LIFT * g.H;
      weight = K.between(T, walk.at, walk.at + each * 0.5) * (1 - K.between(T, walk.at + walk.duration - each * 0.5, walk.at + walk.duration));
    }
    return { base, lift, dir, weight, x: (base[0] + base[1]) / 2 };
  }
  // The Blended Pose At A Time.
  function poseAt(g, T) {
    let pose = Object.assign({}, poseNamed(g.p.pose)), hop = 0;
    for (const change of g.changes) {
      if (T < change.at) break;
      const raw = K.between(T, change.at, change.at + change.duration), u = K.ease.outBack(raw), target = poseNamed(change.pose), next = {};
      for (const key of Object.keys(pose)) next[key] = K.lerp(pose[key], target[key], key === "wave" || key === "gesture" || key === "hop" ? raw : u);
      hop += target.hop * Math.sin(Math.PI * raw);
      pose = next;
    }
    pose.hopNow = hop;
    return pose;
  }
  // Blinks Come At Uneven Seeded Intervals Of A Few Seconds. Returns How Open The Eyes Are, From 0 To 1.
  function eyesOpen(s, T) {
    const random = s.rng("blink");
    let at = 0.9 + random() * 1.6;
    for (let i = 0; i < 400 && at <= T; i++) {
      if (T < at + 0.16) return 1 - K.pulse(T, at, 0.16);
      at += 1.7 + random() * 3.1;
    }
    return 1;
  }

  function draw(c, s) {
    const g = plan(s), p = g.p, H = g.H, rate = p.drawings > 0 ? p.drawings : 0;
    const T = rate ? K.stepTime(s.time, rate, 1) : s.time, drawing = rate ? Math.round(T * rate) : 0;
    const feet = stride(g, T), pose = poseAt(g, T), o = p.colors || {};
    const ink = o.ink || s.colors.foreground, body = o.body || s.colors.accent, skin = o.skin || s.colors.background;
    const width = Math.max(2.2, H * LINE * p.line), wobble = p.boil * Math.max(0.6, H * 0.0032);
    const ground = p.ground * s.height, hopUp = pose.hopNow * H * 0.035;
    const rough = (points, name, closed) => {
      const path = wobble > 0 ? K.boilPath(points, { amount: wobble, seed: name, step: drawing, scale: 6 / H }) : points;
      K.tracePath(c, path, closed);
    };
    const stroke = (points, name) => { rough(points, name, false); c.stroke(); };
    const shape = (points, name, fill) => { rough(points, name, true); c.fillStyle = fill; c.fill(); c.stroke(); };
    c.save();
    c.lineCap = "round"; c.lineJoin = "round"; c.lineWidth = width; c.strokeStyle = ink;

    // Ground Shadow.
    if (p.shadow) {
      c.save(); c.globalAlpha *= 0.14; c.fillStyle = ink;
      c.beginPath(); c.ellipse(feet.x, ground + H * 0.012, H * (0.15 + Math.abs(feet.base[1] - feet.base[0]) / H * 0.5) * (1 - hopUp / H * 3), H * 0.022, 0, 0, K.TAU); c.fill();
      c.restore();
    }

    // Legs. The Hips Sink As The Feet Spread So The Fixed Bones Always Reach The Planted Feet.
    const spread = Math.abs(feet.base[1] - feet.base[0]) / (STEP * H);
    const hipY = ground - (HIP - DROP * spread * spread) * H - hopUp, hipX = feet.x;
    const lean = K.rad(pose.lean + feet.dir * 5 * feet.weight), turn = (x, y) => [x * Math.cos(lean) - y * Math.sin(lean), x * Math.sin(lean) + y * Math.cos(lean)];
    for (const side of [0, 1]) {
      const sign = side ? 1 : -1, hx = hipX + sign * HIP_HALF * H, fx = feet.base[side] + sign * STANCE * H, fy = ground - feet.lift[side] - hopUp;
      const knee = K.joint(hx, hipY, fx, fy, THIGH * H, SHIN * H, -feet.dir);
      const toe = K.lerp(sign, feet.dir, feet.weight) * FOOT * H, heel = feet.lift[side] > 0 ? -feet.lift[side] * 0.35 : 0;
      stroke(K.resample([[hx, hipY], [knee.x, knee.y], [knee.endX, knee.endY]], H * 0.04), "leg" + side);
      stroke([[knee.endX, knee.endY], [knee.endX + toe * 0.5, knee.endY + heel * 0.5], [knee.endX + toe, knee.endY + heel]], "foot" + side);
    }

    // Body: A Bean From The Hips To The Shoulders.
    const at = (x, y) => { const r = turn(x * H, y * H); return [hipX + r[0], hipY + r[1]]; };
    const lift = pose.shrug * 0.022;
    const bean = K.splinePoints([at(-0.062, 0.012), at(0.062, 0.012), at(0.078, -0.1), at(0.07, -0.22), at(SHOULDER, -TORSO + 0.03 - lift), at(0.05, -TORSO - lift * 0.5),
      at(-0.05, -TORSO - lift * 0.5), at(-SHOULDER, -TORSO + 0.03 - lift), at(-0.07, -0.22), at(-0.078, -0.1)], { closed: true, segments: 6 });
    shape(bean, "body", body);

    // Head And Face.
    const headAt = at(0, -TORSO - NECK - HEAD), tilt = lean + K.rad(pose.tilt);
    const face = (x, y) => [headAt[0] + (x * Math.cos(tilt) - y * Math.sin(tilt)) * H, headAt[1] + (x * Math.sin(tilt) + y * Math.cos(tilt)) * H];
    shape(K.circlePoints(headAt[0], headAt[1], HEAD * H, 28), "head", skin);
    const lookX = K.clamp((p.look ? p.look[0] : 0) + pose.lookX + feet.dir * 0.6 * feet.weight, -1, 1), lookY = K.clamp((p.look ? p.look[1] : 0) + pose.lookY, -1, 1);
    const open = eyesOpen(s, T), eyeY = -0.012 + lookY * 0.014, shift = lookX * 0.022;
    c.fillStyle = ink;
    for (const sign of [-1, 1]) {
      const eye = face(sign * 0.058 + shift, eyeY);
      if (open > 0.3) { c.beginPath(); c.ellipse(eye[0], eye[1], H * 0.021, H * 0.021 * open, tilt, 0, K.TAU); c.fill(); }
      else stroke([face(sign * 0.058 + shift - 0.022, eyeY), face(sign * 0.058 + shift + 0.022, eyeY)], "lid" + sign);
      if (p.brows) {
        const raise = -0.062 - pose.brow * 0.02 + lookY * 0.008, slant = pose.brow * 0.012;
        c.save(); c.lineWidth = width * 0.8;
        stroke([face(sign * 0.034 + shift, raise - slant), face(sign * 0.084 + shift, raise + slant)], "brow" + sign);
        c.restore();
      }
    }
    // Mouth. Shown A Little Early So It Does Not Look Dubbed. Closed Below A Small Level And Between Words.
    const ahead = T + 0.04, level = p.talk ? s.voiceAt(ahead) : 0, speaking = level > 0.09;
    const mouthY = 0.074 + lookY * 0.006;
    if (speaking) {
      const word = s.words.find(item => ahead >= item.start - 0.02 && ahead < item.end + 0.02), rounded = word && /[ouw]/i.test(word.text) ? 1 : 0;
      const gape = K.clamp((level - 0.09) * 1.25), centre = face(shift * 0.6, mouthY + gape * 0.012);
      c.beginPath(); c.ellipse(centre[0], centre[1], H * (rounded ? 0.026 : 0.04), H * (0.012 + gape * (rounded ? 0.03 : 0.034)), tilt, 0, K.TAU); c.fill();
    } else {
      const curve = p.mood * 0.022;
      stroke(K.quadPoints(face(shift * 0.6 - 0.04, mouthY - curve * 0.4), face(shift * 0.6, mouthY + curve), face(shift * 0.6 + 0.04, mouthY - curve * 0.4), 8), "mouth");
    }

    // Arms. Fixed Bone Lengths, Turned By The Pose Angles. During A Walk Each Arm Swings Opposite Its Leg.
    const lead = (feet.base[1] - feet.base[0]) * feet.dir / (STEP * H), swing = -lead * 22 * feet.dir * feet.weight;
    const gesture = pose.gesture * (p.talk ? level : 0.4), wave = pose.wave * Math.sin(T * K.TAU * 1.7) * 24;
    for (const side of [0, 1]) {
      const sign = side ? 1 : -1, shoulder = at(sign * SHOULDER * 0.92, -TORSO + 0.035 - lift);
      const a1 = K.rad((side ? pose.rs : pose.ls) + swing + (side ? gesture * 12 : 0)), a2 = a1 + K.rad((side ? pose.re : pose.le) + (side ? wave + gesture * 34 : 0));
      const d1 = turn(sign * Math.sin(a1), Math.cos(a1)), d2 = turn(sign * Math.sin(a2), Math.cos(a2));
      const elbow = [shoulder[0] + d1[0] * UPPER * H, shoulder[1] + d1[1] * UPPER * H], hand = [elbow[0] + d2[0] * FORE * H, elbow[1] + d2[1] * FORE * H];
      stroke(K.resample([shoulder, elbow, hand], H * 0.04), "arm" + side);
      shape(K.circlePoints(hand[0], hand[1], HAND * H, 12), "hand" + side, skin);
    }
    c.restore();
  }

  function events(s) {
    const g = plan(s), pan = x => K.clamp(x / s.width * 2 - 1, -1, 1), out = [];
    g.walks.forEach((walk, w) => {
      for (let j = 0; j < walk.steps; j++) out.push({ id: "walk" + (w + 1) + "-step" + (j + 1), at: walk.at + (j + 1) * walk.duration / walk.steps, what: "Footfall " + (j + 1) + " Of Walk " + (w + 1), kind: "step", pan: pan(walk.land(j)), sound: "Paper Tap", gain: 0.22 });
    });
    g.changes.forEach((change, i) => out.push({ id: "pose" + (i + 1) + "-" + change.pose, at: change.at, what: "Pose Changes To " + change.pose, kind: "pose", pan: pan(stride(g, change.at).x) }));
    return out.sort((a, b) => a.at - b.at);
  }
  MotionScenes.register("Doodle Character", draw, { defaults, events, about: "A Doodle Figure With Poses, A Walk Cycle, Blinking, And A Mouth That Follows The Voice." });
})();
