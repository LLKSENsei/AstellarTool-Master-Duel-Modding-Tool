# MD AstellarTool

[![License](https://img.shields.io/github/license/LLKSENsei/AstellarTool-Master-Duel-Modding-Tool?color=2CC985)](LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)]()
[![Platform](https://img.shields.io/badge/platform-Windows-lightgrey)]()
[![Price](https://img.shields.io/badge/Price-100%25%20Free-brightgreen)]()

This project is an automated tool specifically developed for *Yu-Gi-Oh! Master Duel* to handle asset parsing, database reverse engineering, binary texture injection, Over-Frame Art rendering, and virtual mod management.

Built upon low-level libraries such as Python 3, PySide6, UnityPy, and NumPy, this tool aims to streamline tedious asset customization pipelines, resolve low-level file encryption, reconstruct Spine animation coordinates, and manage OS-level physical files.

---

## Detailed Tutorial

Due to the rich feature set of this tool (including 14 independent pipelines), a separate tutorial document is provided for detailed step-by-step guidance with images:

**[Click here to view the complete tutorial (TUTORIAL.md)](TUTORIAL.md)**

[Video](https://youtu.be/DJUt6wblYLw)

Tutorial contents include:
* How to complete a full card art replacement from scratch (0 to 1)
* Handling techniques for Pendulum and Over-Frame card arts
* When to use the virtual mount and stream fixer

---

## Project Disclaimer & Licensing Terms

This program is completely free and open-source, intended solely for technical exchange and personal research. Commercial resale, bundled sales, or disguised fees of any kind are strictly prohibited. If you paid to acquire this program, you have been scammed; please report the seller/platform immediately and request a refund.

This project is open-sourced under the MIT License. The tool provides only the algorithm implementations for file parsing and modification, and does not contain any official game assets. Copyrights and intellectual property rights for all Unity assets, game images, and related data extracted or packaged by this tool belong to the original official publisher (Konami Digital Entertainment).

---

## System Architecture & Multitasking Computing Scheduling System

When processing tasks such as scanning, decrypting, and writing tens of thousands of encrypted asset bundles, this tool utilizes a highly concurrent multitasking architecture to balance system load, reduce I/O latency, and establish stable protective boundaries across various hardware configurations.

### 1. QThreadPool & TaskWorker Synchronization Bridge
To prevent heavy file I/O or image processing operations from blocking the Qt GUI main Event Loop, the tool implements a `TaskWorker` component inherited from `QRunnable`. Through custom `WorkerSignals`, background threads send progress counts and intermediate states to the main window in a thread-safe manner, enabling real-time UI rendering updates without UI freezing.

### 2. Multiprocessing (ProcessPoolExecutor) Compute Release
For CPU-intensive tasks (such as decrypting binary databases, batch atlas cropping, and pixel background removal), the tool utilizes `concurrent.futures.ProcessPoolExecutor` for parallel multiprocessing. This design bypasses Python's Global Interpreter Lock (GIL), allowing multi-core processors (such as AMD R9 9950X and other high-thread processors) to fully utilize all logical cores. Upon startup, each child process copies the main process's language dictionary via `_init_worker`, ensuring semantic alignment of error messages across isolated process memories.

### 3. OS-Level Memory Protection (Memory Radar)
When decoding large batches of animation frames, C++ underlying libraries may leave large amounts of un-garbage-collected (GC) buffers in memory. To prevent physical memory depletion from causing the OS to force-terminate processes, the tool calls the Windows kernel API `GlobalMemoryStatusEx` via `ctypes` to monitor system memory load in real time. When physical memory usage hits an 85% threshold, concurrent threads temporarily pause and enter an adaptive sleep state until memory is released, ensuring system stability.

### 4. os.walk Dynamic Pruning Algorithm
When scanning large game directories, to prevent invalid paths and custom output directories (such as temporary or backup folders) from causing `os.walk` to fall into infinite recursion or redundant disk I/O, the tool implements `prune_walk_dirs` dynamic pruning. Before entering each directory level, the algorithm pre-calculates physical subpath relationships (`is_subpath`) between output paths and current paths, modifying the `dirs` list directly to truncate recursive paths.

---

## Binary Decryption & Database Reverse Engineering

Key text and card properties in game (such as `card_name.bytes`, `card_prop.bytes`) undergo binary obfuscation and compression. By analyzing low-level binary distributions, this project implements a high-efficiency decoding and alignment engine.

### 5. Custom XOR Obfuscation Decryption Formula
Internal binary encryption uses XOR obfuscation based on bit shifts and dynamic factors. The decryption formula is as follows:

```
decrypted[i] = raw_bytes[i] ^ (((i + key + 0x23D) * key ^ (i % 7)) & 0xFF)
```

Where `i` is the absolute byte stream index and `key` is the obfuscation key.

### 6. Heuristic Key Auto-Bruteforce Engine (Bruteforce Crack)
When game updates cause default keys (such as default value 61) to fail, the tool implements the `auto_crack_key` engine. The algorithm iterates over a finite key space of 0 to 1023, passing decrypted byte streams to the `zlib` decompression module. Normal decrypted files decompress to reveal clear pointers and characteristic structures like `YDLZ`, whereas invalid keys trigger decompression exceptions. Using this heuristic validation indicator, self-healing capability is achieved without static offset positioning.

### 7. Il2Cpp Metadata Lightweight Binary Regex Scan
Chinese descriptions for non-card items (fields, sleeves, avatars) are not stored in regular card databases. To unlock these hash-named accessories without heavy full Il2Cpp decompilation, light binary regex scanning is implemented. By directly searching `global-metadata.dat` for string streams matching the `ID([0-9]{6,7})` format, all potential plaintext IDs are extracted.

### 8. CRC32 Hash Verification & Alignment
For scanned item IDs, the algorithm encodes concatenated strings (e.g., `f"IDS_ITEM.ID{id}"`) and computes their unsigned 32-bit CRC32 hash (`zlib.crc32(x) & 0xFFFFFFFF`). This hash is formatted as an 8-character hex string (or converted to little-endian binary) and cross-aligned against the `ids_item.bytes` map decoded via `msgpack` (configured with `strict_map_key=False` to support non-strict binary keys) to precisely restore Chinese plaintext.

---

## Spine Animation Reconstruction & Image Processing Pipeline

For Over-Frame card art and Spine Cut-In animations, matching image reconstruction algorithms and 2D skeletal math mappings are implemented.

### 9. Premultiplied Alpha Edge Purification
Spine skeletal animations in Unity typically use Premultiplied Alpha blending. Importing standard RGBA images directly causes black borders and antialiasing artifacts on semi-transparent edges. The `apply_premultiplied_alpha` algorithm uses NumPy vectorized operations to normalize and multiply RGB values with the Alpha channel:

```
Color_new = Color_orig * (Alpha / 255.0)
```

This matrix calculation removes edge artifacts and reproduces official-grade transparent gradients.

### 10. Decreasing Height Shelf Packing
To consolidate animation frames into a single texture atlas, a decreasing height shelf packing algorithm is implemented. Sub-images are sorted in descending order by height, then placed left-to-right and top-to-bottom on a canvas up to a defined maximum size (e.g., 8192x8192). If the remaining width in the current row is insufficient, a new row is opened. A 2-pixel padding buffer is injected around each sub-image edge to prevent texture sampling bleed during dynamic scaling.

### 11. Power-of-Two (POT) Alignment & VRAM Optimization
To enable efficient hardware texture compression formats (such as BC7) when Unity loads the output texture atlas, the final canvas size is rounded up to the nearest power of two (e.g., 1024, 2048, 4096, 8192). This alignment optimizes VRAM alignment and sampling performance on GPUs (such as TUF 5070ti).

### 12. Spine 4.2.43 Summon Animation Coordinate Conversion & Bone Translation
The official game Spine animation resolution baseline is 4800x2700. When reading/writing `js-hd.json`, manual pixel offset parameters (`offset_x`, `offset_y`) are automatically parsed and mapped precisely to the Spine world coordinate system:

```
Translate_world_x = (Offset_pixel_x / Canvas_width) * 4800.0
Translate_world_y = -(Offset_pixel_y / Canvas_height) * 2700.0
```

Simultaneously, based on user POP UP timing configurations, internal dynamic interpolators compute keyframe scale ratios along the timeline to ensure visual alignment during rendering.

### 13. PSD Fallback Layer Isolation Rendering (Fallback Layer Isolation)
To automatically composite over-frame cards (five separate layers: PeriFrame, NameBox, ArtFrame, EffFrame, EffBox, BackGround), `psd-tools` is integrated. Considering smart layers or special channels may cause direct composite crashes, dual-track isolation rendering is implemented:
* Track 1: Attempts standard local layer rendering and offset alignment.
* Track 2 (Fallback): If Track 1 fails, visibility for all PSD layers is backed up and turned off. The target layer and its parent group are turned on individually to trigger full global composite rendering (`Composite`), accommodating complex blend modes, before restoring layer visibilities.

---

## Memory-Safe Direct Injection & Registry Reconstruction

For large lobby backgrounds and Over-Frame whitelist registries, lossless binary modifications are implemented.

### 14. Unity Bundle Texture Direct Binary Injection
In handling lobby backgrounds (such as `data.unity3d`) or legacy mod stream fixes, traditional full unpack-and-repack approaches consume extreme system performance and risk structure incompatibility. Memory direct injection technology is implemented:
After UnityPy loads target objects, `path`, `offset`, and `size` in `m_StreamData` are forcibly cleared to sever connections to external large files (.resS). Decoded raw bytes are then written directly into Texture2D `image_data` attributes. This avoids unpacking crashes and achieves safe binary injection.

### 15. `of_card_asset` Registry Binary Reconstruction
The Over-Frame 3D card art whitelist is stored in `of_card_asset`. Loaded as a TextAsset, its byte stream is unpacked using `<HH` layout (little-endian unsigned short pair representing Trigger ID and Target ID).
Upon input of new registered card IDs, conflict checking excludes official placeholder rules and conflicting target logic before merging new key-value pairs incrementally and repacking back into binary asset data.

---

## Virtual Mount Transactions & Safe Rollback Mechanism

The Virtual Mod Manager utilizes Windows Symbolic Links (Symlinks) to achieve zero-disk-space instant mod application and testing.

### 16. Symlink Transaction Defense & Rollback Engine
Before creating symbolic links, target original game files are backed up and renamed with `.vanilla_backup`. To guard against unexpected errors like insufficient privileges (non-admin execution) or locked game process handles, "atomic transactions" are implemented:
`symlink_state.json` tracks all backup and link mapping records in real time. If an error occurs during link creation, the rollback engine immediately terminates further tasks, deletes established links according to records, and restores original backup filenames to protect game file integrity.

### 17. Smart Longest Prefix Matching (Longest Prefix Match)
To allow user-defined, descriptive file names during mod replacement and automated flows (e.g., naming `12345.png` as `12345_Mirrorjade_CustomArt.png`), longest prefix matching is implemented.
All custom filenames are read and sorted in descending order of length, matching from the longest candidate against valid card IDs in the CSV dictionary. After matching, boundary validation checks if the trailing character is an underscore, hyphen, dot, or end-of-string to prevent matching `123456` to `12345`, ensuring high-tolerance and safe batch naming compatibility.

---

## Static Analysis & Dynamic Multi-Language Extraction

To provide complete internationalization (i18n) support without increasing maintenance overhead, Abstract Syntax Tree analysis is implemented.

### 18. AST Static String Extraction
Using Python's `ast` module, static code analysis extracts string data without executing code.
The algorithm traverses `ast.Call` and `ast.keyword` nodes to extract plain text wrapped in `_("...")`, `placeholder="..."`, and sidebar `DEFAULT_TABS`. These strings are compared against `zh-tw.json` in the `Languages` directory to retain existing translations, incrementally fill missing keys, and re-sort output files for automated language dictionary maintenance.

---

## Developer & Build Compatibility Support

### 19. PyInstaller FMOD Dynamic Mocking (Virtualization)
When compiling and packaging the project into a standalone Windows executable (EXE), native engine FMOD sound dependencies (e.g., `fmod_toolkit`, `pyfmodex`) often cause crash-on-launch issues if underlying C++ runtime DLLs are missing.
To eliminate this dependency constraint, a `MockModule` class (inheriting from `types.ModuleType`) is defined at top-level. Before Python imports other modules, `__getattr__` intercepts calls and returns dummy functions, dynamically mocking FMOD interfaces in `sys.modules`. This virtualization removes packaging DLL dependencies and improves executable portability.

### 20. Custom Linear Drag-Scroll Filter
To address the stiff drag experience of Qt's built-in QListWidget and severe non-disableable physics inertia oscillations when dragging outside the window, `LinearDragScrollFilter` is implemented.
The filter takes full control of drag events and introduces a floating-point pixel accumulator (`Scroll Accumulator`). Sub-pixel displacements under 1px are buffered until reaching whole integers before calling QScrollBar for precise stepping, eliminating inertia buildup and delivering a crisp, modern web-grade scrolling experience.

---

### Directory Structure
* `MD_AstellarTool.py`: Main entry point and GUI logic.
* `requirements.txt`: Python dependencies list.
* `MD_Tool_Essential/`: Static assets directory.
  * `Languages/`: Stores AST-exported and user-customized multi-language JSON files.
  * `CardFrame/`: Stores PSD templates and fallback PNG assets for Over-Frame rendering.

---

## Special Thanks

The creation and improvement of open-source projects rely on the selfless sharing and research of community predecessors. Special thanks to the following contributors and communities:

* **TranLinhVy**: Special thanks to NexusMods creator [TranLinhVy](https://www.nexusmods.com/profile/TLVv) for outstanding work and technical inspiration, which greatly assisted the development of this project.
* **Master Duel Modding & Datamining Community**: Homage to all researchers who have contributed to asset unpacking, database analysis, and tool development for *Yu-Gi-Oh! Master Duel*. Your low-level technical research and selfless sharing made MD AstellarTool possible.

### Developer Information
* Author Pixiv: [LonelyMaJo](https://www.pixiv.net/users/126514098)