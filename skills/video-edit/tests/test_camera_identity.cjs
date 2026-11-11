const assert = require("node:assert/strict");
const {createHash, webcrypto} = require("node:crypto");
const {readFileSync} = require("node:fs");
const {join} = require("node:path");
const {test} = require("node:test");
const vm = require("node:vm");
const {Worker} = require("node:worker_threads");

const html = readFileSync(join(__dirname, "../scripts/camera_review.html"), "utf8");
const workerCode = html.match(/<script type="text\/plain" id="cameraHashWorker">([\s\S]*?)<\/script>/)[1];
const playerCode = html.match(/<script>([\s\S]*?)<\/script>/)[1];
const workerBridge = [
  'const {parentPort} = require("node:worker_threads");',
  'const self = {postMessage: x => parentPort.postMessage(x)};',
  workerCode,
  'parentPort.on("message", data => self.onmessage({data}));',
].join("\n");

function expected(...parts) {
  const hash = createHash("sha256");
  for (const part of parts) hash.update(part);
  return hash.digest("hex");
}
function namedBlob(parts) {
  const file = new Blob(parts);
  Object.defineProperty(file, "name", {value: "Target.mp4"});
  return file;
}
function hashMessage(worker, file) {
  return new Promise((resolve, reject) => {
    function receive(data) {
      if (data.percent !== undefined) return;
      worker.off("message", receive);
      if (data.error) reject(Error("Worker Read Failed."));
      else resolve(data.digest);
    }
    worker.on("message", receive);
    worker.postMessage(file);
  });
}

test("SHA-256 Vectors, Padding Boundaries, And Multi-Chunk Inputs", async () => {
  const worker = new Worker(workerBridge, {eval: true});
  try {
    assert.equal(await hashMessage(worker, new Blob()), "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855");
    assert.equal(await hashMessage(worker, new Blob(["abc"])), "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");
    const chunk = 4 * 1024 * 1024;
    for (const size of [1, 55, 56, 63, 64, 65, 119, 120, 127, 128, chunk-1, chunk, chunk+1]) {
      const part = Buffer.alloc(size);
      for (let i=0; i<size; i++) part[i] = (i*7+3) & 255;
      assert.equal(await hashMessage(worker, namedBlob([part])), expected(part), "Size " + size);
    }
    // Reuse One Immutable Blob To Exercise The Upper 32 Bits Of The Bit Length.
    const repeatedBytes = Buffer.alloc(chunk,0x93);
    const repeatedBlob = new Blob([repeatedBytes]);
    const highLength = new Blob([...Array(128).fill(repeatedBlob),"x"]);
    const highHash = expected(...Array(128).fill(repeatedBytes),Buffer.from("x"));
    assert.equal(await hashMessage(worker,highLength),highHash);
    await assert.rejects(hashMessage(worker,{size:5}),/Read Failed/);
  } finally {
    await worker.terminate();
  }
});

function player(crypto, mode = "normal") {
  const nodes = new Map();
  const urls = new Map();
  const workers = [];
  const context2d = {resetTransform() {}, clearRect() {}};
  function element() {
    return {style:{}, dataset:{}, disabled:true, textContent:"", events:{}, readyState:0,
      getContext: () => context2d, addEventListener(event, fn) {this.events[event] = fn;},
      removeAttribute(key) {delete this[key];}, pause() {}, load() {}};
  }
  const document = {
    createElement: element,
    getElementById(id) {
      if (id === "embeddedPlan") return null;
      if (!nodes.has(id)) nodes.set(id,element());
      return nodes.get(id);
    },
  };
  document.getElementById("cameraHashWorker").textContent = workerCode;
  let nextURL = 0;
  class BrowserWorker {
    constructor(url) {
      assert.equal(urls.get(url).type,"text/javascript");
      workers.push(this);
      if (mode === "throw") throw Error("Worker Unavailable.");
      if (mode === "normal") {
        this.native = new Worker(workerBridge,{eval:true});
        this.native.on("message",data=>this.onmessage({data}));
        this.native.on("error",()=>this.onerror());
      }
    }
    postMessage(file) {
      if (mode === "fail") return queueMicrotask(()=>this.onerror());
      if (this.native) this.native.postMessage(file);
    }
    terminate() {
      this.terminated = true;
      if (this.native) this.native.terminate();
    }
  }
  const url = {
    createObjectURL(blob) {const key = "blob:test-"+(++nextURL); urls.set(key,blob); return key;},
    revokeObjectURL(key) {urls.delete(key);},
  };
  const ctx = vm.createContext({Blob, Worker:BrowserWorker, URL:url, document, crypto, queueMicrotask});
  vm.runInContext(playerCode,ctx);
  function install(size, hash) {
    ctx.inputPlan = {
      schema:"camera-transfer/v1",source:{width:64,height:48,duration:1,name:"Target.mp4",bytes:size,sha256:hash},
      reference:{duration:1},settings:{fps:24,strength:1,anchor_x:.5,anchor_y:.5,timing:"hold",edge_mode:"cover"},
      samples:[{t:0,x:0,y:0,angle:0,zoom:1,confidence:1,status:"origin"}],
    };
    return vm.runInContext("installPlan(inputPlan)",ctx);
  }
  const invoke = text=>vm.runInContext(text,ctx);
  function select(file) {
    ctx.file = file;
    return invoke("selectFile(file)");
  }
  function metadata() {
    return invoke("video.videoWidth=64;video.videoHeight=48;video.duration=1;video.events.loadedmetadata();ready");
  }
  return {install,select,metadata,invoke,workers,urls,controls:nodes};
}

test("Large Original And Same-Size Impostor With Identical Metadata", async () => {
  const part = Buffer.alloc(1024*1024,0x37);
  const chunks = Array(64).fill(part);
  const correct = namedBlob([...chunks,"a"]);
  const changed = namedBlob([...chunks,"b"]);
  const app = player(webcrypto);
  app.install(correct.size,expected(...chunks,Buffer.from("a")));
  const pending = app.select(correct);
  assert.equal(app.metadata(),false);
  await pending;
  assert.equal(app.metadata(),true);
  assert.equal(app.workers.length,1);
  const retry = app.select(changed);
  assert.equal(app.metadata(),false);
  await retry;
  assert.equal(app.metadata(),false);
  assert.equal(app.controls.get("play").disabled,true);
  assert.match(app.controls.get("status").textContent,/Hash Differs/);
  assert.ok(app.workers.every(worker=>worker.terminated));
  assert.equal(app.urls.size,0);
});

test("Native, Unavailable, And Failed WebCrypto All Enforce Identity", async () => {
  const good = namedBlob(["abc"]);
  for (const crypto of [webcrypto, undefined, {subtle:{digest:async()=>{throw Error("Unavailable");}}}]) {
    const app = player(crypto);
    assert.throws(()=>app.install(3,undefined),/SHA-256/);
    assert.throws(()=>app.install(3,"f".repeat(63)),/SHA-256/);
    app.install(3,expected(Buffer.from("abc")).toUpperCase());
    await app.select(good);
    assert.equal(app.metadata(),true);
    await app.select(namedBlob(["abd"]));
    assert.equal(app.metadata(),false);
    assert.equal(app.urls.size,0);
    assert.equal(app.workers.length,crypto === webcrypto ? 0 : 2);
  }
});

test("Canceled, Failed, And Blocked Workers Keep Playback Disabled And Release URLs", async () => {
  for (const mode of ["idle", "fail", "throw"]) {
    const app = player(undefined,mode);
    app.install(3,expected(Buffer.from("abc")));
    const pending = app.select(namedBlob(["abc"]));
    if (mode === "idle") {
      await app.select(null);
      app.workers[0].onmessage({data:{digest:expected(Buffer.from("abc"))}});
    }
    await pending;
    assert.equal(app.metadata(),false);
    assert.equal(app.urls.size,0);
    if (mode !== "throw") assert.equal(app.workers[0].terminated,true);
    if (mode !== "idle") assert.match(app.controls.get("status").textContent,/Could Not Verify/);
  }
});
