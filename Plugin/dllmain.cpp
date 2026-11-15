// XNotifyTweaks.xex - DashLaunch system plugin.
//
// Loads at boot, then on every title launch (Aurora, FSD, the stock dash, or
// any game) it re-reads XNotifyTweaks.ini and applies the notification
// position / options to that title. Settings are edited with the companion
// "XNotify Tweaks Config" app, or by hand in the INI.
//
// Why a plugin: XNotifyPositionUI only affects the title that is running when
// it's called, and every title launch resets it. A system DLL survives title
// changes, so it can re-apply on each one regardless of which dashboard you use.

#include "../Shared/XNotifyCore.h"
#include "Skin.h"

namespace
{
const DWORD POLL_MS          = 250;
const DWORD FIRST_APPLY_MS   = 1500;   // after the title reaches "running"
const DWORD SECOND_APPLY_MS  = 8000;   // catches titles that set their own position during init
const DWORD ENFORCE_EVERY_MS = 5000;

volatile LONG g_Stop   = 0;
PVOID         g_Worker = NULL;         // PKTHREAD (EX_CREATE_FLAG_RETURN_KTHREAD)
HANDLE        g_Module = NULL;         // this plugin, for the skin's section:// paths

// Context handed to the short-lived title thread. Only one is in flight at a
// time because ApplyNow waits for it.
XNotifyConfig g_ApplyCfg;
BOOL          g_ApplyToast = FALSE;

DWORD WINAPI TitleApplyThread(LPVOID)
{
    // XNotify* must run on a title thread on real hardware, even from a sysdll.
    if (KeGetCurrentProcessType() != XNT_PROC_USER)
        return 0;
    if (g_Xam.LoaderGetState() != XNT_LOADER_STATE_TITLE_RUNNING)
        return 0;

    XNotifyCore_ApplyOnTitleThread(&g_ApplyCfg);
    if (g_ApplyToast)
    {
        wchar_t text[XNT_BOOT_TEXT_MAX];
        XNotifyCore_Utf8ToWide(g_ApplyCfg.BootText[0] ? g_ApplyCfg.BootText : XNT_DEFAULT_BOOT_TEXT,
                               text, XNT_BOOT_TEXT_MAX);
        XNotifyCore_Toast(g_ApplyCfg.ToastIcon, text);
    }
    return 0;
}

void ApplyNow(const XNotifyConfig* cfg, BOOL toast)
{
    g_ApplyCfg   = *cfg;
    g_ApplyToast = toast;

    PVOID thread = NULL;
    DWORD status = ExCreateThread((PHANDLE)&thread, 0, NULL, NULL, TitleApplyThread, NULL,
                                  XNT_EX_CREATE_FLAG_TITLE_EXEC | XNT_EX_CREATE_FLAG_RETURN_KTHREAD);
    if (!XNT_SUCCESS(status) || thread == NULL)
        return;

    // Wait so the plugin can't unload (and g_ApplyCfg can't change) mid-call.
    LARGE_INTEGER timeout;
    timeout.QuadPart = -5000LL * 10000LL;   // 5 s, relative
    KeWaitForSingleObject(thread, 0 /*Executive*/, 0 /*KernelMode*/, FALSE, &timeout);
    ObDereferenceObject(thread);
}

DWORD WINAPI Worker(LPVOID)
{
    XNotifyCore_MountDrives(TRUE);

    // The custom skin is decided once per boot: hooking and unhooking xam while
    // the HUD is busy isn't worth the risk. Colour changes still apply live.
    char appliedLogo[XNT_LOGO_NAME_MAX] = "";

    // Wait a second first (as your Notify.xex did) so xam, the drives and other
    // plugins have finished starting before we read the INI or touch the HUD.
    Sleep(1000);
    if (!g_Stop)
    {
        XNotifyConfig boot;
        XNotifyConfig_Load(&boot);
        Skin_SetColor(boot.SkinColor);
        if (boot.SkinEnabled)
        {
            // Logo first: the skin's visual loads file://XNTLOGO:/logo.png.
            XNotifyCore_MountLogoDrive();
            Skin_WriteDefaultLogo(g_Module);
            XNotifyCore_ApplyLogo(&boot);
            strncpy(appliedLogo, boot.SkinLogo, sizeof(appliedLogo) - 1);
            Skin_Install(g_Module);
        }
    }

    DWORD lastTitle      = 0xFFFFFFFF;
    BOOL  wasRunning     = FALSE;
    DWORD runningMs      = 0;
    DWORD lastApplyMs    = 0;
    int   passes         = 0;
    BOOL  bootToastDue   = TRUE;
    BOOL  enforce        = FALSE;   // cached from the last INI read

    while (!g_Stop)
    {
        const DWORD title   = g_Xam.GetCurrentTitleId();
        const BOOL  running = g_Xam.LoaderGetState() == XNT_LOADER_STATE_TITLE_RUNNING;

        // New title (or the same one relaunched): start the schedule over.
        if (title != lastTitle || (running && !wasRunning))
        {
            lastTitle = title;
            runningMs = 0;
            lastApplyMs = 0;
            passes = 0;
        }
        wasRunning = running;

        if (running && title != XNT_APP_TITLE_ID)
        {
            runningMs += POLL_MS;

            BOOL due = FALSE;
            if (passes == 0)      due = runningMs >= FIRST_APPLY_MS;
            else if (passes == 1) due = runningMs >= SECOND_APPLY_MS;
            else                  due = enforce && (runningMs - lastApplyMs >= ENFORCE_EVERY_MS);

            if (due)
            {
                // Re-read every time so edits made in the app (or over FTP) are picked up.
                XNotifyConfig cfg;
                XNotifyConfig_Load(&cfg);
                enforce = cfg.Enforce;
                Skin_SetColor(cfg.SkinColor);
                if (XNT_GetSkinState() == XNT_SKIN_STATE_ACTIVE && strcmp(cfg.SkinLogo, appliedLogo) != 0)
                {
                    // Picked in the app (which also copies it) or edited by hand.
                    XNotifyCore_ApplyLogo(&cfg);
                    strncpy(appliedLogo, cfg.SkinLogo, sizeof(appliedLogo) - 1);
                }

                if (cfg.Enabled)
                    ApplyNow(&cfg, bootToastDue && cfg.BootMessage);

                bootToastDue = FALSE;
                lastApplyMs = runningMs;
                if (passes < 2) ++passes;
            }
        }

        Sleep(POLL_MS);
    }
    return 0;
}
} // namespace

BOOL APIENTRY DllMain(HANDLE hModule, DWORD reason, LPVOID reserved)
{
    UNREFERENCED_PARAMETER(reserved);

    if (reason == DLL_PROCESS_ATTACH)
    {
        g_Module = hModule;
        // Resolve now, while we already hold the loader lock, so the worker never needs it.
        if (!XNotifyCore_Resolve())
            return TRUE;   // stay loaded but inert rather than upsetting DashLaunch

        g_Stop = 0;
        PVOID thread = NULL;
        DWORD status = ExCreateThread((PHANDLE)&thread, 0, NULL, NULL, Worker, NULL,
                                      XNT_EX_CREATE_FLAG_SYSTEM | XNT_EX_CREATE_FLAG_RETURN_KTHREAD);
        g_Worker = XNT_SUCCESS(status) ? thread : NULL;
    }
    else if (reason == DLL_PROCESS_DETACH)
    {
        Skin_Uninstall();   // first: xam must never jump into an unloaded plugin
        if (g_Worker)
        {
            InterlockedExchange(&g_Stop, 1);
            LARGE_INTEGER timeout;
            timeout.QuadPart = -10000LL * 10000LL;   // 10 s
            KeWaitForSingleObject(g_Worker, 0, 0, FALSE, &timeout);
            ObDereferenceObject(g_Worker);
            g_Worker = NULL;
        }
    }
    return TRUE;
}
