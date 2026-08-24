#!/usr/bin/env python3
"""Temporarily disable Telegram Desktop's Windows capture-affinity calls.

This is a process-memory workaround for Telegram Desktop 7.1.x. It does not
modify Telegram.exe or Telegram account data. Restarting Telegram undoes it.

Run once from a 64-bit Python process while Telegram Desktop is running:

    python main.py

Or keep watching for Telegram restarts:

    python main.py --watch

The script intentionally does NOT interfere with SetWindowsHookExW. Telegram's
screenshot-protection implementation uses SetWindowDisplayAffinity, while
blocking Windows hooks could break unrelated input handling.
"""

from __future__ import annotations

import ctypes
import argparse
import os
from pathlib import Path
import struct
import sys
import time
from ctypes import wintypes


if sys.platform != "win32":
    raise SystemExit("This workaround only runs on Windows.")

if struct.calcsize("P") != 8:
    raise SystemExit("Use 64-bit Python; the installed Telegram Desktop is 64-bit.")


kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
user32 = ctypes.WinDLL("user32", use_last_error=True)
ntdll = ctypes.WinDLL("ntdll", use_last_error=True)

TH32CS_SNAPPROCESS = 0x00000002
TH32CS_SNAPMODULE = 0x00000008
TH32CS_SNAPMODULE32 = 0x00000010
PROCESS_CREATE_THREAD = 0x0002
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_OPERATION = 0x0008
PROCESS_VM_READ = 0x0010
PROCESS_VM_WRITE = 0x0020
PROCESS_SYNCHRONIZE = 0x00100000
MEM_COMMIT = 0x1000
MEM_RESERVE = 0x2000
MEM_RELEASE = 0x8000
PAGE_READWRITE = 0x04
PAGE_EXECUTE_READWRITE = 0x40
WAIT_OBJECT_0 = 0x00000000
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
NOOP_FUNCTION = b"\xB8\x01\x00\x00\x00\xC3"  # mov eax, 1; ret
ERROR_ALREADY_EXISTS = 183
PERSISTENT_MUTEX_NAME = "Local\\TelegramScreenshot.Persistent"


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.c_size_t),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", wintypes.LONG),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", wintypes.WCHAR * 260),
    ]


class PROCESS_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("Reserved1", wintypes.LPVOID),
        ("PebBaseAddress", wintypes.LPVOID),
        ("Reserved2", wintypes.LPVOID * 2),
        ("UniqueProcessId", ctypes.c_size_t),
        ("Reserved3", wintypes.LPVOID),
    ]


kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
kernel32.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
kernel32.Process32FirstW.restype = wintypes.BOOL
kernel32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
kernel32.Process32NextW.restype = wintypes.BOOL
kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.QueryFullProcessImageNameW.argtypes = [
    wintypes.HANDLE,
    wintypes.DWORD,
    wintypes.LPWSTR,
    ctypes.POINTER(wintypes.DWORD),
]
kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
kernel32.ReadProcessMemory.argtypes = [
    wintypes.HANDLE,
    wintypes.LPCVOID,
    wintypes.LPVOID,
    ctypes.c_size_t,
    ctypes.POINTER(ctypes.c_size_t),
]
kernel32.ReadProcessMemory.restype = wintypes.BOOL
kernel32.WriteProcessMemory.argtypes = [
    wintypes.HANDLE,
    wintypes.LPVOID,
    wintypes.LPCVOID,
    ctypes.c_size_t,
    ctypes.POINTER(ctypes.c_size_t),
]
kernel32.WriteProcessMemory.restype = wintypes.BOOL
kernel32.VirtualAllocEx.argtypes = [
    wintypes.HANDLE,
    wintypes.LPVOID,
    ctypes.c_size_t,
    wintypes.DWORD,
    wintypes.DWORD,
]
kernel32.VirtualAllocEx.restype = wintypes.LPVOID
kernel32.VirtualFreeEx.argtypes = [
    wintypes.HANDLE,
    wintypes.LPVOID,
    ctypes.c_size_t,
    wintypes.DWORD,
]
kernel32.VirtualFreeEx.restype = wintypes.BOOL
kernel32.VirtualProtectEx.argtypes = [
    wintypes.HANDLE,
    wintypes.LPVOID,
    ctypes.c_size_t,
    wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD),
]
kernel32.VirtualProtectEx.restype = wintypes.BOOL
kernel32.CreateRemoteThread.argtypes = [
    wintypes.HANDLE,
    wintypes.LPVOID,
    ctypes.c_size_t,
    wintypes.LPVOID,
    wintypes.LPVOID,
    wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD),
]
kernel32.CreateRemoteThread.restype = wintypes.HANDLE
kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
kernel32.WaitForSingleObject.restype = wintypes.DWORD
kernel32.FlushInstructionCache.argtypes = [
    wintypes.HANDLE,
    wintypes.LPCVOID,
    ctypes.c_size_t,
]
kernel32.FlushInstructionCache.restype = wintypes.BOOL
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL
kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
kernel32.CreateMutexW.restype = wintypes.HANDLE
ntdll.NtQueryInformationProcess.argtypes = [
    wintypes.HANDLE,
    wintypes.ULONG,
    wintypes.LPVOID,
    wintypes.ULONG,
    ctypes.POINTER(wintypes.ULONG),
]
ntdll.NtQueryInformationProcess.restype = wintypes.LONG

WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
user32.EnumWindows.restype = wintypes.BOOL
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD


def winerror(message: str) -> OSError:
    return ctypes.WinError(ctypes.get_last_error(), message)


def telegram_pids() -> list[int]:
    snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snapshot == INVALID_HANDLE_VALUE:
        raise winerror("CreateToolhelp32Snapshot(processes) failed")
    try:
        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(entry)
        found: list[int] = []
        ok = kernel32.Process32FirstW(snapshot, ctypes.byref(entry))
        while ok:
            if entry.szExeFile.casefold() == "telegram.exe":
                found.append(int(entry.th32ProcessID))
            ok = kernel32.Process32NextW(snapshot, ctypes.byref(entry))
        return found
    finally:
        kernel32.CloseHandle(snapshot)


def main_module(process: wintypes.HANDLE, pid: int) -> tuple[int, str]:
    info = PROCESS_BASIC_INFORMATION()
    returned = wintypes.ULONG()
    status = ntdll.NtQueryInformationProcess(
        process,
        0,  # ProcessBasicInformation
        ctypes.byref(info),
        ctypes.sizeof(info),
        ctypes.byref(returned),
    )
    if status < 0 or not info.PebBaseAddress:
        raise RuntimeError(
            f"NtQueryInformationProcess failed for PID {pid} (NTSTATUS 0x{status & 0xFFFFFFFF:08X})"
        )

    # PEB.ImageBaseAddress is at offset 0x10 in a 64-bit process.
    image_base = struct.unpack(
        "<Q", read_memory(process, int(info.PebBaseAddress) + 0x10, 8)
    )[0]
    if not image_base:
        raise RuntimeError(f"PID {pid} has an invalid image base")

    capacity = wintypes.DWORD(32768)
    path_buffer = ctypes.create_unicode_buffer(capacity.value)
    if not kernel32.QueryFullProcessImageNameW(
        process, 0, path_buffer, ctypes.byref(capacity)
    ):
        raise winerror(f"Could not query the executable path for PID {pid}")
    return image_base, path_buffer.value


def read_memory(process: wintypes.HANDLE, address: int, size: int) -> bytes:
    buffer = ctypes.create_string_buffer(size)
    read = ctypes.c_size_t()
    if not kernel32.ReadProcessMemory(
        process, ctypes.c_void_p(address), buffer, size, ctypes.byref(read)
    ) or read.value != size:
        raise winerror(f"ReadProcessMemory failed at 0x{address:X}")
    return buffer.raw


def write_memory(process: wintypes.HANDLE, address: int, data: bytes) -> None:
    buffer = ctypes.create_string_buffer(data)
    written = ctypes.c_size_t()
    if not kernel32.WriteProcessMemory(
        process, ctypes.c_void_p(address), buffer, len(data), ctypes.byref(written)
    ) or written.value != len(data):
        raise winerror(f"WriteProcessMemory failed at 0x{address:X}")


def read_c_string(process: wintypes.HANDLE, address: int, limit: int = 512) -> str:
    result = bytearray()
    while len(result) < limit:
        block = read_memory(process, address + len(result), min(64, limit - len(result)))
        nul = block.find(b"\0")
        if nul >= 0:
            result.extend(block[:nul])
            return result.decode("ascii", errors="strict")
        result.extend(block)
    raise RuntimeError(f"Unterminated string at 0x{address:X}")


def find_iat_entry(
    process: wintypes.HANDLE, image_base: int, function: str
) -> tuple[int, int]:
    dos = read_memory(process, image_base, 0x1000)
    if dos[:2] != b"MZ":
        raise RuntimeError("Telegram main module does not have an MZ header")
    pe_offset = struct.unpack_from("<I", dos, 0x3C)[0]
    headers = read_memory(process, image_base + pe_offset, 0x200)
    if headers[:4] != b"PE\0\0":
        raise RuntimeError("Telegram main module does not have a PE header")

    optional_offset = 24
    magic = struct.unpack_from("<H", headers, optional_offset)[0]
    if magic != 0x20B:
        raise RuntimeError("Telegram is not a 64-bit PE image")
    data_directories = optional_offset + 0x70
    def search_thunks(names_rva: int, iat_rva: int) -> tuple[int, int] | None:
        for index in range(65536):
            thunk = struct.unpack(
                "<Q", read_memory(process, image_base + names_rva + index * 8, 8)
            )[0]
            if thunk == 0:
                break
            if thunk & (1 << 63):
                continue
            imported_name = read_c_string(process, image_base + thunk + 2)
            if imported_name == function:
                iat_address = image_base + iat_rva + index * 8
                original_address = struct.unpack(
                    "<Q", read_memory(process, iat_address, 8)
                )[0]
                return iat_address, original_address
        return None

    import_rva = struct.unpack_from("<I", headers, data_directories + 8)[0]
    if import_rva:
        descriptor_address = image_base + import_rva
        for descriptor_index in range(4096):
            descriptor = read_memory(
                process, descriptor_address + descriptor_index * 20, 20
            )
            original_thunk, _, _, name_rva, first_thunk = struct.unpack(
                "<IIIII", descriptor
            )
            if not any((original_thunk, name_rva, first_thunk)):
                break
            if original_thunk:
                found = search_thunks(original_thunk, first_thunk)
                if found:
                    return found

    # Telegram uses delay-loaded Win32 imports in some builds. The delay-load
    # directory is data-directory entry 13 and has 32-byte descriptors.
    delay_rva = struct.unpack_from("<I", headers, data_directories + 13 * 8)[0]
    if delay_rva:
        descriptor_address = image_base + delay_rva
        for descriptor_index in range(4096):
            descriptor = read_memory(
                process, descriptor_address + descriptor_index * 32, 32
            )
            fields = struct.unpack("<IIIIIIII", descriptor)
            attributes, name, _, iat, names, _, _, _ = fields
            if not any(fields):
                break
            if not (attributes & 1):
                raise RuntimeError("Unsupported VA-based delay-import descriptor")
            found = search_thunks(names, iat)
            if found:
                return found

    raise RuntimeError(f"Could not find imported function {function}")


def telegram_windows(pid: int) -> list[int]:
    handles: list[int] = []

    @WNDENUMPROC
    def callback(hwnd: int, _lparam: int) -> bool:
        owner = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value == pid:
            handles.append(int(hwnd))
        return True

    if not user32.EnumWindows(callback, 0):
        raise winerror("EnumWindows failed")
    return handles


def run_remote_code(process: wintypes.HANDLE, code: bytes) -> None:
    remote = kernel32.VirtualAllocEx(
        process, None, len(code), MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE
    )
    if not remote:
        raise winerror("VirtualAllocEx failed")
    try:
        remote_address = int(remote)
        write_memory(process, remote_address, code)
        kernel32.FlushInstructionCache(process, remote, len(code))
        thread_id = wintypes.DWORD()
        thread = kernel32.CreateRemoteThread(
            process, None, 0, remote, None, 0, ctypes.byref(thread_id)
        )
        if not thread:
            raise winerror("CreateRemoteThread failed")
        try:
            if kernel32.WaitForSingleObject(thread, 5000) != WAIT_OBJECT_0:
                raise RuntimeError("Timed out clearing a Telegram window's affinity")
        finally:
            kernel32.CloseHandle(thread)
    finally:
        kernel32.VirtualFreeEx(process, remote, 0, MEM_RELEASE)


def clear_existing_affinity(
    process: wintypes.HANDLE, pid: int, original_function: int
) -> int:
    count = 0
    for hwnd in telegram_windows(pid):
        # Windows x64 ABI:
        #   sub rsp, 0x28
        #   mov rcx, hwnd              ; first argument
        #   xor edx, edx               ; WDA_NONE
        #   mov rax, SetWindowDisplayAffinity
        #   call rax
        #   add rsp, 0x28
        #   ret
        code = (
            b"\x48\x83\xEC\x28"
            + b"\x48\xB9"
            + struct.pack("<Q", hwnd)
            + b"\x31\xD2"
            + b"\x48\xB8"
            + struct.pack("<Q", original_function)
            + b"\xFF\xD0\x48\x83\xC4\x28\xC3"
        )
        run_remote_code(process, code)
        count += 1
    return count


def install_noop(process: wintypes.HANDLE, iat_address: int) -> int:
    # BOOL WINAPI replacement(...): return TRUE
    code = NOOP_FUNCTION
    remote = kernel32.VirtualAllocEx(
        process, None, len(code), MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE
    )
    if not remote:
        raise winerror("VirtualAllocEx failed for the no-op function")
    remote_address = int(remote)
    try:
        write_memory(process, remote_address, code)
        kernel32.FlushInstructionCache(process, remote, len(code))

        old_protection = wintypes.DWORD()
        if not kernel32.VirtualProtectEx(
            process,
            ctypes.c_void_p(iat_address),
            8,
            PAGE_READWRITE,
            ctypes.byref(old_protection),
        ):
            raise winerror("VirtualProtectEx failed for Telegram's import table")
        try:
            write_memory(process, iat_address, struct.pack("<Q", remote_address))
        finally:
            ignored = wintypes.DWORD()
            kernel32.VirtualProtectEx(
                process,
                ctypes.c_void_p(iat_address),
                8,
                old_protection.value,
                ctypes.byref(ignored),
            )
        # The allocation intentionally remains until Telegram exits because its
        # import-table entry now points to this six-byte function.
        return remote_address
    except Exception:
        kernel32.VirtualFreeEx(process, remote, 0, MEM_RELEASE)
        raise


def patch_telegram(pid: int) -> None:
    access = (
        PROCESS_CREATE_THREAD
        | PROCESS_QUERY_INFORMATION
        | PROCESS_VM_OPERATION
        | PROCESS_VM_READ
        | PROCESS_VM_WRITE
        | PROCESS_SYNCHRONIZE
    )
    process = kernel32.OpenProcess(access, False, pid)
    if not process:
        raise winerror(
            f"Could not open Telegram PID {pid}. Try an Administrator terminal"
        )
    try:
        image_base, path = main_module(process, pid)
        if os.path.basename(path).casefold() != "telegram.exe":
            raise RuntimeError(f"PID {pid} is not Telegram.exe: {path}")

        iat_address, original_function = find_iat_entry(
            process, image_base, "SetWindowDisplayAffinity"
        )
        if read_memory(process, original_function, len(NOOP_FUNCTION)) == NOOP_FUNCTION:
            print(f"Telegram PID {pid} is already patched")
            return
        cleared = clear_existing_affinity(process, pid, original_function)
        replacement = install_noop(process, iat_address)
        print(f"Patched Telegram PID {pid}")
        print(f"  executable: {path}")
        print(f"  cleared {cleared} existing top-level window(s)")
        print(f"  SetWindowDisplayAffinity -> no-op at 0x{replacement:X}")
    finally:
        kernel32.CloseHandle(process)


def run_once() -> int:
    pids = telegram_pids()
    if not pids:
        print("Telegram.exe is not running. Start Telegram, then run this script again.")
        return 1

    failures = 0
    for pid in pids:
        try:
            patch_telegram(pid)
        except Exception as error:
            failures += 1
            print(f"Failed to patch Telegram PID {pid}: {error}", file=sys.stderr)

    if not failures:
        print("Done. Win+Shift+S should now include Telegram.")
        print("Restarting Telegram restores its original screenshot protection.")
    return 1 if failures else 0


def run_persistent(interval: float, pid_file: Path | None = None) -> int:
    ctypes.set_last_error(0)
    mutex = kernel32.CreateMutexW(None, False, PERSISTENT_MUTEX_NAME)
    if not mutex:
        raise winerror("Could not create the persistent-mode mutex")
    if ctypes.get_last_error() == ERROR_ALREADY_EXISTS:
        kernel32.CloseHandle(mutex)
        print("Persistent mode is already running.")
        return 0

    if pid_file:
        pid_file.parent.mkdir(parents=True, exist_ok=True)
        pid_file.write_text(str(os.getpid()), encoding="ascii")

    patched: set[int] = set()
    waiting_announced = False
    print("Persistent mode is active. Press Ctrl+C to stop.")
    print(f"Checking for Telegram every {interval:g} second(s).")

    try:
        while True:
            current = set(telegram_pids())
            patched.intersection_update(current)

            if not current:
                if not waiting_announced:
                    print("Waiting for Telegram.exe...")
                    waiting_announced = True
            else:
                waiting_announced = False

            for pid in sorted(current - patched):
                try:
                    patch_telegram(pid)
                except Exception as error:
                    print(
                        f"Failed to patch Telegram PID {pid}: {error}; retrying...",
                        file=sys.stderr,
                    )
                else:
                    patched.add(pid)

            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nPersistent mode stopped.")
        return 0
    finally:
        if pid_file:
            try:
                if pid_file.read_text(encoding="ascii").strip() == str(os.getpid()):
                    pid_file.unlink(missing_ok=True)
            except (OSError, ValueError):
                pass
        kernel32.CloseHandle(mutex)


def configure_output(log_file: Path | None) -> None:
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        stream = log_file.open("a", encoding="utf-8", buffering=1)
        sys.stdout = stream
        sys.stderr = stream
    elif sys.stdout is None or sys.stderr is None:
        stream = open(os.devnull, "w", encoding="utf-8")
        sys.stdout = stream
        sys.stderr = stream


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="TelegramScreenshot",
        description=(
            "Temporarily disable Telegram Desktop's Windows screenshot "
            "capture-affinity call."
        ),
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="keep running and patch Telegram again whenever it restarts",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=2.0,
        metavar="SECONDS",
        help="polling interval for --watch (default: 2)",
    )
    parser.add_argument(
        "--pid-file",
        type=Path,
        metavar="PATH",
        help="write the persistent watcher's process ID to this file",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        metavar="PATH",
        help="append stdout and stderr to this file (useful with pythonw.exe)",
    )
    args = parser.parse_args(argv)
    if args.interval < 0.25:
        parser.error("--interval must be at least 0.25 seconds")
    if (args.pid_file or args.log_file) and not args.watch:
        parser.error("--pid-file and --log-file require --watch")
    configure_output(args.log_file)
    return run_persistent(args.interval, args.pid_file) if args.watch else run_once()


if __name__ == "__main__":
    raise SystemExit(main())
