// Skin.h - custom XUI notification skin (your Notify.xex, folded into the plugin).
#pragma once
#include "../Shared/XNotifyCore.h"

// Loads every colour variant from the XNotifySkins.xzp section and hooks the
// console's resource locator so "notify.xur" resolves to our scene. Call once,
// from a system thread, after boot has settled. Returns TRUE if active.
BOOL Skin_Install(HANDLE pluginModule);

// Writes the logo packed in XNotifySkins.xzp (icon.png) to <folder>\Logos\Default.png
// if that file doesn't exist yet, so there's always a logo to pick and fall back to.
BOOL Skin_WriteDefaultLogo(HANDLE pluginModule);

// Puts xam's code back the way it was. Safe to call if never installed.
void Skin_Uninstall();

// Colour used for the next notification (index into g_SkinPresets).
void Skin_SetColor(DWORD index);

// Exported to the config app (Plugin.def): live colour preview while it runs.
extern "C" VOID XNT_SetSkinPreview(LONG index);   // ordinal 1; -1 = stop previewing
extern "C" LONG XNT_GetSkinState();                // ordinal 2; 0 off, 1 active, -1 failed

#define XNT_SKIN_STATE_OFF     0
#define XNT_SKIN_STATE_ACTIVE  1
#define XNT_SKIN_STATE_FAILED -1
