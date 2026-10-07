# Glacier offline setup

This guide is for a computer with little or no internet access. Build the pack on a
connected computer first. Use Python 3.12 on both computers. Choose the pack for
the computer that will install it: Windows 64-bit, Linux 64-bit, or macOS.

## On the connected computer

Python 3.12 is the default because the pinned packages have Linux wheels for it.
Use the same Python version on the connected and offline computers. Open a
terminal in the Glacier folder and run one line for the target computer:

Windows 64-bit (PowerShell):

```powershell
py -3.12 setup/offline/build_pack.py --platform win_amd64 --output glacier-offline
```

Linux 64-bit:

```sh
python3 setup/offline/build_pack.py --platform manylinux_2_28_x86_64 --platform manylinux_2_27_x86_64 --platform manylinux_2_17_x86_64 --platform manylinux2014_x86_64 --output glacier-offline
```

macOS Apple silicon:

```sh
python3 setup/offline/build_pack.py --platform macosx_11_0_arm64 --output glacier-offline
```

macOS Intel:

```sh
python3 setup/offline/build_pack.py --platform macosx_11_0_x86_64 --output glacier-offline
```

The pack contains Glacier's source, its Python packages, this guide, and the guide
pages. Keep the `MANIFEST.sha256` file with the pack. The installer prints its
value before installing. If sharing the value separately, open `MANIFEST.sha256`
in a text editor and send its contents to the person carrying the pack.

To record an Ollama model and its estimated size, add `--ollama-model qwen3:0.6b`
to the command. This records the exact `ollama pull` command; it does not include
the model files. Add `--include-model` only if Ollama and the requested model are
installed on the connected computer. That option copies all installed Ollama model
blobs, which may be very large.

## Copy the pack to Windows

Install Python 3.12 first, then copy the complete `glacier-offline` folder to
`C:\Glacier-offline` using a USB drive. Do not use the Desktop or a OneDrive folder.

Press Win+R, type `powershell`, and press Enter. Copy and paste these lines one
at a time. They assume the folder is at `C:\Glacier-offline`:

```powershell
cd C:\Glacier-offline
py -3.12 install_pack.py --destination C:\Glacier
```

If someone sent you the value from `MANIFEST.sha256` separately, add it to the
command like this:

```powershell
py -3.12 install_pack.py --destination C:\Glacier --manifest-sha256 PASTE_SHA256_HERE
```

## Copy the pack to Linux

Install Python 3.12 first, then copy the complete `glacier-offline` folder to your
home folder or a USB drive. In a terminal, paste:

```sh
cd ~/glacier-offline
python3.12 install_pack.py --destination ~/Glacier
```

To compare the value in `MANIFEST.sha256` with one shared by the pack builder,
add it like this:

```sh
python3.12 install_pack.py --destination ~/Glacier --manifest-sha256 PASTE_SHA256_HERE
```

## If a check fails

The installer prints the manifest's SHA-256 before it starts. Compare that value
with `MANIFEST.sha256` or the one shared by the person who built the pack.
If it differs, copying may have damaged or changed the pack; copy it again from the
original USB drive or ask for a fresh copy.

If a file check reports that a file has changed, or the SHA-256 differs from a
trusted value, the pack may have been changed after it was built. Do not install it;
ask the person who built it to check the original pack and share its SHA-256 again.

The pack must match the operating system and Python 3.12. Linux packs use the
compatible `manylinux_2_28`, `manylinux_2_27`, `manylinux_2_17`, and `manylinux2014`
tags so document reading works offline. If the installer says it needs a different
system, use the pack built for your computer. Optional tools such as Ollama, Codex,
Node.js, and Git are checked and reported; they can be installed later when needed.
