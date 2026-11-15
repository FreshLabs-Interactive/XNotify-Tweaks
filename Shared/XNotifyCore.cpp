// XNotifyCore.cpp - shared by the DashLaunch plugin and the config app.
#include "XNotifyCore.h"
#include "SkinPresets.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>


XNotifyApi g_Xam = { 0 };

// ---------------------------------------------------------------------------
// Export resolution
// ---------------------------------------------------------------------------
static BOOL ResolveOrdinal(HANDLE module, DWORD ordinal, PVOID* out)
{
    *out = NULL;
    if (!XNT_SUCCESS(XexGetProcedureAddress(module, ordinal, out)))
        *out = NULL;
    return *out != NULL;
}

BOOL XNotifyCore_Resolve()
{
    HANDLE xam = NULL;
    if (!XNT_SUCCESS(XexGetModuleHandle("xam.xex", &xam)) || xam == NULL)
        return FALSE;

    BOOL ok = TRUE;
    ok &= ResolveOrdinal(xam,  463, (PVOID*)&g_Xam.GetCurrentTitleId);
    ok &= ResolveOrdinal(xam, 1191, (PVOID*)&g_Xam.LoaderGetState);
    ok &= ResolveOrdinal(xam,  652, (PVOID*)&g_Xam.PositionUI);
    ok &= ResolveOrdinal(xam,  656, (PVOID*)&g_Xam.QueueUI);
    // The two option calls are optional: if they ever fail to resolve, the
    // rest of the tool (position, toasts) still works.
    ResolveOrdinal(xam, 658, (PVOID*)&g_Xam.SetOptions);
    ResolveOrdinal(xam, 659, (PVOID*)&g_Xam.GetOptions);
    return ok;
}

// ---------------------------------------------------------------------------
// Positions
// ---------------------------------------------------------------------------
struct PositionInfo { const char* name; const char* key; DWORD flags; };

static const PositionInfo s_Positions[XNT_POS_COUNT] = {
    { "Top Left",      "TopLeft",      XNOTIFYUI_POS_TOPLEFT      },
    { "Top Center",    "TopCenter",    XNOTIFYUI_POS_TOPCENTER    },
    { "Top Right",     "TopRight",     XNOTIFYUI_POS_TOPRIGHT     },
    { "Center Left",   "CenterLeft",   XNOTIFYUI_POS_CENTERLEFT   },
    { "Center",        "Center",       XNOTIFYUI_POS_CENTER       },
    { "Center Right",  "CenterRight",  XNOTIFYUI_POS_CENTERRIGHT  },
    { "Bottom Left",   "BottomLeft",   XNOTIFYUI_POS_BOTTOMLEFT   },
    { "Bottom Center", "BottomCenter", XNOTIFYUI_POS_BOTTOMCENTER },
    { "Bottom Right",  "BottomRight",  XNOTIFYUI_POS_BOTTOMRIGHT  },
};

const char* XNotifyConfig_PositionName(DWORD pos)
{
    return pos < XNT_POS_COUNT ? s_Positions[pos].name : "Bottom Center";
}

const char* XNotifyConfig_PositionKey(DWORD pos)
{
    return pos < XNT_POS_COUNT ? s_Positions[pos].key : "BottomCenter";
}

DWORD XNotifyConfig_PositionFlags(DWORD pos)
{
    return pos < XNT_POS_COUNT ? s_Positions[pos].flags : XNOTIFYUI_POS_BOTTOMCENTER;
}

void XNotifyConfig_Defaults(XNotifyConfig* cfg)
{
    memset(cfg, 0, sizeof(*cfg));   // keeps BootText's unused bytes zero (the app memcmp()s configs)
    cfg->Enabled           = TRUE;
    cfg->Position          = XNT_POS_BOTTOM_CENTER;   // console default
    cfg->ApplyOptions      = FALSE;                   // leave dash toggles alone until the user opts in
    cfg->ShowNotifications = TRUE;
    cfg->PlaySound         = TRUE;
    cfg->ShowDuringVideo   = TRUE;
    cfg->ShowDuringIPTV    = TRUE;
    cfg->Enforce           = FALSE;
    cfg->BootMessage       = TRUE;
    cfg->ToastIcon         = XNT_DEFAULT_TOAST_ICON;
    strcpy(cfg->BootText, XNT_DEFAULT_BOOT_TEXT);
    cfg->SkinEnabled       = FALSE;
    cfg->SkinColor         = 0;
    strcpy(cfg->SkinLogo, XNT_DEFAULT_LOGO);
}

DWORD XNotifyCore_SkinCount() { return XNT_SKIN_COUNT; }

const char* XNotifyCore_SkinName(DWORD index)
{
    return g_SkinPresets[index < XNT_SKIN_COUNT ? index : 0].name;
}

// ---------------------------------------------------------------------------
// Toast icons (values from xkelib's XNOTIFYUI_TYPE enum). Types that change
// notification state rather than just showing an icon (e.g. 23,
// CANCELPERSISTENT) are left out on purpose.
// ---------------------------------------------------------------------------
static const XntIconInfo s_Icons[] = {
    { 34, "Exclamation",               "Exclamation" },
    { 27, "Achievement",               "Achievement" },
    {  0, "Friend online",             "FriendOnline" },
    { 26, "One friend online",         "OneFriendOnline" },
    { 25, "Several friends online",    "MultiFriendOnline" },
    {  2, "Friend request",            "FriendRequest" },
    {  1, "Game invite",               "GameInvite" },
    { 22, "Game invite sent",          "GameInviteSent" },
    {  3, "Generic (mail)",            "Generic" },
    { 29, "Mailbox",                   "Mailbox" },
    {  5, "Personal message",          "PersonalMessage" },
    {  4, "Multiple pending",          "MultiPending" },
    { 10, "Chat request",              "ChatRequest" },
    { 17, "Chat callback",             "ChatCallback" },
    { 24, "Chat callback sent",        "ChatCallbackSent" },
    { 20, "Chat join",                 "ChatJoin" },
    { 21, "Chat leave",                "ChatLeave" },
    {  7, "Signed in",                 "SignedIn" },
    {  8, "Signed in to Live",         "SignedInLive" },
    {  9, "Signed in (needs password)","SignedInNeedPass" },
    {  6, "Signed out",                "SignedOut" },
    { 11, "Connection lost",           "ConnectionLost" },
    { 12, "Download complete",         "DownloadComplete" },
    { 13, "Music",                     "Music" },
    { 14, "Happy face",                "HappyFace" },
    { 15, "Sad face",                  "SadFace" },
    { 16, "Hammer",                    "Hammer" },
    { 18, "Memory unit removed",       "RemovedMU" },
    { 19, "Controller removed",        "RemovedGamepad" },
    { 28, "Hybrid disc",               "HybridDisc" },
    { 52, "Kicked",                    "Kicked" },
    { 68, "Trash can",                 "Trash" },
};
static const int s_IconCount = sizeof(s_Icons) / sizeof(s_Icons[0]);

int XNotifyCore_IconCount() { return s_IconCount; }

const XntIconInfo* XNotifyCore_IconAt(int index)
{
    return (index >= 0 && index < s_IconCount) ? &s_Icons[index] : &s_Icons[0];
}

int XNotifyCore_IconIndex(DWORD type)
{
    for (int i = 0; i < s_IconCount; ++i)
        if (s_Icons[i].type == type) return i;
    return -1;
}

const char* XNotifyCore_IconName(DWORD type)
{
    int i = XNotifyCore_IconIndex(type);
    return i >= 0 ? s_Icons[i].name : "Custom";
}

// ---------------------------------------------------------------------------
// UTF-8 <-> UTF-16
// ---------------------------------------------------------------------------
void XNotifyCore_Utf8ToWide(const char* in, wchar_t* out, int outChars)
{
    int o = 0;
    const unsigned char* p = (const unsigned char*)in;
    while (*p && o < outChars - 1)
    {
        unsigned int cp = '?';
        int extra = 0;
        if      (*p < 0x80)           { cp = *p; }
        else if ((*p & 0xE0) == 0xC0) { cp = *p & 0x1F; extra = 1; }
        else if ((*p & 0xF0) == 0xE0) { cp = *p & 0x0F; extra = 2; }
        else if ((*p & 0xF8) == 0xF0) { cp = *p & 0x07; extra = 3; }
        else                          { ++p; out[o++] = L'?'; continue; }
        ++p;
        for (int i = 0; i < extra; ++i)
        {
            if ((*p & 0xC0) != 0x80) { cp = '?'; extra = 0; break; }
            cp = (cp << 6) | (*p++ & 0x3F);
        }
        if (cp > 0xFFFF) cp = '?';        // outside the BMP: XNotify can't show it anyway
        out[o++] = (wchar_t)cp;
    }
    out[o] = 0;
}

void XNotifyCore_WideToUtf8(const wchar_t* in, char* out, int outBytes)
{
    int o = 0;
    for (const wchar_t* p = in; *p; ++p)
    {
        unsigned int cp = (unsigned int)*p;
        if (cp >= 0xD800 && cp <= 0xDFFF) cp = '?';   // lone surrogate
        if (cp < 0x20) continue;                         // no control characters / newlines
        int need = cp < 0x80 ? 1 : cp < 0x800 ? 2 : 3;
        if (o + need > outBytes - 1) break;              // never split a character
        if (need == 1) out[o++] = (char)cp;
        else if (need == 2) { out[o++] = (char)(0xC0 | (cp >> 6)); out[o++] = (char)(0x80 | (cp & 0x3F)); }
        else { out[o++] = (char)(0xE0 | (cp >> 12)); out[o++] = (char)(0x80 | ((cp >> 6) & 0x3F)); out[o++] = (char)(0x80 | (cp & 0x3F)); }
    }
    out[o] = 0;
}

// ---------------------------------------------------------------------------
// Storage: we mount our own drive letters so we don't depend on whatever the
// active dashboard (Aurora / FSD / stock) has or hasn't mapped.
// ---------------------------------------------------------------------------
struct StorageInfo { const char* drive; const char* device; };

static const StorageInfo s_Storage[] = {
    { "XNTHDD:", "\\Device\\Harddisk0\\Partition1" },  // internal HDD
    { "XNTUSB:", "\\Device\\Mass0" },                  // first USB drive
};
static const int s_StorageCount = sizeof(s_Storage) / sizeof(s_Storage[0]);

#define XNT_FOLDER   "XNotifyTweaks"
#define XNT_INI_NAME "XNotifyTweaks.ini"

static void InitAnsi(XNT_ANSI_STRING* s, char* buf)
{
    s->Buffer        = buf;
    s->Length        = (USHORT)strlen(buf);
    s->MaximumLength = (USHORT)(s->Length + 1);
}

void XNotifyCore_MountDrives(BOOL systemContext)
{
    for (int i = 0; i < s_StorageCount; ++i)
    {
        char linkBuf[64];
        char devBuf[64];
        _snprintf(linkBuf, sizeof(linkBuf), "%s%s",
                  systemContext ? "\\System??\\" : "\\??\\", s_Storage[i].drive);
        linkBuf[sizeof(linkBuf) - 1] = 0;
        strncpy(devBuf, s_Storage[i].device, sizeof(devBuf));
        devBuf[sizeof(devBuf) - 1] = 0;

        XNT_ANSI_STRING link, dev;
        InitAnsi(&link, linkBuf);
        InitAnsi(&dev, devBuf);
        ObDeleteSymbolicLink(&link);   // ignore failure (not mounted yet)
        ObCreateSymbolicLink(&link, &dev);
    }
}

static void BuildIniPath(int storage, char* out, size_t outSize)
{
    _snprintf(out, outSize, "%s\\" XNT_FOLDER "\\" XNT_INI_NAME, s_Storage[storage].drive);
    out[outSize - 1] = 0;
}

// ---------------------------------------------------------------------------
// Tiny INI reader/writer (key=value, ';' or '#' comments, [sections] ignored)
// ---------------------------------------------------------------------------
static char* Trim(char* s)
{
    while (*s == ' ' || *s == '\t') ++s;
    char* e = s + strlen(s);
    while (e > s && (e[-1] == ' ' || e[-1] == '\t' || e[-1] == '\r' || e[-1] == '\n')) --e;
    *e = 0;
    return s;
}

static BOOL ParseBool(const char* v)
{
    return (_stricmp(v, "1") == 0 || _stricmp(v, "true") == 0 ||
            _stricmp(v, "yes") == 0 || _stricmp(v, "on") == 0);
}

static void ApplyKey(XNotifyConfig* cfg, const char* key, const char* val)
{
    if      (_stricmp(key, "Enabled") == 0)           cfg->Enabled = ParseBool(val);
    else if (_stricmp(key, "ApplyOptions") == 0)      cfg->ApplyOptions = ParseBool(val);
    else if (_stricmp(key, "ShowNotifications") == 0) cfg->ShowNotifications = ParseBool(val);
    else if (_stricmp(key, "PlaySound") == 0)         cfg->PlaySound = ParseBool(val);
    else if (_stricmp(key, "ShowDuringVideo") == 0)   cfg->ShowDuringVideo = ParseBool(val);
    else if (_stricmp(key, "ShowDuringIPTV") == 0)    cfg->ShowDuringIPTV = ParseBool(val);
    else if (_stricmp(key, "Enforce") == 0)           cfg->Enforce = ParseBool(val);
    else if (_stricmp(key, "BootMessage") == 0)       cfg->BootMessage = ParseBool(val);
    else if (_stricmp(key, "Skin") == 0)              cfg->SkinEnabled = ParseBool(val);
    else if (_stricmp(key, "SkinColor") == 0)
    {
        for (DWORD i = 0; i < XNT_SKIN_COUNT; ++i)
        {
            if (_stricmp(val, g_SkinPresets[i].key) == 0) { cfg->SkinColor = i; return; }
        }
    }
    else if (_stricmp(key, "SkinLogo") == 0)
    {
        if (XNotifyCore_IsValidLogoName(val))
        {
            memset(cfg->SkinLogo, 0, sizeof(cfg->SkinLogo));
            strcpy(cfg->SkinLogo, val);
        }
    }
    else if (_stricmp(key, "BootMessageText") == 0)
    {
        // Round-trip through UTF-16 so a truncated value never ends mid-character.
        wchar_t wide[XNT_BOOT_TEXT_MAX];
        XNotifyCore_Utf8ToWide(val, wide, XNT_BOOT_TEXT_MAX);
        memset(cfg->BootText, 0, sizeof(cfg->BootText));
        XNotifyCore_WideToUtf8(wide, cfg->BootText, sizeof(cfg->BootText));
    }
    else if (_stricmp(key, "ToastIcon") == 0)
    {
        for (int i = 0; i < s_IconCount; ++i)
        {
            if (_stricmp(val, s_Icons[i].key) == 0) { cfg->ToastIcon = s_Icons[i].type; return; }
        }
        if (*val >= '0' && *val <= '9')
        {
            DWORD n = (DWORD)atoi(val);
            if (n <= 255) cfg->ToastIcon = n;   // hand-entered number: trusted as-is
        }
    }
    else if (_stricmp(key, "Position") == 0)
    {
        for (DWORD p = 0; p < XNT_POS_COUNT; ++p)
        {
            if (_stricmp(val, s_Positions[p].key) == 0) { cfg->Position = p; return; }
        }
    }
}

static BOOL ParseIni(XNotifyConfig* cfg, char* text)
{
    char* line = text;
    while (line && *line)
    {
        char* next = strchr(line, '\n');
        if (next) *next++ = 0;

        char* l = Trim(line);
        if (*l && *l != ';' && *l != '#' && *l != '[')
        {
            char* eq = strchr(l, '=');
            if (eq)
            {
                *eq = 0;
                ApplyKey(cfg, Trim(l), Trim(eq + 1));
            }
        }
        line = next;
    }
    return TRUE;
}

BOOL XNotifyConfig_Load(XNotifyConfig* cfg)
{
    XNotifyConfig_Defaults(cfg);

    for (int i = 0; i < s_StorageCount; ++i)
    {
        char path[MAX_PATH];
        BuildIniPath(i, path, sizeof(path));

        HANDLE f = CreateFileA(path, GENERIC_READ, FILE_SHARE_READ, NULL,
                               OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
        if (f == INVALID_HANDLE_VALUE)
            continue;

        char buf[4096];
        DWORD read = 0;
        BOOL ok = ReadFile(f, buf, sizeof(buf) - 1, &read, NULL);
        CloseHandle(f);
        if (!ok)
            continue;

        buf[read] = 0;
        return ParseIni(cfg, buf);
    }
    return FALSE;
}

BOOL XNotifyConfig_Save(const XNotifyConfig* cfg, char* outPath)
{
    char iconValue[32];
    int iconIndex = XNotifyCore_IconIndex(cfg->ToastIcon);
    if (iconIndex >= 0) _snprintf(iconValue, sizeof(iconValue), "%s", s_Icons[iconIndex].key);
    else                _snprintf(iconValue, sizeof(iconValue), "%u", (unsigned)cfg->ToastIcon);
    iconValue[sizeof(iconValue) - 1] = 0;

    char text[1536];
    int len = _snprintf(text, sizeof(text),
        "; XNotify Tweaks settings - edited by XNotifyTweaks Config, read by the DashLaunch plugin.\r\n"
        "; Position: TopLeft TopCenter TopRight CenterLeft Center CenterRight BottomLeft BottomCenter BottomRight\r\n"
        "[XNotifyTweaks]\r\n"
        "Enabled=%d\r\n"
        "Position=%s\r\n"
        "ApplyOptions=%d\r\n"
        "ShowNotifications=%d\r\n"
        "PlaySound=%d\r\n"
        "ShowDuringVideo=%d\r\n"
        "ShowDuringIPTV=%d\r\n"
        "Enforce=%d\r\n"
        "BootMessage=%d\r\n"
        "; ToastIcon: icon name (see README) or a number. Used for the boot message and test toasts.\r\n"
        "ToastIcon=%s\r\n"
        "BootMessageText=%s\r\n"
        "; Skin: custom XUI notification skin (1 = on, needs a reboot). Remove Notify.xex from launch.ini first.\r\n"
        "Skin=%d\r\n"
        "SkinColor=%s\r\n"
        "; SkinLogo: a PNG in the Logos folder next to this file\r\n"
        "SkinLogo=%s\r\n",
        cfg->Enabled ? 1 : 0,
        XNotifyConfig_PositionKey(cfg->Position),
        cfg->ApplyOptions ? 1 : 0,
        cfg->ShowNotifications ? 1 : 0,
        cfg->PlaySound ? 1 : 0,
        cfg->ShowDuringVideo ? 1 : 0,
        cfg->ShowDuringIPTV ? 1 : 0,
        cfg->Enforce ? 1 : 0,
        cfg->BootMessage ? 1 : 0,
        iconValue,
        cfg->BootText,
        cfg->SkinEnabled ? 1 : 0,
        g_SkinPresets[cfg->SkinColor < XNT_SKIN_COUNT ? cfg->SkinColor : 0].key,
        XNotifyCore_IsValidLogoName(cfg->SkinLogo) ? cfg->SkinLogo : XNT_DEFAULT_LOGO);
    if (len <= 0 || len >= (int)sizeof(text))
        return FALSE;

    // Prefer a location that already has a config, otherwise the first that works.
    int order[8];
    int count = 0;
    for (int i = 0; i < s_StorageCount; ++i)
    {
        char path[MAX_PATH];
        BuildIniPath(i, path, sizeof(path));
        if (GetFileAttributesA(path) != INVALID_FILE_ATTRIBUTES)
            order[count++] = i;
    }
    for (int i = 0; i < s_StorageCount; ++i)
    {
        BOOL seen = FALSE;
        for (int j = 0; j < count; ++j) if (order[j] == i) seen = TRUE;
        if (!seen) order[count++] = i;
    }

    for (int n = 0; n < count; ++n)
    {
        int i = order[n];
        char folder[MAX_PATH];
        _snprintf(folder, sizeof(folder), "%s\\" XNT_FOLDER, s_Storage[i].drive);
        folder[sizeof(folder) - 1] = 0;
        CreateDirectoryA(folder, NULL);   // fine if it already exists

        char path[MAX_PATH];
        BuildIniPath(i, path, sizeof(path));
        HANDLE f = CreateFileA(path, GENERIC_WRITE, 0, NULL, CREATE_ALWAYS,
                               FILE_ATTRIBUTE_NORMAL, NULL);
        if (f == INVALID_HANDLE_VALUE)
            continue;

        DWORD written = 0;
        BOOL ok = WriteFile(f, text, (DWORD)len, &written, NULL) && written == (DWORD)len;
        CloseHandle(f);
        if (ok)
        {
            if (outPath)
            {
                strncpy(outPath, path, MAX_PATH);
                outPath[MAX_PATH - 1] = 0;
            }
            return TRUE;
        }
    }
    return FALSE;
}

// ---------------------------------------------------------------------------
// Data folder and skin logos
// ---------------------------------------------------------------------------
int XNotifyCore_DataFolder(char* out, size_t outSize)
{
    int pick = -1;
    for (int i = 0; i < s_StorageCount && pick < 0; ++i)          // 1. the one with the INI
    {
        char ini[MAX_PATH];
        BuildIniPath(i, ini, sizeof(ini));
        if (GetFileAttributesA(ini) != INVALID_FILE_ATTRIBUTES)
            pick = i;
    }
    for (int i = 0; i < s_StorageCount && pick < 0; ++i)          // 2. existing or creatable folder
    {
        char folder[MAX_PATH];
        _snprintf(folder, sizeof(folder), "%s\\" XNT_FOLDER, s_Storage[i].drive);
        folder[sizeof(folder) - 1] = 0;
        CreateDirectoryA(folder, NULL);
        DWORD attr = GetFileAttributesA(folder);
        if (attr != INVALID_FILE_ATTRIBUTES && (attr & FILE_ATTRIBUTE_DIRECTORY))
            pick = i;
    }
    if (pick >= 0 && out)
    {
        _snprintf(out, outSize, "%s\\" XNT_FOLDER, s_Storage[pick].drive);
        out[outSize - 1] = 0;
    }
    return pick;
}

void XNotifyCore_MountLogoDrive()
{
    int storage = XNotifyCore_DataFolder(NULL, 0);
    if (storage < 0)
        storage = 0;
    char linkBuf[64] = "\\System??\\XNTLOGO:";
    char devBuf[96];
    _snprintf(devBuf, sizeof(devBuf), "%s\\" XNT_FOLDER, s_Storage[storage].device);
    devBuf[sizeof(devBuf) - 1] = 0;
    XNT_ANSI_STRING link, dev;
    InitAnsi(&link, linkBuf);
    InitAnsi(&dev, devBuf);
    ObDeleteSymbolicLink(&link);
    ObCreateSymbolicLink(&link, &dev);
}

BOOL XNotifyCore_IsValidLogoName(const char* name)
{
    size_t len = name ? strlen(name) : 0;
    if (len < 5 || len >= XNT_LOGO_NAME_MAX || _stricmp(name + len - 4, ".png") != 0)
        return FALSE;
    for (const char* p = name; *p; ++p)
    {
        if (*p < 0x20 || *p > 0x7E || strchr("\\/:*?\"<>|", *p))
            return FALSE;
    }
    return name[0] != '.';
}

BOOL XNotifyCore_CopyFile(const char* src, const char* dst)
{
    HANDLE in = CreateFileA(src, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
    if (in == INVALID_HANDLE_VALUE)
        return FALSE;
    const DWORD MAX_BYTES = 1024 * 1024;
    BYTE* buf = (BYTE*)malloc(MAX_BYTES);
    DWORD read = 0;
    BOOL ok = buf && ReadFile(in, buf, MAX_BYTES, &read, NULL) && read > 0 && read < MAX_BYTES;
    CloseHandle(in);
    if (ok)
    {
        HANDLE out = CreateFileA(dst, GENERIC_WRITE, 0, NULL, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
        ok = out != INVALID_HANDLE_VALUE;
        if (ok)
        {
            DWORD written = 0;
            ok = WriteFile(out, buf, read, &written, NULL) && written == read;
            CloseHandle(out);
        }
    }
    free(buf);
    return ok;
}

BOOL XNotifyCore_ApplyLogo(const XNotifyConfig* cfg)
{
    char folder[MAX_PATH];
    if (XNotifyCore_DataFolder(folder, sizeof(folder)) < 0)
        return FALSE;

    char src[MAX_PATH], dst[MAX_PATH];
    const char* name = XNotifyCore_IsValidLogoName(cfg->SkinLogo) ? cfg->SkinLogo : XNT_DEFAULT_LOGO;
    _snprintf(src, sizeof(src), "%s\\Logos\\%s", folder, name);
    src[sizeof(src) - 1] = 0;
    if (GetFileAttributesA(src) == INVALID_FILE_ATTRIBUTES)
    {
        _snprintf(src, sizeof(src), "%s\\Logos\\" XNT_DEFAULT_LOGO, folder);   // picked file was deleted
        src[sizeof(src) - 1] = 0;
    }
    _snprintf(dst, sizeof(dst), "%s\\logo.png", folder);
    dst[sizeof(dst) - 1] = 0;
    return XNotifyCore_CopyFile(src, dst);
}

// ---------------------------------------------------------------------------
// Applying
// ---------------------------------------------------------------------------
void XNotifyCore_ApplyOnTitleThread(const XNotifyConfig* cfg)
{
    if (g_Xam.PositionUI)
        g_Xam.PositionUI(XNotifyConfig_PositionFlags(cfg->Position));

    if (cfg->ApplyOptions && g_Xam.SetOptions)
        g_Xam.SetOptions(cfg->ShowNotifications, cfg->ShowDuringVideo,
                         cfg->PlaySound, cfg->ShowDuringIPTV);
}

void XNotifyCore_Toast(DWORD icon, const wchar_t* text)
{
    if (g_Xam.QueueUI)
        g_Xam.QueueUI(icon, XUSER_INDEX_ANY, XNOTIFY_SYSTEM, (PWCHAR)text, NULL);
}
