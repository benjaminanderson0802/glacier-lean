# Install Glacier without an internet connection

You will need two computers or two trips to the internet: one computer that can download files, and the computer where you want to use Glacier. The computers should use the same kind of system (Windows, Linux, or Mac) and the same kind of processor. Python 3.12 must be installed on the computer where you build the pack and on the computer where you install it.

## 1. Build the pack on a computer with internet

Open PowerShell on Windows, or Terminal on Linux or Mac. Go to the Glacier project folder. Copy and paste the command for the computer where you plan to install Glacier.

Windows 64-bit:

```powershell
python setup/offline/build_pack.py --platform win_amd64 --python-version 3.12 --output Glacier-offline
```

Linux 64-bit:

```text
python3 setup/offline/build_pack.py --python-version 3.12 --output Glacier-offline
```

The Linux command automatically downloads wheels for several compatible Linux versions. For a Mac with an Intel processor, use `--platform macosx_11_0_x86_64`. For a Mac with an Apple processor, use `--platform macosx_11_0_arm64`.

When the command finishes, copy the entire Glacier-offline folder to a USB drive. The folder contains the installer, the getting-started guide, and the pinned Python packages. Keep the MANIFEST.json file with the folder; Glacier uses it to check that files were copied safely.

## 2. Install on Windows

1. Copy Glacier-offline from the USB drive to your Desktop.
2. Press **Win+R**, type `powershell`, and press **Enter**.
3. Copy and paste this line, then press **Enter**:

```powershell
cd $env:USERPROFILE\Desktop\Glacier-offline
```

4. Copy and paste this line, then press **Enter**:

```powershell
py -3.12 install_pack.py --destination $env:USERPROFILE\Glacier
```

Leave the PowerShell window open until it says setup is complete. If Windows says Python is missing, ask someone with internet access to bring you the Python 3.12 installer on the USB drive.

## 3. Install on Linux

1. Copy Glacier-offline from the USB drive into your home folder.
2. Open **Terminal** from your applications menu.
3. Copy and paste this line, then press **Enter**:

```text
cd ~/Glacier-offline
```

4. Copy and paste this line, then press **Enter**:

```text
python3 install_pack.py --destination ~/Glacier
```

Leave the Terminal window open until it says setup is complete. If it says Python 3.12 is missing, ask someone with internet access to bring a Python 3.12 installer for your Linux version on the USB drive.

## Optional local AI model

To add model information to the pack, include `--ollama-model qwen3:0.6b` in the build command. This records the exact command `ollama pull qwen3:0.6b` and the model size if Ollama can report it. The model files are not copied into the pack. Model files can be several gigabytes and need an internet connection to download unless they are moved separately.

If the installer says that pack files have changed, copy the whole folder again from the USB drive and retry. It checks the file list and every SHA-256 fingerprint before creating the Python environment. After installing the packages, it checks Python, Git, Ollama, and Codex and tells you which ones are ready or missing.
