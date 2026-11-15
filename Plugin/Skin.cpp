// Skin.cpp - custom XUI notification skin.
//
// This is your Notify.xex's technique, minus the string obfuscation:
//   1. XuiLoadVisualFromBinary registers the toast visual(s) from a section
//      embedded in this xex (Plugin/XNotifySkins.xzp, section "584E5453").
//   2. XamBuildXamResourceLocator is patched to jump here. When the HUD asks
//      for "notify.xur" we answer with our scene; everything else is passed to
//      XamBuildResourceLocator exactly as xam would.
//
// What's new: tools/make_skins.py builds one scene + visual per colour preset,
// each visual with its own name, so all of them are loaded up front and the
// colour can change between notifications without a reboot.
//
// Ordinals (xkelib xamExpEnum.h and Xenia's xam table agree):
//   795 XamBuildResourceLocator, 799 XamBuildXamResourceLocator,
//   871 XuiVisualSetBasePath, 2058 XuiLoadVisualFromBinary

#include "Skin.h"
#include "../Shared/SkinPresets.h"
#include <stdio.h>

// Your original called XuiVisualSetBasePath(L"skin://") after loading. That
// makes relative paths in the visual (its "icon.png" logo) resolve against the
// console's own skin instead of our package, which is one reason the logo never
// showed. Leave this at 0 to use the logo and sound packed in XNotifySkins.xzp.
#define XNT_SKIN_USE_SYSTEM_BASE_PATH 0

// Writing Logos\Default.png reads the skin package with XGetModuleSection (xbox.h).
// If your SDK doesn't have it, set this to 0 and copy skins\src\icon.png to
// Hdd:\XNotifyTweaks\Logos\Default.png yourself.
#define XNT_HAVE_XGETMODULESECTION 1

namespace
{
typedef HRESULT (*PFN_XuiLoadVisualFromBinary)(LPCWSTR resourcePath, LPCWSTR prefix);
typedef VOID    (*PFN_XuiVisualSetBasePath)(LPCWSTR basePath, LPCWSTR prefix);
typedef VOID    (*PFN_XamBuildResourceLocator)(HANDLE module, LPCWSTR moduleName, LPCWSTR resource,
                                               LPWSTR locator, DWORD cchLocator);

HANDLE                      g_SkinModule  = NULL;
HMODULE                     g_XamModule   = NULL;
PFN_XamBuildResourceLocator g_BuildLocator = NULL;
DWORD*                      g_PatchedFn   = NULL;
DWORD                       g_SavedCode[4];

volatile LONG g_SkinColor   = 0;
volatile LONG g_SkinPreview = -1;
volatile LONG g_SkinState   = XNT_SKIN_STATE_OFF;

FARPROC XamOrdinal(DWORD ordinal)
{
    return g_XamModule ? GetProcAddress(g_XamModule, (LPCSTR)ordinal) : NULL;
}

// lis r11,hi / addi r11,r11,lo / mtctr r11 / bctr  (same as your PatchInJump)
void WriteJump(DWORD* at, DWORD destination)
{
    at[0] = 0x3D600000 + ((destination >> 16) & 0xFFFF);
    if (destination & 0x8000)
        at[0] += 1;
    at[1] = 0x396B0000 + (destination & 0xFFFF);
    at[2] = 0x7D6903A6;
    at[3] = 0x4E800420;
}

VOID SkinLocatorHook(LPCWSTR resource, LPWSTR locator, DWORD cchLocator)
{
    if (resource && locator && cchLocator > 1 && _wcsicmp(resource, L"notify.xur") == 0)
    {
        LONG index = g_SkinPreview >= 0 ? g_SkinPreview : g_SkinColor;
        if (index < 0 || index >= XNT_SKIN_COUNT)
            index = 0;
        _snwprintf(locator, cchLocator, L"section://%X," XNT_SKIN_SECTION L"#scene%d.xur",
                   (DWORD)g_SkinModule, (int)index);
        locator[cchLocator - 1] = 0;
        return;
    }
    // Everything else: what the original XamBuildXamResourceLocator does.
    g_BuildLocator((HANDLE)g_XamModule, L"xam", resource, locator, cchLocator);
}
} // namespace

BOOL Skin_Install(HANDLE pluginModule)
{
    if (g_SkinState == XNT_SKIN_STATE_ACTIVE)
        return TRUE;

    g_SkinModule = pluginModule;
    g_XamModule  = GetModuleHandle("xam.xex");

    PFN_XuiLoadVisualFromBinary loadVisual = (PFN_XuiLoadVisualFromBinary)XamOrdinal(2058);
    g_BuildLocator = (PFN_XamBuildResourceLocator)XamOrdinal(795);
    DWORD* target  = (DWORD*)XamOrdinal(799);
    if (!g_SkinModule || !loadVisual || !g_BuildLocator || !target)
    {
        g_SkinState = XNT_SKIN_STATE_FAILED;
        return FALSE;
    }

    // Register every colour's visual. If any fails, don't hook at all: a scene
    // pointing at a missing visual would give you blank notifications.
    for (int i = 0; i < XNT_SKIN_COUNT; ++i)
    {
        WCHAR path[128];
        _snwprintf(path, 128, L"section://%X," XNT_SKIN_SECTION L"#visual%d.xur", (DWORD)g_SkinModule, i);
        path[127] = 0;
        if (FAILED(loadVisual(path, NULL)))
        {
            g_SkinState = XNT_SKIN_STATE_FAILED;
            return FALSE;
        }
    }

#if XNT_SKIN_USE_SYSTEM_BASE_PATH
    PFN_XuiVisualSetBasePath setBasePath = (PFN_XuiVisualSetBasePath)XamOrdinal(871);
    if (setBasePath)
        setBasePath(L"skin://", NULL);
#endif

    memcpy(g_SavedCode, target, sizeof(g_SavedCode));
    g_PatchedFn = target;
    WriteJump(target, (DWORD)SkinLocatorHook);

    g_SkinState = XNT_SKIN_STATE_ACTIVE;
    return TRUE;
}

static DWORD ReadBE32(const BYTE* p) { return (DWORD)p[0] << 24 | (DWORD)p[1] << 16 | (DWORD)p[2] << 8 | p[3]; }

BOOL Skin_WriteDefaultLogo(HANDLE pluginModule)
{
    char folder[MAX_PATH], logos[MAX_PATH], path[MAX_PATH];
    if (XNotifyCore_DataFolder(folder, sizeof(folder)) < 0)
        return FALSE;
    _snprintf(logos, sizeof(logos), "%s\\Logos", folder);
    logos[sizeof(logos) - 1] = 0;
    CreateDirectoryA(logos, NULL);
    _snprintf(path, sizeof(path), "%s\\" XNT_DEFAULT_LOGO, logos);
    path[sizeof(path) - 1] = 0;
    if (GetFileAttributesA(path) != INVALID_FILE_ATTRIBUTES)
        return TRUE;                                   // already there (or replaced by you)

#if XNT_HAVE_XGETMODULESECTION
    PVOID data = NULL;
    ULONG size = 0;
    if (!XGetModuleSection(pluginModule, "584E5453", &data, &size) || !data || size < 22)
        return FALSE;

    // XUIZ: "XUIZ", ver, total, 0, table size, u16 count, then size/offset/len/name entries;
    // file data starts right after the table.
    const BYTE* xzp = (const BYTE*)data;
    if (memcmp(xzp, "XUIZ", 4) != 0)
        return FALSE;
    const DWORD count = (DWORD)xzp[20] << 8 | xzp[21];
    const BYTE* p = xzp + 22;
    const BYTE* end = xzp + size;
    const BYTE* found = NULL;
    DWORD foundSize = 0, foundOff = 0;
    for (DWORD i = 0; i < count && p + 9 <= end; ++i)
    {
        DWORD fileSize = ReadBE32(p), fileOff = ReadBE32(p + 4), nameLen = p[8];
        if (p + 9 + nameLen > end)
            return FALSE;
        if (nameLen == 8 && memcmp(p + 9, "icon.png", 8) == 0)
        {
            found = p;
            foundSize = fileSize;
            foundOff = fileOff;
        }
        p += 9 + nameLen;
    }
    const BYTE* fileData = p + foundOff;               // p is now the end of the table
    if (!found || fileData + foundSize > end || foundSize == 0)
        return FALSE;

    HANDLE f = CreateFileA(path, GENERIC_WRITE, 0, NULL, CREATE_NEW, FILE_ATTRIBUTE_NORMAL, NULL);
    if (f == INVALID_HANDLE_VALUE)
        return FALSE;
    DWORD written = 0;
    BOOL ok = WriteFile(f, fileData, foundSize, &written, NULL) && written == foundSize;
    CloseHandle(f);
    return ok;
#else
    UNREFERENCED_PARAMETER(pluginModule);
    return FALSE;
#endif
}

void Skin_Uninstall()
{
    // If the plugin is unloaded while xam still jumps into it, the console
    // crashes on the next notification, so put the original code back first.
    if (g_PatchedFn)
    {
        memcpy(g_PatchedFn, g_SavedCode, sizeof(g_SavedCode));
        g_PatchedFn = NULL;
    }
    g_SkinState = XNT_SKIN_STATE_OFF;
}

void Skin_SetColor(DWORD index)
{
    InterlockedExchange(&g_SkinColor, index < XNT_SKIN_COUNT ? (LONG)index : 0);
}

extern "C" VOID XNT_SetSkinPreview(LONG index)
{
    InterlockedExchange(&g_SkinPreview, (index >= 0 && index < XNT_SKIN_COUNT) ? index : -1);
}

extern "C" LONG XNT_GetSkinState()
{
    return g_SkinState;
}
