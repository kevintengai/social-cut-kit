"""Offline Checks For The Resolve 21.1 Native API Contract."""

import math
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import resolve_native as native
from resolve_native_plan import plan_timeline
from timeline import EditError


class NativeResolveTests(unittest.TestCase):
    def test_plan_preserves_audio_overlaps_and_geometry(self):
        v = {"width": 1920, "height": 1080}
        model = dict(title="Test", width=1080, height=1920, fps=30, duration=1,
                     assets={"Film": {"kind": "video", "path": "original.mov", "video": v, "audio": {"channels": 2}}},
                     shots=[dict(asset="Film", at=0, start=2, end=4, duration=1, speed=2, gain=0,
                                 geometry={"browser": [0, .341796875, 1, .31640625]},
                                 brightness=1, contrast=1, saturation=1)],
                     overlays=[dict(asset="Film", at=t, end=e, start=0, x=0, y=0, width=540)
                               for t,e in [(0,.5),(.25,.75),(.75,1)]],
                     captions=[], audio=[], caption_style={})
        plan = plan_timeline(model)
        picture, audio, *overlays = plan["clips"]
        self.assertEqual((picture["frames"], picture["source_in"], picture["source_out"]), (30, 2, 4))
        self.assertEqual(picture["transform"], {"ZoomX":1, "ZoomY":1, "Pan":0, "Tilt":0})
        self.assertEqual((audio["kind"], audio["gain"], audio["shot"]), ("audio", 0, picture["shot"]))
        self.assertEqual([x["track"] for x in overlays], [2, 3, 2])
        self.assertEqual(overlays[0]["transform"]["Pan"], -270)
        self.assertEqual(overlays[0]["transform"]["Tilt"], 808.125)

    def test_retime_seeds_record_length_and_preserves_original_audio(self):
        app, project, folder = Mock(), Mock(), Mock()
        a = native.Assembly(app, project, {"assets": {"Film":{"kind":"video"}}, "fps":24}, folder)
        a.base = 86400
        a.timeline = Mock()
        app.GetProjectManager.return_value.GetCurrentProject.return_value = project
        project.GetCurrentTimeline.return_value = a.timeline
        media = Mock()
        media.GetClipProperty.return_value = 30
        a.sources = {"Film": media}
        item = Mock()
        item.GetDuration.return_value = 24
        item.GetStart.return_value = 86412
        item.GetTrackTypeAndIndex.return_value = ["audio", 1]
        item.GetSourceStartTime.return_value = 2
        item.GetSourceEndTime.return_value = 4
        item.GetSpeed.return_value = {"Percentage":200, "PitchCorrection":True}
        item.GetProperties.return_value = {"AudioVolume":20*math.log10(.5)}
        a.pool.AppendToTimeline.return_value = [item]
        clip = dict(role="source_audio", asset="Film", kind="audio", track=1, at=12, frames=24,
                    source_in=2, source_out=4, speed=2, gain=.5)
        self.assertIs(a.media_clip(clip), item)
        a.pool.AppendToTimeline.assert_called_once_with([dict(mediaPoolItem=media, mediaType=2,
            trackIndex=1, recordFrame=86412, startFrame=60.0, endFrame=90.0)])
        item.SetSpeed.assert_called_once_with({"Percentage":200, "PitchCorrection":True, "RippleTimeline":False})
        item.SetProperties.assert_called_once_with({"AudioVolume":20*math.log10(.5)})

    def test_still_duration_uses_marks_on_the_private_copy(self):
        a = native.Assembly(Mock(), Mock(), {"assets":{"Still":{"kind":"image"}}}, Mock())
        media, item = Mock(), Mock()
        a.sources, a.base = {"Still": media}, 0
        item.GetStart.return_value, item.GetDuration.return_value = 1, 180
        item.GetTrackTypeAndIndex.return_value = ["video", 2]
        clip = dict(role="overlay", kind="video", track=2, at=1, frames=180, asset="Still")
        with patch.object(a, "append", return_value=item) as append:
            self.assertIs(a.media_clip(clip), item)
        media.SetMarkInOut.assert_called_once_with(0, 179, "video")
        append.assert_called_once_with(media, clip)
        media.ClearMarkInOut.assert_called_once_with("video")

    def test_duplicate_name_before_and_during_assembly(self):
        app = Mock()
        manager = app.GetProjectManager.return_value
        project = manager.GetCurrentProject.return_value
        project.GetName.return_value = "Project"
        app.GetVersion.return_value = [21, 1, 0, 14]
        project.GetTimelineByIndex.return_value.GetName.return_value = "Cut"
        project.GetTimelineCount.return_value = 1
        with self.assertRaisesRegex(EditError, "Already Exists"):
            native.build(app, {}, "Project", "cut")
        project.GetMediaPool.assert_not_called()
        pool = project.GetMediaPool.return_value
        folder = pool.AddSubFolder.return_value
        folder.GetClipList.return_value = []
        folder.GetSubFolderList.return_value = []
        project.GetTimelineCount.side_effect = [0, 1]
        with patch.object(native.Assembly,"setup"), patch.object(native.Assembly,"assemble"):
            with self.assertRaisesRegex(EditError, "Already Exists"):
                native.build(app, {}, "Project", "cut")
        pool.DeleteFolders.assert_called_once_with([folder])
        manager.SaveProject.assert_not_called()

    def test_other_project_is_left_alone_on_failure(self):
        app = Mock()
        app.GetVersion.return_value = [21,1]
        manager = app.GetProjectManager.return_value
        project, replacement = Mock(), Mock()
        manager.GetCurrentProject.side_effect = [project, replacement]
        project.GetName.return_value = "Project"
        project.GetTimelineCount.return_value = 0
        with patch.object(native.Assembly, "setup", side_effect=EditError("Switched")):
            with self.assertRaisesRegex(EditError, "Destination Project Changed"):
                native.build(app, {}, "Project", "Cut")
        project.GetMediaPool.return_value.DeleteFolders.assert_not_called()
        project.SetCurrentTimeline.assert_not_called()
        replacement.SetCurrentTimeline.assert_not_called()

    def test_refuses_wrong_host_or_open_project(self):
        app = Mock()
        app.GetVersion.return_value = [20,3]
        with self.assertRaisesRegex(EditError, "21.1"):
            native.build(app, {}, "Project", "Cut")
        app.GetProjectManager.assert_not_called()
        app.GetVersion.return_value = [21,1]
        app.GetProjectManager.return_value.GetCurrentProject.return_value.GetName.return_value = "Other"
        with self.assertRaisesRegex(EditError, "Named Destination"):
            native.build(app, {}, "Project", "Cut")


if __name__ == "__main__":
    unittest.main()
