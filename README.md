# XNotify Tweaks

Change where Xbox 360 notifications ("toasts") appear, and whether they show and chime, on **any dashboard**: Aurora, FSD, the stock dash, and inside games.

There are two pieces:

| File | What it is | Where it goes |
|---|---|---|
| `XNotifyTweaks.xex` | DashLaunch plugin. Loads at boot and re-applies your settings every time a title starts (a dashboard counts as a title). | `Hdd:\Plugins\XNotifyTweaks.xex` |
| `default.xex` | **XNotify Tweaks Config**, the on-console settings app with a controller menu and live preview. | `Hdd:\Apps\XNotifyTweaks\default.xex` |

**Why it needs a plugin:** the console resets the notification position every time a title launches, so a standalone app can only change it for itself. The plugin stays loaded across title changes and puts your settings back each time. That's what makes it work on every dashboard.

---

## 1. What you need

- An RGH/JTAG console with **DashLaunch 3.21** (you have this).
- A Windows PC with:
  - **Visual Studio 2010** (with SP1). The Xbox 360 toolchain only plugs into VS2010.
  - The **Xbox 360 SDK (XDK) 2.0.21256**, the final release, installed on top of VS2010. Microsoft never released it publicly, so you'll have to source it yourself. Other XDK versions may work, but see Troubleshooting.
  - An FTP client (FileZilla, WinSCP…). Aurora and FSD both have an FTP server built in.
- Python 3 with Pillow, **only** if you want to change the app's font (`tools/gen_font.py`).

## 2. Build

1. Open `XNotifyTweaks.sln` in Visual Studio 2010.
2. Pick **Release | Xbox 360** in the toolbar.
3. **Build → Build Solution.**
4. The outputs land in `build\Release\`:
   - `XNotifyTweaks.xex`: the plugin
   - `default.xex`: the config app

## 3. Install

1. FTP into the console and copy:
   - `XNotifyTweaks.xex` → `Hdd:\Plugins\` (create the folder if needed)
   - `default.xex` → `Hdd:\Apps\XNotifyTweaks\`
2. Download your `launch.ini` (normally `Hdd:\launch.ini`). Under `[Plugins]`, add the plugin on the first free line (DashLaunch allows `plugin1` to `plugin5`):
   ```ini
   [Plugins]
   plugin1 = Hdd:\Plugins\XNotifyTweaks.xex
   ```
   Upload it back, overwriting the old one.
3. **Reboot the console.** With "Boot message" on (the default), you'll see an "XNotify Tweaks active" toast once the dashboard loads.

### Launching the config app

- **Aurora:** add `Hdd:\Apps` as a scan path (Settings → Content → Scan Paths, type *Applications*) and rescan. *XNotify Tweaks Config* shows up under Homebrew/Applications.
- **FSD:** add `Hdd:\Apps` as a content path (type *Homebrew*) and rescan.
- **Stock dashboard:** it can't browse loose `.xex` files. Either launch the app from Aurora/FSD once, or bind it to a DashLaunch quick-launch button in `launch.ini`, e.g.:
  ```ini
  [QuickLaunchButtons]
  BUT_X = Hdd:\Apps\XNotifyTweaks\default.xex
  ```

### Cover art in Aurora

The app's Title ID is **`FFFF584E`**. It's set in `App/App.vcxproj` (ImageXex → TitleID). Aurora looks up cover art online by Title ID, and there's none online for homebrew, so the art ships with the project in `art/`:

| File | Contains |
|---|---|
| `GCFFFF584E.asset` | Box art (full wrap: back, spine, front) |
| `BKFFFF584E.asset` | Background |
| `GLFFFF584E.asset` | Icon + banner |

1. Launch Aurora with the app scanned in, so it appears in your list. Aurora creates a folder for it: `<Aurora folder>\Data\GameData\FFFF584E_<number>\` (for example `Hdd1:\Aurora\Data\GameData\FFFF584E_00000012\`). It contains small placeholder `.asset` files.
2. FTP the three `.asset` files from `art/` into that folder, overwriting the placeholders.
3. Restart Aurora.

**Afterwards:** don't run *Download assets* on this title, because Aurora would replace the art with empty placeholders again. If that happens, just repeat step 2.

**Checking the Title ID:** Aurora's title details should show `FFFF584E`. If it says `00000000`, check **Project Properties → Image Conversion → Title ID** and rebuild. Then remove the app from Aurora and rescan, because Aurora caches what it read the first time.

These `.asset` files are Aurora-only; FSD and the stock dash don't use them. The PNGs in `art/` are the editable sources. Change them, or `tools/make_art.py`, and rebuild the assets with `python tools/aurora_asset.py --check`, which needs Pillow and numpy.

## 4. Using the app

| Button | Action |
|---|---|
| D-pad / left stick | Move; Left/Right changes values |
| A | Toggle / select |
| X | Send a test notification |
| START | Save |
| B | Back to your dashboard (asks first if anything is unsaved) |

- Every change **previews live** inside the app. Moving the position sends a sample toast so you can see where it lands. The little 3×3 grid shows which corner is selected.
- The header shows **Plugin: loaded** or **NOT loaded**. If it says NOT loaded, recheck step 3.
- **Override notification options** is off by default, which leaves show/sound/video/IPTV to the dashboard's own settings. Turn it on to have the plugin enforce your four toggles on every title.
- **Enforce** re-applies every 5 seconds. Only turn it on if a particular game keeps moving notifications back.
- **Boot message text:** press A to type your own message on the on-screen keyboard (up to 40 characters). Leave it empty to use the default. You get a preview toast right away.
- **Toast icon:** Left/Right cycles through the console's built-in icons. Press X to preview the selected one. This sets the icon for the toasts XNotify Tweaks sends (boot message and test). Other system notifications keep their own icons.
- Saved settings take effect on the next title launch, which includes going back to the dashboard when you exit the app.

## 4b. Custom notification skin (your Notify.xex)

Your animated XUI toast is built into the plugin, with 8 colour presets you can switch from the app. It's **off by default**.

**Turn it on:**
1. **Remove `Notify.xex` from `launch.ini`.** Both plugins hook the same xam function, so running both would conflict.
2. In the app, set **Custom notification skin** to On, press START to save, and reboot.
3. Pick a colour under **Skin colors**. It applies to the next notification, so there's no reboot for colour changes. Press X to preview.

Switching the skin itself on or off always needs a reboot, because the hook is installed once at boot. The status line under the help text tells you whether the skin is active.

**Presets (24):** Green / Purple (your design, unchanged), Red / Black, Pink / White, Red / Black / White, Blue / Silver / Black, Gold / Green, Blue / Orange, Pink / Purple, Red / Blue / White, Blue / Cyan, Ice / Blue, Teal / Navy, Mint / Teal, Orange / Gold, Orange / Pink, Crimson / Gold, Red / Grey, Purple / Green, Purple / Gold, Lime / Grey, Gold / Black, Yellow / Black, Silver / Grey, Black / White. `skins/swatches.png` gives a rough idea of each.

**How it's built:** `tools/make_skins.py` takes your compiled visual (`skins/src/visual.xur`) and makes one copy per preset. Each copy only has its colour table and its visual name changed; the script checks that every other byte matches. It packs them with their scenes, your logo (`icon.png`) and the popup sound into `Plugin/XNotifySkins.xzp`. That's 58 KB, versus about 490 KB for the old package, which carried a full copy of the HUD assets. The xzp is already built. Only rerun the script if you change something:

```
python tools/make_skins.py --check
```

**One-time step after this update: recompile your visual.** The fixed design is in `skins/src/visual.xui`. Its bar, both end caps and the disc behind the logo now share one solid body colour, the text no longer flashes magenta at the end, and it no longer uses the PC-only "Arial Unicode MS" font. Only the XUI tool can compile a `.xui`:
1. Open `skins/src/visual.xui` in the XUI tool and save/compile it as `skins/src/visual.xur`, replacing the old one.
2. Run `python tools/make_skins.py --check`. It refuses to build from an old `visual.xur`, so you can't accidentally ship the unfixed version.
3. Rebuild the plugin and the app, and copy both `.xex` files to the console.

**Changing the design:**
- **New colours:** edit the `PRESETS` list at the top of `tools/make_skins.py`. Each entry is a key, a name, an accent colour (edges and text), a secondary colour (rings and effects) and a body colour (the bar's solid fill). In your `.xui`, the body is the marker colour `0xFF141414`; anything you paint with that exact colour follows the preset's body colour. Rerun the script, then rebuild the plugin *and* the app, because the preset names are compiled into both through `Shared/SkinPresets.h`.
- **New animation or layout:** edit `skins/src/visual.xui` in the XUI tool, keeping its Id `eacbe6b504a`. Compile it over `skins/src/visual.xur`, rerun the script and rebuild.
- `skins/xui/` contains each preset as a `.xui` file, so you can open any colour variant in the XUI tool.

**Skin logo (picked in the app):**
1. Over FTP, put square PNGs (about 128×128, transparent background, names up to 42 characters) in `Hdd:\XNotifyTweaks\Logos\`. Use `Usb0:` instead if your settings live on USB.
2. In the app, pick one under **Skin logo** and press START. The app copies it to `Hdd:\XNotifyTweaks\logo.png`, which is the file the skin displays.
3. The next notification should show it. The console may cache the old image, so if it doesn't change, reboot.

How it works:
- **`Default.png`:** the plugin writes the logo packed in the skin package (`skins/src/icon.png`) to `Logos\Default.png`. It only does this if that file doesn't exist, so you can replace it.
- **Boot:** at every boot the plugin re-copies your chosen logo to `logo.png`. If you delete the file you picked, it falls back to `Default.png`.
- **The drive name:** the visual's logo path is `file://XNTLOGO:/logo.png`. The plugin maps `XNTLOGO:` to whichever XNotifyTweaks folder holds your settings, on HDD or USB.

**This needs one more compile of `visual.xui`** (logo path changed): open it in the XUI tool, save it as `skins/src/visual.xur`, run `python tools/make_skins.py --check`, then rebuild **both** projects. Until you do, the script prints a note and the logo picker has no effect.

**If the logo shows blank after this:** the console's skin system didn't accept the `file://` path. To go back, set `xenonLogo1`'s ImagePath to `icon.png` in the XUI tool and recompile. The logo is then packed again and changed by replacing `skins/src/icon.png` and rebuilding.

**Why the icon didn't show, and what changed:**
- **Your logo:** the visual's `xenonLogo1` element asks for `icon.png`, but the old package only contained `popuplogo.png`. On top of that, `XuiVisualSetBasePath(L"skin://")` pointed relative paths at the console's own skin instead of your package. Now the logo is packed as `icon.png` and the base-path call is off. If you want the old behaviour back, set `XNT_SKIN_USE_SYSTEM_BASE_PATH` to 1 in `Plugin/Skin.cpp`.
- **The notification's icon (the Toast icon setting):** your visual draws it through the `Image` presenter. Its timeline only shows it during frames 70–120 of each loop, taking turns with the logo, and frames 125–185 hide it again. That comes from the template's design. To show the icon the whole time, open the visual in the XUI tool, edit the `Image` timeline so it stays visible, and hide `xenonLogo1`.

**Not tested on hardware yet:**
- The console might cache the popup scene after the first notification. If colour changes only show up after a reboot, that's why.
- With 24 presets the skin package is about 150 KB. If it stops loading next to another plugin, move `<baseaddr>` in `Plugin/xex.xml` to a free 64 KB-aligned address.
- Your old startup message ("FreshLabs RGH") is now the app's **Boot message text** setting.

## 5. Settings file

`Hdd:\XNotifyTweaks\XNotifyTweaks.ini`, or `Usb0:\XNotifyTweaks\XNotifyTweaks.ini` if there's no HDD. You can also edit it over FTP; the plugin re-reads it on every title launch.

```ini
[XNotifyTweaks]
Enabled=1
Position=TopRight        ; TopLeft TopCenter TopRight CenterLeft Center CenterRight BottomLeft BottomCenter BottomRight
ApplyOptions=0           ; 1 = enforce the four options below
ShowNotifications=1
PlaySound=1
ShowDuringVideo=1
ShowDuringIPTV=1
Enforce=0                ; 1 = re-apply every 5 s
BootMessage=1
ToastIcon=Exclamation    ; name from the list below, or a raw number 0-255
BootMessageText=XNotify Tweaks active   ; UTF-8, empty = default
Skin=0                   ; 1 = custom XUI skin (reboot to apply)
SkinColor=GreenPurple    ; any preset key from PRESETS in tools/make_skins.py, e.g. RedBlackWhite, BlueSilverBlack
SkinLogo=Default.png     ; a PNG in the Logos folder
```

**ToastIcon names:** Exclamation, Achievement, FriendOnline, OneFriendOnline, MultiFriendOnline, FriendRequest, GameInvite, GameInviteSent, Generic, Mailbox, PersonalMessage, MultiPending, ChatRequest, ChatCallback, ChatCallbackSent, ChatJoin, ChatLeave, SignedIn, SignedInLive, SignedInNeedPass, SignedOut, ConnectionLost, DownloadComplete, Music, HappyFace, SadFace, Hammer, RemovedMU, RemovedGamepad, HybridDisc, Kicked, Trash.

You can type a raw number into the INI to try icon types that aren't in the list. The app shows those as "Custom". Unlisted types are undocumented, so some may show no icon at all.

**Colours and custom images:** the console draws every notification itself, using its built-in system skin. The notification call only takes text and an icon type, so there's no setting for toast colours or your own pictures. Changing those would mean modifying system files, which this tool deliberately doesn't do.

## 6. How it works (for tinkering)

```
Shared/XNotifyCore.*   kernel/xam imports, INI load/save, "apply" + "toast"
Plugin/dllmain.cpp     system thread: watches title ID + loader state, then
                       spawns a short TITLE thread to call XNotify* (xam
                       ignores these calls from system threads on real hardware)
App/main.cpp           menu, input, live preview
App/Renderer.cpp       tiny D3D9 shader-based 2D renderer (360 has no fixed function)
App/FontAtlas.h        DejaVu Sans baked to a 4-bit atlas by tools/gen_font.py
```

Undocumented xam exports are resolved at runtime by ordinal (`XexGetProcedureAddress`): 463 `XamGetCurrentTitleId`, 652 `XNotifyPositionUI`, 656 `XNotifyQueueUI`, 658/659 `XNotifyUISetOptions`/`GetOptions`, 1191 `XamLoaderGetState`. These were checked against both xkelib and Xenia's export table.

After a title launches, the plugin applies your settings at **1.5 s** and again at **8 s**, to catch games that set their own position while they start up. With Enforce on, it also re-applies every 5 s. It skips the config app's own title ID (`0xFFFF584E`) so it doesn't overwrite the live preview.

## 7. Troubleshooting

| Problem | Fix |
|---|---|
| Header says **Plugin: NOT loaded** | Check the `launch.ini` path and spelling, and that the file is really at `Hdd:\Plugins\XNotifyTweaks.xex`. Then reboot. |
| Plugin won't load next to another plugin | Base-address clash. Change `<baseaddr addr="0x91AC0000"/>` in `Plugin/xex.xml` to another 64 KB-aligned free address and rebuild. |
| One game ignores the position | Turn on **Enforce**. Some games draw their own popups, which this can't affect. |
| Build error: `XNOTIFYUI_POS_…` undeclared | Your XDK spells the macros differently. Find them in `xbox.h` and fix the table at the top of `Shared/XNotifyCore.cpp`. |
| Link error: `XexGetModuleHandle`, `ExCreateThread`, `ObCreateSymbolicLink`… unresolved | Older XDK. Add [xkelib](https://github.com/cOzInABox/xkelib), build its `kernelext.lib` for your SDK version, and add it to the linker inputs. |
| Build error: `XLAUNCH_KEYWORD_DEFAULT_APP` | Replace it with `XLAUNCH_KEYWORD_DASH` in `App/main.cpp`. |
| Console misbehaves after installing | Delete the `pluginN = …XNotifyTweaks.xex` line from `launch.ini` (over FTP, or with the drive on a PC) and reboot. |

**Keep the console off Xbox Live** while running unsigned plugins. That's standard RGH advice, nothing specific to this tool.

## 8. Changing things

- **Title ID:** if you change `<TitleID>` in `App/App.vcxproj`, change `XNT_APP_TITLE_ID` in `Shared/XNotifyCore.h` to match.
- **App colours:** the `COL_*` constants at the top of `App/main.cpp` (ARGB hex).
- **Font:** run `python tools/gen_font.py path\to\font.ttf 28 App\FontAtlas.h`. DejaVu Sans, the default, is under a free licence that allows embedding.
- **Timings:** see the constants at the top of `Plugin/dllmain.cpp`.
