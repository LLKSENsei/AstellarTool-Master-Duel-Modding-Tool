# MD AstellarTool (MD Astrea Toolbox)

[![License](https://img.shields.io/github/license/LLKSENsei/AstellarTool-Master-Duel-Modding-Tool?color=2CC985)](LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)]()
[![Platform](https://img.shields.io/badge/platform-Windows-lightgrey)]()
[![Price](https://img.shields.io/badge/Price-100%25%20Free-brightgreen)]()

This project is an automated asset parsing, database reverse engineering, binary texture injection, Over-Frame Art rendering, and virtual mod management tool specifically developed for *Yu-Gi-Oh! Master Duel*.

Built on foundational libraries such as Python 3, PySide6, UnityPy, and NumPy, this tool aims to solve the tedious pipeline steps during game asset customization, underlying file structure encryption, Spine animation coordinate reconstruction, and OS-level physical file management issues.

---

## Detailed Tutorial

As this tool is feature-rich (containing 14 independent working pipelines), to provide clearer illustrated instructions, please refer to the standalone tutorial document:

**[Click here to view the full tutorial (TUTORIAL.md)](TUTORIAL.md)**

[Video](https://youtu.be/DJUt6wblYLw)

The tutorial covers:
* How to complete a full card art replacement from scratch (0 to 1)
* Processing techniques for Pendulum and Over-Frame card art
* When to use Virtual Mount and the Stream Fixer

---

## Project Disclaimer & License

This program is a completely free and open-source tool, intended solely for technical exchange and personal research. Any form of commercial resale, bundled sales, or disguised charging is strictly prohibited. If you paid for this program, you have been scammed; please apply for a refund from the seller or platform immediately and report the merchant.

This project is open-sourced under the MIT License. This tool only provides algorithmic implementations for file parsing and modification and does *not* contain any official original game assets. The copyright and intellectual property rights of all Unity assets, game images, and related data extracted or packaged by this tool belong to the original official publisher (Konami Digital Entertainment).

---

## System Architecture & Multitasking Compute Scheduling System

Faced with the scanning, decryption, and writing tasks of tens of thousands of encrypted asset Bundle files, this tool is designed with a highly parallel multitasking architecture to balance system load, reduce I/O latency, and implement stable protection boundaries across various hardware specifications.

### 1. Synchronization Bridge of QThreadPool and TaskWorker
To prevent massive file I/O or image processing from blocking the Qt GUI's main Event Loop, this tool implements a `TaskWorker` thread component inherited from `QRunnable`. Through custom `WorkerSignals`, background threads can send progress counts and intermediate states to the main window in a Thread-Safe manner, achieving real-time rendering updates of the interface without freezing.

### 2. Compute Power Release via Multiprocessing (ProcessPoolExecutor)
For CPU-intensive tasks (e.g., decrypting binary databases, massive atlas cropping, pixel chroma-keying calculations), this tool utilizes `concurrent.futures.ProcessPoolExecutor` to implement multiprocess parallel computing. This design effectively bypasses Python's Global Interpreter Lock (GIL), allowing multi-core processors to fully schedule all logical cores. When each child process is launched, it duplicates the main process's language dictionary via `_init_worker`, ensuring semantic alignment of error messages during cross-process memory isolation.

### 3. OS-Level Memory Protection (Memory Radar)
During batch decoding of large animation frames, underlying C++ libraries may leave a massive amount of un-garbage-collected (GC) buffers in memory. To prevent physical memory exhaustion that leads to the OS forcefully terminating the process, the tool uses `ctypes` to invoke the Windows kernel's `GlobalMemoryStatusEx` API, monitoring system memory load in real-time. When physical memory usage reaches the 85% critical threshold, parallel threads will temporarily suspend and enter an adaptive sleep state until memory is released, ensuring system stability.

### 4. os.walk Dynamic Pruning Algorithm
When scanning game directories on a large scale, to prevent invalid paths and custom output directories (like temporary or backup folders) from causing `os.walk` to fall into infinite recursion or generate redundant disk I/O, this tool implements a `prune_walk_dirs` dynamic pruning mechanism. Before entering each directory level, the algorithm pre-calculates the physical subpath relationship (`is_subpath`) between the output path and the current path, directly modifying the `dirs` list to truncate recursive paths.

---

## Binary Decryption & Database Reverse Engineering

Key text and card properties within the game (e.g., `card_name.bytes`, `card_prop.bytes`) are obfuscated and compressed in binary. By analyzing their underlying binary distribution, this project implements a highly efficient decoding and alignment engine.

### 5. Custom XOR Obfuscation Decryption Formula
The game's internal binary encryption uses XOR obfuscation based on bit shifting and dynamic factors. The decryption formula is as follows:
```python
decrypted[i] = raw_bytes[i] ^ (((i + key + 0x23D) * key ^ (i % 7)) & 0xFF)
```
Where `i` is the absolute index of the byte stream, and `key` is the obfuscation key.

### 6. Heuristic Key Auto-Cracking (Bruteforce Crack)
When a game update invalidates the default key (default is 61), this tool implements an `auto_crack_key` guessing engine. The algorithm iterates within a limited key space of 0 to 1023, feeding the decrypted byte stream into the `zlib` decompression module. Since correctly decrypted files will contain clear pointers and characteristic structures like `YDLZ` upon decompression, whereas incorrect decryption triggers decompression exceptions. The tool uses this as a heuristic validation indicator, achieving self-healing capabilities without needing to statically locate offsets.

### 7. Global 6-bit Card Property Parsing Model
To parse the true Type and SubType of cards, the algorithm directly intervenes in the `card_prop.bytes` binary structure. Through an O(1) lookup table method, this model achieves extreme parsing performance. Its core logic and byte definitions are as follows:

* **Offset Alignment & Chunk Reading**: Based on the index calculated from `card_indx.bytes`, data is read in 8-Byte chunks.
* **Data Extraction & Bitmasking**:
  * The first 2 Bytes (`chunk[0:2]`) of the chunk are a little-endian unsigned short integer (`<H`), representing the Card ID (`cid`).
  * The 3rd Byte (`chunk[2]`) stores the main property. The algorithm performs a bitwise AND operation (`& 0x3F`) to strip high-bit noise, obtaining a clean 6-bit code (`b_clean`).
  * The 7th Byte (`chunk[6]`) stores the secondary property tags for Spell and Trap cards.
* **Exception Interceptor (Paradox Defense)**: Paradoxical data exists in the game database, such as ID 4644 (Queen of Autumn Leaves). Conventional parsing would cause a classification crash. The system sets up an interceptor before entering the lookup table; if it detects this ID, it forcibly assigns `Type="Monster"`, `SubType="Fusion=Non-Effect"` and returns early.
* **Smart Failsafe Line**: To guard against future game updates adding extremely rare undocumented codes, when encountering an unknown `b_clean` value, the system will automatically and safely downgrade its classification to "Effect Monster" and log the unknown hexadecimal code in `Raw_Data`. This ensures that subsequent UI rendering and frame application workflows are absolutely never interrupted.

**[Table 1: Monster Property Mapping Matrix (CARD_TYPE_MAP)]**
This table lists the main/sub-classifications corresponding to `b_clean` values.

| Hex Value (`b_clean`) | Card Type | SubType | Hex Value (`b_clean`) | Card Type | SubType |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `0x00` | Monster | Normal | `0x1B` | Monster | Effect=Special Summon |
| `0x01` | Monster | Effect | `0x1C` | Monster | Effect=Special Summon=Toon |
| `0x02` | Monster | Fusion=Non-Effect | `0x1D` | Monster | Effect=Special Summon=Spirit |
| `0x03` | Monster | Fusion=Effect | `0x1E` | Monster | Effect=Special Summon=Tuner |
| `0x04` | Monster | Ritual=Non-Effect | `0x20` | Monster | Effect=Flip=Tuner |
| `0x05` | Monster | Ritual=Effect | `0x21` | Monster | Effect=Pendulum=Tuner |
| `0x06` | Monster | Effect=Toon | `0x22` | Monster | Xyz=Pendulum |
| `0x07` | Monster | Effect=Spirit | `0x23` | Monster | Effect=Pendulum=Flip |
| `0x08` | Monster | Effect=Union | `0x24` | Monster | Synchro=Pendulum |
| `0x09` | Monster | Effect=Gemini | `0x25` | Monster | Effect=Union=Tuner |
| `0x0A` | Monster | Token | `0x26` | Monster | Ritual=Spirit |
| `0x0F` | Monster | Normal=Tuner | `0x27` | Monster | Fusion=Tuner |
| `0x10` | Monster | Effect=Tuner | `0x28` | Monster | Effect=Pendulum=Special Summon |
| `0x11` | Monster | Synchro=Non-Effect | `0x29` | Monster | Fusion=Pendulum |
| `0x12` | Monster | Synchro=Effect | `0x2A` | Monster | Link=Non-Effect |
| `0x13` | Monster | Synchro=Tuner | `0x2B` | Monster | Link=Effect |
| `0x16` | Monster | Xyz=Non-Effect | `0x2C` | Monster | Normal=Pendulum=Tuner |
| `0x17` | Monster | Xyz=Effect | `0x2D` | Monster | Effect=Pendulum=Spirit |
| `0x18` | Monster | Effect=Flip | `0x2F` | Monster | Ritual=Tuner |
| `0x19` | Monster | Normal=Pendulum | `0x30` | Monster | Fusion=Tuner |
| `0x1A` | Monster | Effect=Pendulum | `0x31` | Monster | Token=Tuner |
| | | | `0x34` | Monster | Ritual=Pendulum |
| | | | `0x35` | Monster | Ritual=Flip |

**[Table 2: Spell and Trap Card Sub-Classification Mapping Matrix]**
When `b_clean` is `0x0D` (Spell) and `0x0E` (Trap) respectively, the system turns to read the 7th Byte (`chunk[6]`) for secondary property mapping.

| Hex Value (`chunk[6]`) | Card Type | SubType |
| :--- | :--- | :--- |
| **Spell Card Branch (`b_clean == 0x0D`)** | | |
| `0x00` | Spell | Normal |
| `0x08` | Spell | Field |
| `0x0C` | Spell | Equip |
| `0x10` | Spell | Continuous |
| `0x14` | Spell | Quick-Play |
| `0x18` | Spell | Ritual |
| **Trap Card Branch (`b_clean == 0x0E`)** | | |
| `0x00` | Trap | Normal |
| `0x04` | Trap | Counter |
| `0x10` | Trap | Continuous |

### 8. Il2Cpp Metadata Lightweight Binary Regex Scanning
Chinese descriptions of non-card objects (e.g., fields, sleeves, icons) are not stored in the conventional card database. This tool abandons the heavy full Il2Cpp decompilation approach and implements a lightweight binary regex scan. By directly searching the `global-metadata.dat` file for string character streams matching the `ID([0-9]{6,7})` format, it extracts all potential plaintext IDs.

### 9. CRC32 Hash Verification & Alignment
For scanned accessory IDs, the algorithm encodes their combined strings (e.g., `f"IDS_ITEM.ID{id}"`) into binary, and calculates its unsigned 32-bit CRC32 hash value (`zlib.crc32(x) & 0xFFFFFFFF`). Subsequently, this hash value is formatted as an 8-digit hexadecimal string and cross-aligned with the `ids_item.bytes` lookup table decoded via `msgpack`, accurately restoring the plaintext Chinese of the accessory.

---

## Multi-Dimensional Tokenization & Data Search Engine

### 10. Bi-directional Assimilation & Tokenizer Search (Tokenizer & Fuzzy Search)
In the "Find File" and "Quick Single Card" search boxes, this tool implements an advanced search engine in pure Python with no external dependencies:
* **NFKC Bi-directional Assimilation**: Uses `unicodedata.normalize('NFKC', text)` to standardize full-width characters, half-width characters, Hiragana, and Katakana. It also unifies game-specific quotation marks via regex replacement.
* **Syntax Tree Tokenizer**: Supports boolean logic. Search strings are parsed into inclusion words (`+`), exclusion words (`-`), and exact phrase (`"..."`) sets.
* **Sliding Window Fuzzy Matching**: When strict matching fails, it enables `difflib.SequenceMatcher` and employs a sliding window algorithm to slice and match effect texts, ensuring local features in long texts can still be captured with high fault tolerance.
* **Matrix-Style Attribute Filtering**: Combined with the parsed `Type` and `SubType` mentioned above, it allows for multi-dimensional intersection filtering via checkboxes.

---

## Spine Animation Reconstruction & Image Processing Pipeline

For Over-Frame card art and Spine Summoning Animations (Cut-Ins), this tool implements highly integrated image reconstruction algorithms and 2D animation bone mathematical mapping.

### 11. Premultiplied Alpha Edge Purification
Spine skeletal animations typically use Premultiplied Alpha blending in the Unity engine. Importing normal RGBA images directly causes severe black borders and anti-aliasing distortion on semi-transparent edges. This tool's `apply_premultiplied_alpha` algorithm utilizes NumPy's vectorized operations to normalize and multiply the RGB color values with the Alpha channel:
```python
Color_new = Color_orig * (Alpha / 255.0)
```
This matrix operation completely eliminates edge noise, reproducing factory-level transparent gradients and halo glow effects.

### 12. Chroma Key & Despill Algorithm
For MP4 or live-action video materials imported by the user, the system features a built-in pure matrix calculation background removal engine:
* **Color Space Euclidean Distance**: Calculates the 3D distance `sqrt((r-tr)^2 + (g-tg)^2 + (b-tb)^2)` between each pixel and the Target Color. If the distance is greater than the Tolerance, it is deemed a kept area, and supports GaussianBlur for edge feathering.
* **Despill (Spill Correction)**: Video edges often reflect the green screen's light. The algorithm checks if the current pixel is green-dominant (`g > r` and `g > b`). If so, it suppresses the green channel to the maximum of the red and blue channels `min(g, max(r, b))`, and blends in the original color based on the spill correction strength ratio, restoring the natural lighting of the edges.

### 13. Height-Descending Shelf Packing & POT Alignment
To integrate multiple frames of an animation into a single Texture Atlas, the algorithm first sorts all sub-images in descending order based on their cropped height (Bounding Box Height), then horizontally packs them from left to right on a canvas of a set maximum size (e.g., 8192x8192). A 2-pixel color-bleed prevention gap is forcibly injected around the edges of each sub-image. After packing, the final canvas size is rounded up to the nearest Power-of-Two (POT), significantly optimizing the graphics card's memory alignment and texture compression (BC7) performance during runtime.

### 14. Spine 4.2.43 Summon Animation Coordinate Conversion & Bone Translation
The game's official Spine animation resolution baseline is 4800x2700. When dynamically generating the `js-hd.json` skeleton description file, this tool automatically parses the user's manual pixel offset parameters and accurately aligns them to the Spine world coordinate system:
```python
Translate_world_x = (Offset_pixel_x / Canvas_width) * 4800.0
Translate_world_y = -(Offset_pixel_y / Canvas_height) * 2700.0
```
Note: Because the PIL image coordinates (Y-axis points down) and Spine world coordinates (Y-axis points up) are opposite, the Y-axis sign is forcibly inverted during translation, ensuring what the user sees in the UI preview is what they get.

### 15. Dual-Layer Over-Frame Synthesis & Alpha Geometric Boolean Punch-Hole (Z-Order Synthesis)
Over-Frame art processing is not just scaling and cropping. In `MODE_OVERFRAME` mode, the algorithm executes complex layer synthesis and mask calculations:
* **Multi-Layer Rendering Mechanism**: Drawn sequentially from bottom to top: Background Plate (`-bg`) -> Card Back Background -> Effect Text Box -> Card Art Frame -> Effect Frame -> Card Name Box -> Outer Border -> Character Layer (`-ch`).
* **Geometric Purification & Boolean Intersection**: To allow the character layer to "pass through" the physical card frame without being obscured by the frame, the algorithm uses NumPy to extract the Alpha mask of the clean frame. It performs a bitwise AND intersection (`m_ch_art & m_3frames_clean`) between the "Character Layer Alpha > 0" region and the masks of the "Three Major Frames (Outer Border, Art Frame, Effect Frame)".
* **Auto Punch Hole**: Forcibly invalidates the calculated intersection area in the Alpha channel of the final composited image (`data[m_final_zero, 3] = 0`). This makes the frame portion transparent during the game's 3D shader rendering, allowing the character layer behind it to fill in the gap, achieving a seamless 3D frame-breaking stereoscopic effect.

### 16. In-Game Foil Shader Simulation
To make the UI preview and the baked effects outputted to the card art perfectly replicate the game's Diamond/Royal finish effects, this project uses advanced mathematics in Python to delineate a complete set of Shaders:
* **IQ Cosine Palette**: Uses the formula `a + b * cos(2pi * (c*t + d))` to calculate a smoothly transitioning rainbow/champagne gold/platinum diamond color matrix based on the pixel's X/Y coordinates, rotation angle, and wave frequency.
* **High-Pass Focus**: Adopts the human visual luminance formula `0.299R + 0.587G + 0.114B` to calculate lightness, and exponentially amplifies it `power(lum, sharpness)` to calculate the brightness ratio matrix. Multiplying this ratio back into the RGB channels successfully constrains the soft spectrum into sharp laser reflection bands without causing hue shifts.
* **Pegtop Soft Light Blending Engine**: Adopts the standard Pegtop soft light blending formula: `(1 - 2*Foil) * Base^2 + 2*Base*Foil`. Unlike traditional Screen or Additive modes, this algorithm perfectly preserves the underlying card art's bump textures and dark outlines, allowing the flash effect to seep into the layers like physical printing.

### 17. PSD Multi-Layer Fallback Layer Isolation Rendering Algorithm
To automatically read card frame templates, the tool integrates `psd-tools`. Considering that smart layers or special channel blend modes might cause direct composite rendering to crash, the program implements dual-track isolated rendering:
* Track 1: Attempts conventional localized layer rendering and offset alignment.
* Track 2 (Fallback): If Track 1 throws an exception, the system temporarily backs up the visibility state of all PSD layers and sets them all to hidden, solely lighting up the target layer and its parent group channels to invoke global image rendering. This method bypasses local rendering limitations, is compatible with all complex layer styles, and restores all layer visibilities once rendering is complete.

---

## Memory-Safe Direct Injection & Registry Reconstruction

For large lobby backgrounds and Over-Frame whitelist registrations, this tool implements lossless binary data modification, completely avoiding the structural damage risks brought by unpacking and repacking.

### 18. Unity Bundle Texture Color Space & Data Stream Injection
* **Stream Severing**: When processing lobby backgrounds (e.g., `data.unity3d`) or repairing old mod streams, the program forcibly clears the `path`, `offset`, and `size` in the `m_StreamData` structure to 0, severing the Unity engine's dependence on and addressing of external massive resource files (.resS).
* **Direct Overwrite**: Converts the image data processed by PIL or OpenCV into raw bytes and assigns them directly to the `image_data` property of the Texture2D.
* **Gamma Space Correction**: When the replaced file matches the `p\d+` (summon animation texture) regex feature, the program intervenes in the data stream, forcibly overwriting Unity's `m_ColorSpace` property to `0` (Linear space). This eliminates the possibility of the engine applying secondary Gamma correction to sRGB images, completely solving the long-standing pain point of mod animations looking washed out and losing saturation upon entering the game.

### 19. `of_card_asset` Registry Binary Reconstruction & Incremental Merging
The Over-Frame 3D card art whitelist is stored in the `of_card_asset` file. This tool loads it as a TextAsset and implements an absolutely safe modification mechanism:
* **Unpacking**: Uses `struct.unpack("<HH", ...)` to unpack the script byte stream in groups of 4 Bytes into two little-endian 16-bit unsigned short integers (Trigger ID and Target ID).
* **Incremental Diff**: Every time the registry is read, the system searches the cache directory for a pure `.pristine` original backup. Using Python dictionary comprehension to compare the differences between the two, it accurately extracts the "difference set purely modified by the player".
* **Conflict Interception & Writing**: When writing the new registry list, the system compares the target IDs input by the player. If it encounters the official's original special placeholders (pointing to 0) or logical contradictions where the same item points to different targets, it triggers a safety interrupt. After passing validation, it merges the difference set with the latest version of the official base, repackages it into a binary stream via `struct.pack("<HH")`, and writes it back to the asset. This technology ensures that even if the game undergoes a major update, the Over-Frame whitelist painstakingly built by the player can be seamlessly transferred across versions.

---

## Virtual Mount Transactions & Safe Rollback Mechanism

The Virtual Mod Manager utilizes Windows Symbolic Link (Symlink) technology, aiming to implement instant mod application and testing with zero hard drive space occupation.

### 20. Symlink Transaction Defense & Rollback Engine
Before creating a soft link, the manager first backs up the target original game file, renaming it to `.vanilla_backup`. When creating symbolic links, to guard against insufficient privileges (non-admin execution) halfway through or the file being locked by the game process, the tool implements "Atomic Transactions":
The program logs all backup and link mapping trails (State Log) in real-time in `symlink_state.json`. If an OS exception is thrown during the Symlink creation process of any file, the rollback engine intervenes immediately and terminates subsequent loops. The engine reads the JSON trail log, forcibly unlinks (`os.unlink`) all phantom links created during this task, and restores the corresponding backup files to their original positions. This design ensures that the game folder structure always maintains consistency, leaving no broken half-finished products.

### 21. Smart Longest Prefix Match
In the image replacement and automated packaging workflows, to allow users to customize more identifiable image file names (e.g., naming `12345.png` as `12345_Mirrorjade_CN_AltArt.png`), this tool abandons the rigid `split('_')[0]` slicing method and implements a longest prefix match.
The algorithm reads all custom names and sorts them in descending order by character length, starting from the longest string to attempt a match with valid Card IDs in the CSV dictionary (`test_str.startswith(prefix)`). After a successful match, the algorithm implements a Boundary Check: it verifies that the first character following the matched string must be a valid separator (underscore, hyphen, dot, space) or the string's end directly. This ensures that a card named `123456.png` is not incorrectly categorized under ID `12345`, achieving high fault tolerance and highly safe batch naming compatibility.

---

## Static Analysis & Dynamic Multi-Language Extraction

To provide comprehensive internationalization (i18n) support without increasing maintenance costs, this project implements abstract syntax tree analysis.

### 22. AST Abstract Syntax Tree Static String Extraction
This tool utilizes Python's `ast` module to perform static parsing (Static Analysis) on the code, constructing an abstract syntax tree without actually executing the code.
The algorithm traverses all `ast.Call` (call nodes) and `ast.keyword` (keyword argument nodes), accurately extracting all plaintext strings wrapped in `_("...")`, within `placeholder="..."` watermarks, and defined in the `DEFAULT_TABS` dictionary of the sidebar. Subsequently, the algorithm automatically compares them with the `zh-tw.json` in the Languages directory as key-value pairs, retains the translated content manually adjusted by the player, incrementally fills in the new statements added in the code, re-sorts the dictionary, and writes it back to JSON, achieving a highly automated multi-language dictionary iteration with zero human intervention.

---

## Developer & Compilation Environment Compatibility Support

### 23. PyInstaller FMOD Dynamic Virtualization (Mocking)
When compiling and packaging the project into a standalone Windows executable (EXE), the game engine's native FMOD audio module dependencies (such as `fmod_toolkit`, `pyfmodex`) often cause the compiled program to crash with an `ImportError` upon launch because the compilation environment lacks the underlying C++ runtime dynamic link libraries (DLLs).
To remove this underlying dependency restriction, the tool defines a `MockModule` class (inheriting from `types.ModuleType`) at the very top level of the program. Before the Python interpreter attempts to load other modules, it intercepts the `__getattr__` magic method to make it return an empty anonymous function (`lambda *args, **kwargs: None`), and dynamically Mock overwrites all FMOD interfaces in the `sys.modules` dictionary. This virtualization technique perfectly eliminates the physical DLL dependency during packaging, ensuring the lightweight nature and portability of the tool library.

### 24. Custom Linear Drag-Scroll Filter
Aimed at the issue where Qt's built-in `QListWidget` and `QScrollArea` feel stiff when dragged, and produce severe, unstoppable physical inertial oscillation when the mouse moves out of the window, this project implements a `LinearDragScrollFilter`.
The filter completely takes over the window's mouse click and move events via `installEventFilter` and introduces a floating-point pixel Scroll Accumulator. It substitutes the distance between the cursor and the window boundary into a sensitivity coefficient for decimal point calculation, temporarily storing micro-displacements of less than 1 pixel in a bucket. Once the accumulation reaches an integer, it calls the QScrollBar for precise stepping, retaining the remaining decimal points. The instant the mouse is released, the system immediately forces the `QTimer` to stop and clears the accumulator. This solves the inertial accumulation problem of Qt's underlying event stack, achieving an instant-stop, extremely smooth modern web-level scrolling experience.

---

### Directory Structure Description
* `MD_AstellarTool.py`: Main program entry point and interface logic.
* `requirements.txt`: Python dependency list.
* `MD_Tool_Essential/`: Static resources directory.
  * `Languages/`: Stores multi-language JSON files exported via AST and customized by users.
  * `CardFrame/`: Stores PSD templates used for Over-Frame rendering and PNG fallback images for downgrade usage.

---

## Special Acknowledgments

The creation and perfection of open-source projects rely heavily on the selfless sharing and research of predecessors in the community. Special thanks to the following contributors and communities:

* **TranLinhVy**: Special thanks to NexusMods creator [TranLinhVy](https://www.nexusmods.com/profile/TLVv) for their excellent work and technical inspiration, which greatly helped the development of this project.
* **Master Duel Datamining & Modding Community**: Saluting all researchers who have contributed to *Yu-Gi-Oh! Master Duel* asset unpacking, database analysis, and tool development. MD AstellarTool was born thanks to your dedication to underlying technologies and selfless sharing.

### Developer Information
* Author Pixiv: [LonelyMaJo](https://www.pixiv.net/users/126514098)