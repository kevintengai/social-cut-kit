import array
import json
import math
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
from example import example
from handoff import otio
from media import analyze, graph, process
from review import make_server
from timeline import EditError, binary, load, prepare, srt, write_new


class EditorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="cut fixtures ", dir=Path(__file__).resolve().parent)
        cls.base = Path(cls.temp.name)
        cls.path = example(cls.base / "Words With Spaces")

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def model(self):
        return prepare(load(self.path), self.path.parent)

    def test_complete_graph_null_sink(self):
        model = self.model()
        self.assertEqual(4, model["duration"])
        process(model)
        self.assertFalse(list(self.base.rglob("*.mp4")))

    def test_srt_and_handoff(self):
        model = self.model()
        self.assertIn("00:00:00,250 --> 00:00:01,500", srt(model))
        tracks = otio(model)["tracks"]
        self.assertEqual(len(tracks["children"]), 4)
        self.assertEqual(tracks["children"][0]["children"][0]["OTIO_SCHEMA"], "Clip.1")
        self.assertIn("%20", tracks["children"][0]["children"][0]["media_reference"]["target_url"])
        self.assertEqual(len(tracks["markers"]), 2)

    def test_audio_analysis(self):
        report = analyze(self.path.parent / "Stereo Cue.wav", -40, .3, .3)
        self.assertEqual(len(report["silence"]), 2)
        self.assertAlmostEqual(report["silence"][0]["end"], .5, delta=.01)

    def test_handles_retime_and_bounds(self):
        doc = load(self.path)
        doc.update(captions=[], audio=[], overlays=[])
        doc["shots"] = [{"asset":"First","in":.25,"out":1.5,"lead":.25,"tail":.5,"speed":2}]
        model = prepare(doc, self.path.parent)
        self.assertEqual((0,2,1), tuple(model["shots"][0][k] for k in ("start","end","duration")))
        process(model)
        doc["shots"][0]["lead"] = 2
        with self.assertRaises(EditError):
            prepare(doc, self.path.parent)

    def test_original_stereo_retime_and_muted_second_shot(self):
        # Synthesize A/V Directly In FFmpeg. The Picture Stream Goes To A Null Sink.
        model = {"width":96,"height":64,"fps":24,"duration":1.5,"overlays":[],"captions":[],"audio":[],
                 "assets":{"AV":{"kind":"video","path":"In Memory","video":{"index":0,"width":80,"height":80},"audio":{"index":1}}},
                 "shots":[{"asset":"AV","start":0,"end":1,"duration":.5,"speed":2,"gain":1,"fit":"cover"},
                          {"asset":"AV","start":0,"end":1,"duration":1,"speed":1,"gain":0,"fit":"contain"}]}
        _, expression = graph(model)
        source = "testsrc2=size=80x80:rate=24:duration=1[out0];aevalsrc=0.1*sin(2*PI*220*t)|0.2*sin(2*PI*440*t):s=48000:d=1[out1]"
        args = [binary("ffmpeg"),"-hide_banner","-loglevel","error","-nostdin",
                "-f","lavfi","-i",source,"-f","lavfi","-i",source,"-filter_complex_threads","1",
                "-filter_complex",expression,"-map","[picture]","-f","null","-",
                "-map","[sound]","-c:a","pcm_s16le","-f","s16le","pipe:1"]
        result = subprocess.run(args, capture_output=True, check=True)
        samples = array.array("h")
        samples.frombytes(result.stdout)
        if sys.byteorder != "little":
            samples.byteswap()
        self.assertEqual(48000 * 2 * 1.5, len(samples))
        left, right = samples[960:9600:2], samples[961:9601:2]
        left_rms = math.sqrt(sum(v*v for v in left) / len(left))
        right_rms = math.sqrt(sum(v*v for v in right) / len(right))
        self.assertGreater(right_rms, left_rms * 1.8)
        self.assertEqual(0,max(samples[53000:]))

    def test_reframe_color_caption_and_single_pixel(self):
        doc = load(self.path)
        doc["shots"][0].update(zoom=1.7,pan_x=.8,pan_y=-.25,brightness=.8,contrast=1.1,saturation=0)
        doc["caption_style"] = {"font":"Georgia","color":"#86D730","outline":"#1A2540","stroke":3,"size":24,"margin":12}
        model = prepare(doc,self.path.parent)
        process(model)
        self.assertLess(model["shots"][0]["geometry"]["crop"][0],160)
        inputs, expression = graph(model,False)
        args = [binary("ffmpeg"),"-hide_banner","-loglevel","error","-nostdin",*inputs,"-filter_complex_threads","1",
                "-filter_complex",expression+";[picture]select='eq(n,2)',crop=2:2:20:20,format=rgb24[pixels];[sound]anullsink",
                "-map","[pixels]","-frames:v","1","-f","rawvideo","pipe:1"]
        result = subprocess.run(args,check=True,capture_output=True)
        self.assertEqual(12,len(result.stdout))
        self.assertLessEqual(max(result.stdout[:3]) - min(result.stdout[:3]),3)

    def test_overwrite_and_unapproved_render(self):
        target = self.base / "Keep.srt"
        write_new(target,"Keep This")
        with self.assertRaises(FileExistsError):
            write_new(target,"Replacement")
        self.assertEqual("Keep This",target.read_text())
        result = subprocess.run([sys.executable,"-B",str(SCRIPTS / "edit_video.py"),"render",str(self.path),
                                 str(self.base / "Unapproved.mp4")],capture_output=True,text=True)
        self.assertNotEqual(0,result.returncode)
        self.assertIn("Owner Review",result.stderr)
        self.assertFalse((self.base / "Unapproved.mp4").exists())

    def test_browser_save_range_and_revision(self):
        project = self.path.with_name("Review Copy.json")
        write_new(project,self.path.read_text())
        with make_server(project) as server:
            thread = threading.Thread(target=server.serve_forever,daemon=True)
            thread.start()
            try:
                self.assertIn(b"Editable Timeline",urlopen(server.url).read())
                state = json.load(urlopen(server.url+"state"))
                req = Request(server.url+"media/First",headers={"Range":"bytes=0-7"})
                with urlopen(req) as media:
                    self.assertEqual(media.status,206)
                    self.assertEqual(media.read(),b"\x89PNG\r\n\x1a\n")
                state["project"]["title"] = "Saved Cut"
                body = json.dumps({"project":state["project"],"revision":state["revision"]}).encode()
                req = Request(server.url+"save",data=body,headers={"Content-Type":"application/json","Origin":server.origin})
                saved = json.load(urlopen(req))
                self.assertEqual(saved["model"]["title"],"Saved Cut")
                self.assertEqual(load(project)["title"],"Saved Cut")
                with self.assertRaises(HTTPError) as failure:
                    urlopen(req)
                self.assertEqual(failure.exception.code,409)
                failure.exception.close()
            finally:
                server.shutdown()
                thread.join()


if __name__ == "__main__":
    unittest.main()
