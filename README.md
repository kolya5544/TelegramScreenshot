# TelegramScreenshot

Ultimate screenshot freedom for Telegram Desktop on Windows.

A focused, dependency-free freedom-oriented Python utility that temporarily disables Telegram
Desktop's capture-affinity call, allowing Snipping Tool, `Win + Shift + S`,
screen sharing, and compatible capture software to see the Telegram window.

![Platform](https://img.shields.io/badge/platform-Windows-0078D4?logo=windows)
![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)
![Architecture](https://img.shields.io/badge/architecture-x86--64-informational)
![Dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen)
![Persistence](https://img.shields.io/badge/changes-memory--only-orange)
![License](https://img.shields.io/badge/license-MIT-blue)

---

## ✨ Why TelegramScreenshot

Telegram Desktop 7.1.x introduced screenshot protection on Windows. In affected
setups, invoking Windows Snipping Tool can make the entire Telegram window
disappear from the capture surface.

TelegramScreenshot fixes the problem:

- ⚡ patches an already-running Telegram process in seconds;
- 📸 restores `Win + Shift + S` and Snipping Tool capture;
- 🔄 can run invisibly at Windows sign-in and reapply after Telegram restarts;
- 🧼 makes no changes to `Telegram.exe`, `tdata`, chats, or account settings;
- 📦 uses only the Python standard library;

---

## ⚡ Quick Start

### Run once

Start Telegram, then double-click:

```text
run-once.bat
```

Approve the Windows elevation prompt. The patch remains active until Telegram
exits.

### Invisible startup mode

Double-click:

```text
add-startup-persistent.bat
```

The installer creates a per-user Windows startup entry and immediately launches
the watcher through `pythonw.exe`. No console window remains visible.
TelegramScreenshot will start every time you sign in and patch each new
`Telegram.exe` process.

To stop the watcher and remove its startup entry completely, double-click:

```text
remove-startup-persistent.bat
```

### Why hidden Telegram windows are left untouched

Telegram owns hidden helper windows (`Qt6120ScreenChangeObserverWindow` and
`Qt6120ThemeChangeObserverWindow`, both 1440x759 at cascade positions) that are
never visible. TelegramScreenshot never calls `SetWindowDisplayAffinity` on
them. That call makes the desktop compositor create a redirection surface even
for a window that was never shown, and the orphaned surface is then presented
as a solid white rectangle above the desktop wallpaper and below all other
windows, click-through and impossible to dismiss, until Telegram exits. Only
windows that already report a non-zero capture affinity are cleared; an
unpatched Telegram reports `WDA_NONE` on every window, so the usual case
touches nothing at all.

---

## 🧱 Requirements

| Requirement | Details |
|---|---|
| Operating system | Windows 10 or Windows 11 |
| Python | 64-bit Python 3.10 or newer |
| Telegram | 64-bit Telegram Desktop with the affected capture-affinity implementation |
| Privileges | One-shot mode requests Administrator access; startup mode runs as the signed-in user |
| Packages | None |

> TelegramScreenshot currently targets 64-bit processes.

### Compatibility scope

TelegramScreenshot is version-independent within a specific implementation
boundary:

> It supports 64-bit Telegram Desktop builds on x64 Windows when
> `Telegram.exe` imports `SetWindowDisplayAffinity` through a normal or
> delay-loaded import table.

The utility discovers process IDs, ASLR module bases, Telegram window handles,
the import table, and the target IAT entry dynamically. It contains no
Telegram-version-specific address, installation path, PID, window handle,
instruction signature, or IAT offset.

The implementation does contain stable Windows x64 details: PE32+ structure
offsets, the Windows x64 calling convention, a six-byte x64 return stub, and
the x64 PEB location used to obtain the image base. These are platform and
architecture assumptions—not offsets taken from a particular Telegram build.

A future Telegram release may require an update if it moves the call into a
different module or process, resolves it dynamically, changes the process
name, or stops importing the API. ARM64 and 32-bit builds are not currently
supported.

---

## 🚀 Launch Modes

| Mode | Launcher | Python command | Behavior |
|---|---|---|---|
| One shot | `run-once.bat` | `python main.py` | Patches every running Telegram process, then exits |
| Install at startup | `add-startup-persistent.bat` | `pythonw main.py --watch` | Runs invisibly at sign-in and patches new Telegram processes |
| Remove from startup | `remove-startup-persistent.bat` | — | Stops the verified watcher and removes its generated state |
| Custom polling | — | `python main.py --watch --interval 5` | Uses a custom interval in seconds |

Command-line help is available with:

```powershell
python .\main.py --help
```

---

## 🔬 How It Works

Telegram's Windows implementation calls the documented Win32
[`SetWindowDisplayAffinity`](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setwindowdisplayaffinity)
API with `WDA_EXCLUDEFROMCAPTURE`. Windows then omits the protected top-level
window from supported capture paths.

TelegramScreenshot performs four narrowly scoped actions:

1. Finds processes whose executable name is exactly `Telegram.exe`.
2. Locates Telegram's normal or delay-loaded import-table entry for
   `SetWindowDisplayAffinity`.
3. Calls the original function inside Telegram with `WDA_NONE` to clear the
   affinity of existing Telegram windows.
4. Redirects that one import entry to a six-byte function that returns success
   without reapplying protection.

The replacement lives only in Telegram's private process memory. No Windows
system DLL and no executable on disk is patched.

---

## 🛡️ Safety and Privacy

**While patched, Telegram's screenshot
protection is disabled for every chat in that Telegram process, including
restricted or non-copyable chats.** Use the tool only on systems and accounts
you are authorized to operate.

Because the technique writes to another process's memory and creates a short
remote thread, endpoint security software may flag or block it. Review the
source before running it and follow your organization's security policy.

---

## 🧰 Troubleshooting

### `Telegram.exe is not running`

Start Telegram Desktop and run `run-once.bat` again, or use
`add-startup-persistent.bat` before starting Telegram.

### `Access is denied` or `Could not open Telegram`

Use one of the batch launchers and accept its elevation prompt. If Telegram is
running under a different Windows account or security boundary, access may
still be denied.

### `Use 64-bit Python`

Install a 64-bit Python build and ensure `python.exe` or the `py` launcher is on
`PATH`.

### Antivirus or EDR blocks the script

Process-memory patching resembles techniques used by debugging and security
tools, so detection is possible. Do not disable organizational security
controls without authorization. Restarting Telegram safely restores its normal
state if the patch was only partially applied.

The installer now treats registry or process-launch errors as fatal and reports
the real Windows error instead of displaying a false success message. A
`Requested registry access is not allowed` message can also come from running
inside a restricted sandbox; it is not, by itself, a Defender malware
detection.

### Telegram updated and the import cannot be found

TelegramScreenshot deliberately validates the PE import structure instead of
using fixed offsets. A future Telegram build may nevertheless change how the
API is resolved. Check the source before adapting the tool to a new build.

Older Telegram versions that never implemented this display-affinity path may
also report that the import cannot be found; those versions ordinarily do not
need this workaround.

---

## 📁 Project Structure

```text
TelegramScreenshot/
├── .gitignore              # Ignores generated runtime state
├── LICENSE                 # MIT license
├── main.py                 # Core utility and command-line module
├── run-once.bat            # Elevated one-shot launcher
├── add-startup-persistent.bat
│                             # Install and start the invisible watcher
├── remove-startup-persistent.bat
│                             # Stop and fully remove startup mode
└── README.md               # Project documentation
```

---

## ⚠️ Disclaimer

This project is a temporary interoperability workaround, not a security bypass
guarantee. Use it only with software, systems, conversations, and content you
are authorized to capture. You are responsible for complying with workplace
policies, privacy obligations, applicable law, and Telegram's terms.

---

## 📄 License

TelegramScreenshot is released under the [MIT License](LICENSE).

Copyright © 2026 `kolya5544`.
