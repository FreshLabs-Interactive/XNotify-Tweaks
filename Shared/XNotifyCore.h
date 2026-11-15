// XNotifyCore.h - shared by the DashLaunch plugin and the config app.
//
// Everything undocumented is resolved at runtime by ordinal, so the only
// link-time requirements are the stock XDK libs (xapilib.lib, xboxkrnl.lib).
//
// Ordinals verified against xkelib (cOzInABox/xkelib) and Xenia's xam table:
//   xam  463  XamGetCurrentTitleId
//   xam  652  XNotifyPositionUI
//   xam  656  XNotifyQueueUI
//   xam  658  XNotifyUISetOptions
//   xam  659  XNotifyUIGetOptions
//   xam 1191  XamLoaderGetState

#pragma once
#include <xtl.h>

// The Xbox 360 XDK headers don't define this one (desktop Windows does).
#ifndef INVALID_FILE_ATTRIBUTES
#define INVALID_FILE_ATTRIBUTES ((DWORD)-1)
#endif

// Title ID baked into the config app (App.vcxproj -> ImageXex -> TitleID).
// The plugin stays hands-off while this title is running so it doesn't fight
// the app's live preview. Keep the two in sync if you change it.
#define XNT_APP_TITLE_ID 0xFFFF584E

#define XNT_PLUGIN_MODULE_NAME "XNotifyTweaks.xex"

// ---------------------------------------------------------------------------
// Kernel exports (present in the final 2.0.21256 XDK's xboxkrnl.lib).
// If you are on an older XDK and get unresolved externals for these, add
// xkelib (github.com/cOzInABox/xkelib) and link its kernelext.lib.
// ---------------------------------------------------------------------------
typedef struct _XNT_ANSI_STRING {
    USHORT Length;
    USHORT MaximumLength;
    PCHAR  Buffer;
} XNT_ANSI_STRING;

extern "C" {
    LONG  __stdcall XexGetModuleHandle(PCSTR moduleName, PHANDLE hand);
    LONG  __stdcall XexGetProcedureAddress(HANDLE hand, DWORD ordinal, PVOID pvAddress);
    DWORD __stdcall ExCreateThread(PHANDLE pHandle, DWORD stackSize, LPDWORD threadId,
                                   PVOID apiThreadStartup, LPTHREAD_START_ROUTINE startAddress,
                                   LPVOID parameter, DWORD creationFlags);
    LONG  __stdcall KeWaitForSingleObject(PVOID object, DWORD waitReason, DWORD waitMode,
                                          BOOLEAN alertable, PLARGE_INTEGER timeout);
    VOID  __stdcall ObDereferenceObject(PVOID object);
    UCHAR __stdcall KeGetCurrentProcessType(VOID);
    LONG  __stdcall ObCreateSymbolicLink(XNT_ANSI_STRING* linkName, XNT_ANSI_STRING* deviceName);
    LONG  __stdcall ObDeleteSymbolicLink(XNT_ANSI_STRING* linkName);
}

#define XNT_EX_CREATE_FLAG_SUSPENDED      0x00000001
#define XNT_EX_CREATE_FLAG_SYSTEM         0x00000002
#define XNT_EX_CREATE_FLAG_RETURN_KTHREAD 0x00000080
#define XNT_EX_CREATE_FLAG_TITLE_EXEC     0x00000100

#define XNT_PROC_USER   1
#define XNT_PROC_SYSTEM 2

#define XNT_LOADER_STATE_TITLE_RUNNING 5

#define XNT_SUCCESS(s) (((LONG)(s)) >= 0)

// ---------------------------------------------------------------------------
// xam function pointers (filled by XNotifyCore_Resolve)
// ---------------------------------------------------------------------------
typedef DWORD (__stdcall *PFN_XamGetCurrentTitleId)(VOID);
typedef DWORD (__stdcall *PFN_XamLoaderGetState)(VOID);
typedef VOID  (__stdcall *PFN_XNotifyPositionUI)(DWORD position);
typedef VOID  (__stdcall *PFN_XNotifyQueueUI)(DWORD type, DWORD userIndex, ULONGLONG areas,
                                              PWCHAR text, PVOID context);
typedef VOID  (__stdcall *PFN_XNotifyUISetOptions)(BOOL show, BOOL showMovie, BOOL playSound, BOOL showIPTV);
typedef VOID  (__stdcall *PFN_XNotifyUIGetOptions)(BOOL* show, BOOL* showMovie, BOOL* playSound, BOOL* showIPTV);

struct XNotifyApi {
    PFN_XamGetCurrentTitleId GetCurrentTitleId;
    PFN_XamLoaderGetState    LoaderGetState;
    PFN_XNotifyPositionUI    PositionUI;
    PFN_XNotifyQueueUI       QueueUI;
    PFN_XNotifyUISetOptions  SetOptions;   // may be NULL
    PFN_XNotifyUIGetOptions  GetOptions;   // may be NULL
};

extern XNotifyApi g_Xam;

// Resolves all xam exports. Call once at startup (in the plugin: from DllMain,
// before starting the worker, so the worker never touches the loader lock).
BOOL XNotifyCore_Resolve();

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------
#define XNT_BOOT_TEXT_MAX      128     // bytes of UTF-8, including the terminator
#define XNT_BOOT_TEXT_CHARS    40      // characters the on-screen keyboard allows
#define XNT_DEFAULT_BOOT_TEXT  "XNotify Tweaks active"
#define XNT_DEFAULT_TOAST_ICON 34      // exclamation mark
#define XNT_LOGO_NAME_MAX      43      // XTAF (360 FAT) names are at most 42 characters
#define XNT_DEFAULT_LOGO       "Default.png"

enum XntPosition {
    XNT_POS_TOP_LEFT = 0,
    XNT_POS_TOP_CENTER,
    XNT_POS_TOP_RIGHT,
    XNT_POS_CENTER_LEFT,
    XNT_POS_CENTER,
    XNT_POS_CENTER_RIGHT,
    XNT_POS_BOTTOM_LEFT,
    XNT_POS_BOTTOM_CENTER,
    XNT_POS_BOTTOM_RIGHT,
    XNT_POS_COUNT
};

struct XNotifyConfig {
    BOOL  Enabled;            // master switch for the plugin
    DWORD Position;           // XntPosition
    BOOL  ApplyOptions;       // if FALSE, the four toggles below are left to the dashboard
    BOOL  ShowNotifications;
    BOOL  PlaySound;
    BOOL  ShowDuringVideo;
    BOOL  ShowDuringIPTV;
    BOOL  Enforce;            // re-apply every few seconds (beats titles that reset it)
    BOOL  BootMessage;        // toast once after boot
    DWORD ToastIcon;          // XNOTIFYUI_TYPE_* used for this tool's own toasts
    char  BootText[XNT_BOOT_TEXT_MAX];   // UTF-8; empty = default text
    BOOL  SkinEnabled;        // custom XUI toast skin (read at boot only)
    DWORD SkinColor;          // index into g_SkinPresets (Shared/SkinPresets.h)
    char  SkinLogo[XNT_LOGO_NAME_MAX];   // file in <folder>\Logos, copied to <folder>\logo.png
};

void        XNotifyConfig_Defaults(XNotifyConfig* cfg);
const char* XNotifyConfig_PositionName(DWORD pos);    // "Bottom Center"
const char* XNotifyConfig_PositionKey(DWORD pos);     // "BottomCenter"
DWORD       XNotifyConfig_PositionFlags(DWORD pos);   // XNOTIFYUI_POS_* value

// Mounts the storage device(s) under XNT drive letters for the current
// context. Pass TRUE from system threads (plugin), FALSE from a title (app).
void XNotifyCore_MountDrives(BOOL systemContext);

// Load: returns TRUE if a config file was found and parsed (cfg always gets
// defaults first, so it is valid either way).
BOOL XNotifyConfig_Load(XNotifyConfig* cfg);
// Save: creates the folder if needed. Returns TRUE on success and writes the
// path used into outPath (optional, MAX_PATH chars).
BOOL XNotifyConfig_Save(const XNotifyConfig* cfg, char* outPath);

// The XNotifyTweaks folder: the one holding the INI, else the first that
// exists or can be created. out gets e.g. "XNTHDD:\XNotifyTweaks".
// Returns the storage index (0 = HDD, 1 = USB) or -1.
int  XNotifyCore_DataFolder(char* out, size_t outSize);

// System context only (the plugin): maps XNTLOGO: to the XNotifyTweaks folder,
// so the skin's "file://XNTLOGO:/logo.png" works on HDD and USB setups.
void XNotifyCore_MountLogoDrive();

// Skin logos: PNGs in <folder>\Logos. The active one is copied to <folder>\logo.png.
BOOL XNotifyCore_IsValidLogoName(const char* name);
BOOL XNotifyCore_CopyFile(const char* src, const char* dst);   // whole file, up to 1 MB
BOOL XNotifyCore_ApplyLogo(const XNotifyConfig* cfg);           // falls back to Default.png

// Applies the config to the CURRENT title. Must be called on a title thread.
void XNotifyCore_ApplyOnTitleThread(const XNotifyConfig* cfg);

// Skin colour presets (generated into Shared/SkinPresets.h by tools/make_skins.py).
DWORD       XNotifyCore_SkinCount();
const char* XNotifyCore_SkinName(DWORD index);   // "Green / Purple"

// Queues a toast with one of the built-in icons. Must be called on a title thread.
void XNotifyCore_Toast(DWORD icon, const wchar_t* text);

// Built-in toast icons, in picker order. The system draws these; there is no
// API for custom images or colours.
struct XntIconInfo { DWORD type; const char* name; const char* key; };
int                XNotifyCore_IconCount();
const XntIconInfo* XNotifyCore_IconAt(int index);
int                XNotifyCore_IconIndex(DWORD type);   // -1 if not in the list
const char*        XNotifyCore_IconName(DWORD type);    // "Custom" if not in the list

// UTF-8 <-> UTF-16 (the INI is UTF-8, the keyboard and XNotify use wide text).
// Both always terminate the output and never split a character.
void XNotifyCore_Utf8ToWide(const char* in, wchar_t* out, int outChars);
void XNotifyCore_WideToUtf8(const wchar_t* in, char* out, int outBytes);
