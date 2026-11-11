# Handoffs

Two Cases Where Fresh Animation Has To Fit Into Existing Work. In Both, The Existing Work Sets The Terms And The New Animation Fits Them.

| Case | What Already Exists | What You Make |
| --- | --- | --- |
| Revising Part Of A Finished Film | An Animated Film With Its Narration And Music | Replacement Sections Only |
| A Single Insert For A Camera Edit | A Footage Edit Owned By The Video Edit Skill | One Animated Or 3D Clip Built To A Shot Brief |

## Revising Part Of A Finished Film

**Rebuild Only The Weakest Sections.** Agree With The Owner Which Sections Change, By Time Range Or By Beat, Before Building Anything. Sections The Owner Accepted Stay Untouched. Every Change Puts An Accepted Moment At Risk And Makes The Next Review Larger.

**Keep The Length.** A Replacement Section Occupies Exactly The Frame Range Of The Section It Replaces. The Narration And Music Around It Are Fixed, So A Single Extra Frame Pushes Everything After It Out Of Step.

**Match Frames Either Side Of Every Seam.** A Seam Is Each Boundary Between Kept And Rebuilt Material.

- Render The Last Kept Frame Before The Seam And The First Kept Frame After It From The Finished Film. These Are The Targets.
- Render The First And Last Frames Of The New Section And Set Them Beside The Targets. Compare Element Positions, Scale, Colors, Camera, Background, And The State Of Any Texture Or Boil.
- Take Starting And Ending States From The Project's Own Values. Do Not Match By Eye.
- Check A Strip Of Consecutive Frames Across Each Seam. An Element That Is Moving At The Cut Continues At The Same Speed And In The Same Direction.
- Where A Clean Match Is Impossible, Make The Seam A Deliberate Cut On A Word Or A Beat Of The Music. A Deliberate Cut Is Better Than A Near Match.

**Keep Narration And Music As Delivered.** The Voice And The Music Of The Finished Film Are Not Retimed, Releveled, Trimmed, Or Replaced. The Picture Is Fitted To Them. New Sound Events Belong Only Inside The Rebuilt Sections And Sit Under The Existing Mix. If The Revision Cannot Work Without Changing The Voice, That Is A New Request For The Owner To Decide.

**Keep The Style.** Use The Film's Existing Style Sheet, With Its Palette, Type, Line, Frame Rate, And Light. A Section That Looks Better Than Its Neighbors Stands Out As Much As One That Looks Worse.

**Archive, Do Not Delete.** Move Each Replaced Scene File, Still, And Render To An Archive Folder With The Date And The Reason. The Owner May Prefer The Earlier Version, And The Earlier Version Is The Reference For Every Seam. Earlier Deliverables Stay Where They Are.

**Review The Whole Film.** Check Each Seam With Stills And Strips, Then Take A Sparse Strip Across The Whole Film To See That The New Sections Sit In. The Owner Reviews The Whole Film In Remotion Studio, Not Only The New Parts, Before Any Video File Is Created. That Includes A Test Or Preview Export. Motion Studio Is The Owner's Review Route Only When Node.js Packages Cannot Be Installed.

**Report.** State Which Frame Ranges Changed, Which Files Were Archived And Where, What Each Seam Check Showed, And Anything Listed Under What To Report In [Review](REVIEW.md).

## A Single Insert For A Camera Edit

The Camera Edit Belongs To The [Video Edit Skill](../video-edit/SKILL.md). Its Timeline, Mix, And Cue Sheet Stay With The Edit. The Animation Side Makes One Clip That Fits.

### The Shot Brief Sets The Terms

The Brief Comes From The Edit. When It Is Missing Or Incomplete, Ask For It. Do Not Guess At A Frame Count.

| The Brief States | Why It Matters |
| --- | --- |
| Frames | The Exact Length. One Frame Short Leaves A Flash Of Footage, And One Frame Long Covers The Next Shot. |
| Rate | The Frame Rate Of The Edit. A Mismatch Stutters When The Clip Is Placed. |
| Size | The Pixel Dimensions, And Whether The Clip Fills The Frame Or Sits Over Footage |
| Cue Frames | The Frames Inside The Clip Where Events Must Land, Usually Tied To A Spoken Word In The Edit |
| Layer Order | What Sits Above And Below The Clip, Such As Captions And Titles, And Which Regions Must Stay Clear |
| Look | Palette, Type, Grain, And Light Direction, And Whether The Clip Should Feel Part Of The Footage Or A Clear Graphic Break |

When The Brief Asks For Something That Will Not Read, Such As Text On Screen For Too Few Frames, Say So And Propose A Change. The Edit Decides.

### Build To The Brief

- Hit The Frame Count Exactly, And Land Each Event On Its Cue Frame. Verify Both With A Strip.
- Design The First And Last Frames To Cut Against The Footage On Either Side. Ask The Edit For Stills Of Those Neighboring Frames And Match Brightness, Color, And Grain To Them.
- Keep Clear Of The Regions The Layer Order Reserves.
- Leave Voice And Music Out Of The Clip. Sound For The Insert Travels As A List Of Events.
- Apply The Style Guide For The Chosen Look, And [Realistic 3D](styles/realistic-3d.md) When The Insert Is A Product Render.

### Review And Return

- Show Stills And Strips While The Scene Is Still Editable. The Edit Can Hold The Slot With A Still Of The Key Frame In The Meantime.
- The Clip Is A Video File. It Is Created Only After The Owner Has Reviewed The Editable Scene In Remotion Studio And Approved It. That Includes Any Test Render. A Blender Scene Is Reviewed In Blender.
- After Approval, Return The Following.
  - The Clip, Named For Its Slot.
  - Its Sound Events. Give Each A Sound Name, A Frame Counted From The First Frame Of The Clip, And A Suggested Level.
  - The Library Entries Used. Give The Name And Pinned Revision Of Every Mark, Sound, Font, Or Part Recorded In The [Asset Library](../asset-library/SKILL.md).
  - The Path Of The Editable Scene, So A Later Revision Starts From It.

### What Stays With The Edit

| The Edit Keeps | The Animation Side Does Not |
| --- | --- |
| The Timeline And The Placement Of The Clip | Edit The Timeline File |
| The Mix, Including The Level Of Every Sound Event | Bake Sound Into The Clip Or Change Any Level |
| The Cue Sheet | Add Cues To It Directly |
| The Final Check And The Owner's Review Of The Whole Edit | Treat Approval Of The Insert As Approval Of The Edit |

If The Insert Needs More Frames Or A Different Position, Ask The Edit. A Clip That Fits Its Brief Exactly Is Worth More Than A Better Clip That Does Not Fit.
