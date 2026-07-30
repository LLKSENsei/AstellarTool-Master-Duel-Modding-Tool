[繁體中文](README.md) | [English](README_en.md)

[![License](https://img.shields.io/github/license/LLKSENsei/AstellarTool-Master-Duel-Modding-Tool?color=2CC985)](LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)]()
[![Platform](https://img.shields.io/badge/platform-Windows-lightgrey)]()
[![Price](https://img.shields.io/badge/Price-100%25%20Free-brightgreen)]()

An automated tool specifically developed for *Yu-Gi-Oh! Master Duel*, featuring asset parsing, texture replacement, Over-Frame Art rendering, and virtual mod management. Built with Python 3, PySide6, and UnityPy, this project is dedicated to streamlining the tedious workflow and solving the underlying file structure issues commonly encountered during game modding.

# MD AstellarTool

---

## Detailed Tutorial

As this tool is feature-rich (containing 14 independent pipelines), we provide a dedicated tutorial document with clear visual and textual instructions:

**[Click here to view the complete tutorial (TUTORIAL_en.md)](TUTORIAL_en.md)**

[VIDEO](https://youtu.be/DJUt6wblYLw)

The tutorial covers:
* How to complete a full card art replacement from scratch (from 0 to 1)
* Techniques for processing Pendulum and Over-Frame card arts
* When and how to use Virtual Mounting and the Mod Streaming Fixer

---

## Project Vision & Disclaimer

This tool is a completely free and open-source software, developed primarily for technical exchange, programming research, and personal hobby sharing. **Any form of commercial resale, paid bundling, or disguised charging is strictly prohibited.** If you paid for this tool or a "modpack" containing it, you have been scammed. Please request a refund immediately and report the seller to the platform.

This project is open-sourced under the MIT License. It only provides file parsing and modification functionalities and **does not contain any original game files**. All Unity assets, game images, and related data extracted by this tool are the copyrighted property of Konami Digital Entertainment.

---

## Core Technologies & Algorithms

To ensure stability and automation, this tool implements the following technologies and algorithms for its underlying parsing and system resource management:

### 1. Binary XOR Obfuscation Decryption & Auto-Cracking Engine
In-game text databases (like `card_name.bytes`) utilize custom XOR obfuscation encryption. This tool implements the corresponding decryption algorithm: `(i + key + 0x23D) * key ^ (i % 7)`.
To solve the issue of decryption keys changing after game updates, the system features a built-in auto-cracking mechanism (`auto_crack_key`). When the default key fails, the program iterates from 0 to 1023, using zlib decompression success rates to validate the correct key. This gives the tool self-healing capabilities, eliminating the need for frequent version updates just because the key changed.

### 2. IL2CPP Metadata Reverse Mapping & CRC32 Validation
Accessory files in the game (such as sleeves, fields, icons) usually lack plaintext IDs and are named by Hashes. To resolve their actual names, the tool reads the game's `global-metadata.dat` and uses regex to extract `ID([0-9]{6,7})`. It then calculates the CRC32 hash of these strings (e.g., `IDS_ITEM.ID{id}`). Finally, cross-referencing these hashes with a dictionary parsed from `ids_item.bytes` via msgpack accurately restores the localized names of all non-card objects.

### 3. Card Property Signatures & Pendulum Dual-Check
When parsing `card_prop.bytes`, the program performs bitwise operations in 8-byte blocks. By reading specific bytes, it identifies `0x020D` as Spell cards and `0x024E` as Trap cards. For Monster cards, it extracts a 6-bit mask (`b2 & 0x3F`) to determine subtypes (e.g., Fusion, Synchro, Xyz).
Due to the complex binary markers of Pendulum cards, the tool implements a dual-check mechanism. It simultaneously verifies if "the card effect text contains Pendulum keywords" OR "the binary signature matches". Using this OR logic completely resolves the issue of Pendulum cards being misclassified.

### 4. Unity Bundle Memory-Safe Direct Injection
In the "Mod Streaming Fixer" feature, to migrate images from outdated mods to the new version of game files, the tool bypasses the traditional full unpack and repack process (which typically causes massive memory consumption).
Instead, it directly reads the target `Texture2D` object, forces the new original file's `m_StreamData` attributes (path, offset, size) to zero to truncate external streams, and seamlessly writes the raw bytes of the old mod directly into `image_data`. This inline injection technique effectively prevents OOM (Out of Memory) crashes and ensures high file compatibility.

### 5. Over-Frame Registry Binary Reconstruction
The game determines which cards should use Over-Frame rendering via the `of_card_asset` file. The tool reads this file as a `TextAsset` and unpacks its internal binary data using a `uint16` (`<HH`) structure into an array of `[Trigger_ID, Target_ID]`.
When a user inputs a new ID, the program performs conflict checks (filtering out official placeholders and custom overlaps), then repacks the new array back into the Bundle. A `.pristine` backup is simultaneously created to prevent structural corruption caused by multiple write cycles.

### 6. Dynamic PSD Multi-Layer Compositing & Caching Engine
When handling Over-Frame art, the tool integrates the `psd-tools` library to dynamically read PSD templates, precisely extracting 5 independent layers: PeriFrame, NameBox, ArtFrame, EffFrame, and EffBox.
To tackle the performance bottleneck of batch-processing hundreds of images, the tool employs a `_psd_cache` memory caching engine. Users can customize the opacity (0-100%) of these layers via the UI, and the program synthesizes them in real-time using PIL's Alpha channel compositing. A Fallback mechanism is also in place, automatically downgrading to static PNG templates if dependencies are missing.

### 7. System-Level Transaction Rollback & Vanilla Backup Mechanism
The Virtual Mod Manager utilizes Windows Symbolic Links (Symlink) to mount mods, achieving zero disk space usage.
Before modifying any original game file, the program renames it to `.vanilla_backup` for protection. The mounting process incorporates an atomic transaction rollback mechanism: if any permission denial or file-in-use error occurs during the loop, the system immediately aborts and restores all changed files based on the `state_log`, guaranteeing absolute safety for the base game.

### 8. OS-Level Memory Protection & Dynamic Path Pruning
During bulk scans of the game directory, to prevent low-end PCs from freezing, the program calls the Windows `GlobalMemoryStatusEx` API to monitor physical RAM. When the memory load exceeds 85%, threads automatically enter sleep mode until resources are freed.
Additionally, a `prune_walk_dirs` algorithm is implemented for `os.walk`. By dynamically filtering out output and temporary directories before traversal, it effectively blocks infinite recursion and unnecessary disk I/O.

### 9. AST Extraction & Dynamic i18n Mapping
To reduce the maintenance cost of multiple languages, the tool abandons manual translation dictionaries. Instead, it utilizes Python's built-in `ast` module to parse the main script into an Abstract Syntax Tree (AST), traversing all `ast.Call` and `ast.keyword` nodes to precisely extract strings wrapped in `_("...")` as well as UI placeholders.
Post-extraction, the program automatically compares the results with the existing `zh-tw.json` (and other languages), preserving translated content while incrementally appending missing strings. This achieves highly automated i18n maintenance.

### 10. EXE Compilation Virtualization (MockModule)
When packaging the tool into a standalone executable using PyInstaller, native audio dependencies (like `fmod`) often cause startup crashes due to missing DLLs.
To ensure smooth compilation in non-audio environments, a `MockModule` inheriting from `types.ModuleType` is defined at the top of the script. By intercepting `__getattr__`, it virtualizes `fmod_toolkit` and `pyfmodex` within `sys.modules`. This approach massively improves code portability and compilation success rates.

### 11. Custom Linear Drag-Scroll Filter
To fix the rigid drag-scroll feel and un-disableable physical inertia of Qt's built-in `QListWidget`, a `LinearDragScrollFilter` is implemented.
By intercepting mouse move events, the program introduces a decimal pixel scroll accumulator. Sub-pixel movements (less than 1 pixel) are stored, and only when a full integer is reached does it trigger a `QScrollBar` step. This elevates the UI drag experience to the smooth, stop-on-a-dime standard of modern web browsers.

---

## Modules & Tabs Overview

The interface is divided into 14 independent tabs, each handling a specific segment of the modding pipeline:

* **0. Guide**: Provides an overview of the workflow, concept explanations, and a summary of each tab's functions.
* **1. Scan & Index**: Uses multiprocessing (`ProcessPoolExecutor`) to scan the `0000` directory. After decrypting text files, it generates a lookup table (CSV) mapping File Hashes to Card IDs, Names, Effects, and Properties, serving as the data foundation.
* **2. Find Files**: Reads the CSV table, supporting text and Regex searches. Select your target cards, and the system automatically copies the corresponding Hash files from the game directory to the workspace.
* **3. Extract Data**: Loads the files via `UnityPy`, traversing the object tree for `Texture2D` assets. Auto-filters low-res thumbnails, exports clean original art, and creates original file backups.
* **4. Replace Art**: Repackages external modified images back into the Bundle. The program scales the image using the Lanczos algorithm to match the original `Texture2D` dimensions, performs a binary replacement, and saves.
* **5. Package Mod**: Auto-detects directory type (standard `0000` or `StreamingAssets`), reconstructs the accurate folder structure, and supports one-click ZIP compression for easy sharing/installation.
* **6. Smart Pipeline**: An automated factory scheduler chaining "Find, Extract, Post-Process, Replace, Package." Powered by a callback sequence, it allows for a 1-click execution of the entire workflow.
* **7. Pendulum & Over-Frame Post-Processing**: Designed for advanced card beautification. Fills bottom transparent pixels for Pendulums to prevent distortion; supports 11:16 ratio cropping and PSD 5-layer dynamic synthesis for Over-Frame rendering, complete with a real-time `QImage` preview panel.
* **8. Quick Single Mod**: Bypasses full project creation. Input a Card ID and image path, and the program directly extracts, modifies, and overwrites the game file. Features special routing for modifying raw files like `data.unity3d` (e.g., lobby backgrounds).
* **9. Over-Frame Registry**: Reads and writes the `of_card_asset` registry. Provides existing list parsing, external registry merging, and conflict checks. Adding an ID here applies borderless/over-frame rendering logic to that card in-game.
* **10. Graphical Browser**: A gallery viewer for fields, icons, sleeves, and accessories. Converts disk I/O into memory lookups for rapid grid thumbnails. Supports sandbox filtering and 1-click transfers to extraction or quick modding pipelines.
* **11. Mod Streaming Fixer**: A rescue tool for mods broken by game updates. Analyzes the new game files and losslessly injects texture streaming data from old mods directly, saving massive amounts of remaking time.
* **12. Virtual Mod Manager**: Mounts mods via system Symlinks with zero disk space cost. Drag-and-drop to adjust load priority across dual lists. Features strict permission checks and safe rollback mechanics, ideal for quickly testing multiple mods.
* **13. Settings & Appearance**: Centralized management for environment variables and UI. Supports a custom 5-dimensional palette (dynamically applied QSS), custom backgrounds with 9-slice anchors, multiprocess thread limit adjustments, and exporting AST-parsed translation templates.

---

### Directory Structure
* `MD_AstellarTool.py`: Main application entry point and UI logic.
* `requirements.txt`: Python dependency list.
* `MD_Tool_Essential/`: Static resources directory.
  * `Languages/`: Stores AST-exported and custom multi-language JSON files.
  * `CardFrame/`: Stores PSD templates and fallback PNGs used for Over-Frame rendering.

---

## Special Thanks

The creation and refinement of this open-source project wouldn't be possible without the selfless sharing and research of the community. Special thanks to the following contributors:

* **TranLinhVy**: Huge thanks to NexusMods creator [TranLinhVy](https://www.nexusmods.com/profile/TranLinhVy) for their excellent work and technical inspiration, which immensely helped the development of this project.
* **Master Duel Datamining & Modding Community**: Respect to all researchers who have contributed to asset unpacking, database analysis, and tool development for *Yu-Gi-Oh! Master Duel*. Your dedication to exploring the underlying tech made MD AstellarTool possible.

### Developer Info
* Author Pixiv: [LonelyMaJo](https://www.pixiv.net/users/126514098)
