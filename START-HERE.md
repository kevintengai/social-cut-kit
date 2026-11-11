# Start Here

This Sheet Tells You What To Install, Which Skill To Ask For, And What To Say To Your Agent. Read It Once Before You Open Anything Else.

## 1. Install

You Need Python 3.10 Or Later. The Footage Editor Also Needs FFmpeg And FFprobe On Your System Path.

From The Unzipped Folder, Run One Of These. Then Restart Or Reload Your Agent.

```sh
python install.py --agent claude
python install.py --agent codex
```

To Check What Is Missing On Your Machine, Run This. It Installs Nothing And Prints An Install Command For Each Missing Tool.

```sh
python skills/video-edit/scripts/edit_video.py setup
```

## 2. Pick The Skill For Your Task

| You Want To | Ask For This Skill | Say Something Like |
| --- | --- | --- |
| Decide What A Video Should Sell Or Prove | `teng-campaign-brief` | "Use The Campaign Brief Skill To Turn My Offer Into A Brief." |
| Find Ideas, Write A Script, Or Learn From A Posted Video | `video-script` | "Use The Video Script Skill To Brainstorm Ideas For My Next Video." |
| Plan The Shots Before Filming | `director` | "Use The Director Skill To Turn This Script Into A Shot Board." |
| Edit Recorded Footage | `video-edit` | "Use The Video Edit Skill To Edit The Footage In This Folder." |
| Make An Animated Explainer Or Title | `animated-video` | "Use The Animated Video Skill To Turn This Script Into An Animated Video." |
| Find Or Reuse Footage, Sounds, Or Graphics | `asset-library` | "Use The Asset Library Skill To Search My Library Before Sourcing Anything." |
| Review How A Session Went And Improve Your Instructions | `reflect` | "Use The Reflect Skill To Review This Session And Show Me The Findings First." |
| Test Whether A Change To A Skill Really Helps | `rsi` | "Use The RSI Skill To Test One Improvement Against The Current Version." |

## 3. A Typical Order

Most Videos Use Three Or Four Skills In This Order. Every Skill Also Works Alone.

1. **Brief.** `teng-campaign-brief` Sets The Offer, The Proof, And The Viewer Action.
2. **Script.** `video-script` Writes The Timed Script And The List Of Shots To Capture.
3. **Plan.** `director` Builds The Shot Board.
4. **Make.** `video-edit` Cuts Camera Footage. `animated-video` Draws Animation. Use Whichever Owns The Final Video.
5. **Learn.** After Posting, `video-script` Reviews The Analytics. After Any Session, `reflect` Reviews The Work.

## 4. Three Rules The Kit Follows

- **You Approve Before Any Export.** The Agent Saves An Editable Project For You To Review. It Creates No Video File, Including Test Or Preview Files, Until You Say So.
- **Your Original Audio Stays As Recorded.** Gain And Loudness Changes Happen Only When You Ask.
- **Use Only Material You Have Rights To.** The Kit Does Not Download Other People's Posts.

## 5. Try It Before Installing

```sh
python skills/video-edit/scripts/edit_video.py review examples/repair-desk/timeline.json
```

An Eight-Second Example Edit Opens In Your Browser. For Animation, Open `skills/animated-video/studio/index.html`. For Icons, Open `art/index.html`.

## 6. Where To Read More

Each Skill Has Its Own Guide At `skills/NAME/SKILL.md`. The [Product Overview](README.md) Lists What The Download Contains, And [Usage Terms](USAGE.md) Covers What You May Do With It.

If You Use Remotion For Animation, Each Generated Project Needs Its Own `npm install`, And Remotion Has Its Own License Terms. See The [Remotion Adapter Guide](skills/animated-video/adapter/README.md).
