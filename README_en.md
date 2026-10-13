# MD AstellarTool

[![License](https://img.shields.io/github/license/LLKSENsei/AstellarTool-Master-Duel-Modding-Tool?color=2CC985)](LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)]()
[![Platform](https://img.shields.io/badge/platform-Windows-lightgrey)]()
[![Price](https://img.shields.io/badge/Price-100%25%20Free-brightgreen)]()

This project is an automated asset parsing, database reverse engineering, binary texture injection, Over-Frame Art rendering, and virtual mod management tool specifically developed for *Yu-Gi-Oh! Master Duel*.

Built upon low-level libraries including Python 3, PySide6, UnityPy, and NumPy, this tool aims to resolve the tedious pipeline steps in game asset customization, underlying file structure encryption, Spine animation coordinate reconstruction, and OS-level physical file management issues.

---

## Detailed Usage Tutorial

As this tool is feature-rich (containing 14 independent pipelines), please refer to the dedicated tutorial documentation for clearer illustrated instructions:

**[Click here to view the complete tutorial (TUTORIAL.md)](TUTORIAL.md)**

[Video](https://youtu.be/DJUt6wblYLw)

The tutorial covers:
* How to complete a full card artwork replacement from scratch.
* Processing techniques for Pendulum and Over-Frame Art.
* Use cases for the Virtual Mount and Stream Updater.

---

## Project Disclaimer & License Terms

This program is a completely free and open-source tool, intended solely for technical exchange and personal research. Commercial reselling, repackaged selling, or disguised charging for this program in any form is strictly prohibited. If you paid to acquire this program, you have been scammed; please immediately request a refund from the seller or platform and report the merchant.

This project is open-sourced under the MIT License. This tool only provides algorithmic implementations for file parsing and modification and does not include any official original game assets. The copyrights and intellectual property rights of all Unity assets, game images, and related data extracted or packed by this tool belong to the original official publisher (Konami Digital Entertainment).

---

## System Architecture & Multi-Tasking Compute Scheduling System

Faced with the tasks of scanning, decrypting, and writing tens of thousands of encrypted asset Bundle files, this tool is designed with a highly concurrent multi-tasking architecture to balance system load, reduce I/O latency, and implement stable protection boundaries across various hardware specifications.

### 1. The Synchronous Bridge between QThreadPool and TaskWorker
To prevent massive file I/O or image processing from blocking the Qt GUI's main Event Loop, this tool implements a `TaskWorker` thread component inheriting from `QRunnable`. Through custom `WorkerSignals`, background threads can send progress counts and intermediate states to the main window in a Thread-Safe manner, realizing real-time rendering updates of the interface without freezing.

### 2. Cross-Process Memory Isolation & IPC Safe Interruption (ProcessPoolExecutor & StopEvent)
For CPU-intensive tasks (e.g., decrypting binary databases, massive atlas cropping), this tool employs multi-process parallel computing, bypassing Python's Global Interpreter Lock (GIL). To address OS limitations and memory isolation brought by cross-processing, the following protections are implemented:
* **Clone Arming of Language Dictionaries (`_init_worker`)**: When Windows subprocesses start, their memory is empty and cannot read the main program's UI translation dictionary. The program forces the `UI_LANG_DICT` to be cloned and injected into the subprocess via initialization parameters every time a CPU core starts, ensuring that the semantic meaning of exception reports perfectly aligns with the main window if a subprocess crashes.
* **IPC-Level Safe Brakes (`multiprocessing.Event`)**: In brute-force scanning or large-file decryption tasks that easily take dozens of seconds, the tool deeply passes a `stop_event` interruption flag. Upon receiving the interrupt signal, each core will immediately `break` early in the `os.walk` or decryption loop and safely release memory, avoiding zombie processes left behind by abrupt process termination.

### 3. OS-Level Memory Protection (Memory Radar)
When batch decoding large animation frames, underlying C++ libraries may leave massive un-garbage-collected (GC) buffers in memory. To prevent physical memory exhaustion that leads the OS to forcibly terminate the process, the tool uses `ctypes` to invoke the Windows kernel's `GlobalMemoryStatusEx` API to monitor system memory load in real-time. When physical memory usage reaches the 85% threshold, concurrent threads will temporarily suspend and enter an adaptive sleep state until memory is released, ensuring system stability.

### 4. Dynamic Barrier Pruning & URI Smart Sanitization (`prune_walk_dirs` & `clean_path`)
* **Infinite Recursion Defense**: During large-scale scanning, if a user sets a custom output directory inside the scanning source, it will trigger an infinite loop. `get_child_exclude_paths` pre-calculates dangerous physical boundaries (`is_subpath`) and directly modifies the `dirs` array to truncate and remove them before `os.walk` enters that directory level.
* **URI Scheme Smart Sanitization**: For paths dragged in by users from browsers or externally, the built-in `clean_path` automatically intercepts and strips `file://` and `//localhost/` prefixes, and normalizes backslashes, ensuring absolute safety for underlying hard drive I/O addressing.

---

## Binary Decryption & Database Reverse Engineering

Crucial texts and card properties (e.g., card_name.bytes, card_prop.bytes) within the game are obfuscated and compressed in binary. This project implements an efficient decoding and alignment engine by analyzing their underlying binary distribution.

### 5. Custom XOR Obfuscation Decryption Formula
The game's internal binary encryption uses XOR obfuscation based on bitwise shifting and dynamic factors. The decryption formula is as follows:
```python
decrypted[i] = raw_bytes[i] ^ (((i + key + 0x23D) * key ^ (i % 7)) & 0xFF)
```
Where `i` is the absolute index of the byte stream, and `key` is the obfuscation key.

### 6. Heuristic Key Auto-Cracking (Bruteforce Crack)
When a game version update causes the default key (default value 61) to fail, this tool implements the `auto_crack_key` guessing engine. The algorithm iterates within a finite key space from 0 to 1023, inputting the decrypted byte stream into the `zlib` decompression module. Since correctly decrypted files will contain explicit pointers and signature structures like `YDLZ` upon decompression, whereas incorrect decryptions will trigger decompression exceptions, the tool uses this as a heuristic validation metric, achieving self-repairing capabilities without needing statically located offsets.

### 7. Global 6-bit Card Property Parsing Model (Card Property Parsing)
To parse the true Type and SubType of cards, the algorithm directly intervenes in the `card_prop.bytes` binary structure. Through O(1) table lookups, this model achieves extreme parsing performance, with its core logic and byte definitions as follows:

* **Offset Alignment and Chunk Reading**: Based on the index calculated from `card_indx.bytes`, data is read in 8-byte chunks.
* **Data Extraction and Bitmasking**:
  * The first 2 bytes (`chunk[0:2]`) of the chunk are a little-endian unsigned short (`<H`), representing the Card ID (`cid`).
  * The 3rd byte (`chunk[2]`) stores the primary property. The algorithm performs a bitwise AND operation (`& 0x3F`) to strip high-bit noise, obtaining a clean 6-bit code (`b_clean`).
  * The 7th byte (`chunk[6]`) stores the secondary property markers for Spell and Trap cards.
* **Paradox Defense (Exception Interceptor)**: Known paradox data exists in the game database, such as ID 4644 (Queen of Autumn Leaves). Routine parsing would cause classification crashes. The system sets up an interceptor before entering the lookup table; if this ID is detected, it forcibly assigns `Type="Monster"`, `SubType="Fusion=Non-Effect"`, and returns early.
* **Smart Failsafe Defense**: To guard against extremely rare, unrecorded codes added in future game updates, when encountering an unknown `b_clean` value, the system automatically and safely downgrades the classification to "Effect Monster", and logs the unknown hexadecimal code in `Raw_Data`, ensuring that subsequent UI rendering and frame application processes are absolutely never interrupted.

**[Table 1: Monster Property Mapping Matrix (CARD_TYPE_MAP)]**
This table lists the primary/secondary monster classifications corresponding to `b_clean` values.

| Hex Value (`b_clean`) | Card Type (Type) | SubType | Hex Value (`b_clean`) | Card Type (Type) | SubType |
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

**[Table 2: Spell and Trap Card SubType Mapping Matrix]**
When `b_clean` is `0x0D` (Spell) and `0x0E` (Trap) respectively, the system pivots to read the 7th byte (`chunk[6]`) for secondary property mapping.

| Hex Value (`chunk[6]`) | Card Type (Type) | SubType |
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
Chinese descriptions for non-card objects (e.g., Fields, Protectors, Icons) are not stored in the regular card database. This tool abandons heavy complete Il2Cpp decompilation solutions and implements a lightweight binary regex scan. By directly searching the `global-metadata.dat` file for string character streams matching the `ID([0-9]{6,7})` format, it extracts all potential plaintext IDs.

### 9. CRC32 Hash Checksum and Alignment
For the scanned accessory IDs, the algorithm applies binary encoding to their combined strings (e.g., `f"IDS_ITEM.ID{id}"`) and calculates their unsigned 32-bit CRC32 hash value (`zlib.crc32(x) & 0xFFFFFFFF`). Subsequently, it formats this hash value as an 8-digit hexadecimal string and cross-aligns it with the `ids_item.bytes` mapping table decoded via `msgpack`, accurately restoring the plaintext names of accessories.

---

## Multi-Dimensional Tokenization & Data Retrieval Engine

### 10. Bidirectional Assimilation & Tokenization Search (Tokenizer & Fuzzy Search)
In the search boxes of "Find Files" and "Quick Single Card Mod", this tool implements a pure Python high-level search engine with no external dependencies:
* **NFKC Bidirectional Assimilation**: Uses `unicodedata.normalize('NFKC', text)` to standardize full-width characters, half-width characters, hiragana, and katakana. It simultaneously unifies game-specific quotation marks via regex substitution.
* **Syntax Tree Tokenizer**: Supports boolean logic. The search string is parsed into inclusive terms (`+`), exclusive terms (`-`), and exact phrases (`"..."`).
* **Sliding Window Fuzzy Matching**: When strict matching fails, `difflib.SequenceMatcher` is enabled, employing a sliding window algorithm to slice and match effect texts, ensuring local features in long texts can be captured with high fault tolerance.
* **Matrix Property Filtering**: Combining the parsed `Type` and `SubType` mentioned above, it allows multi-dimensional intersection filtering via checkboxes.

---

### 10.5 Dual-Track CSV Header Degradation & Dynamic Fault Tolerance Matrix (`find_lang_column_index`)
To be compatible with various older versions of CSV mapping tables circulated online, the database engine implements a dual-track parser with a `strict` parameter:
* **Loose Reading Mode (`strict=False`)**: When searching and reading, fuzzy matching degradation (Fallback) is activated. As long as the header contains "名", "Name", or "名稱", even without a formal language tag, it can successfully fetch data, preventing old CSVs from paralyzing the program.
* **Strict Writing Mode (`strict=True`)**: When expanding and writing, the engine becomes extremely strict. If the standard format matching `zh-tw(Name)` cannot be found, the system will **absolutely not** overwrite or guess using old columns, but forcibly and losslessly expand a brand new column on the far right, ensuring long-term backward and forward compatibility of the database format.

---

## Spine Animation Reconstruction & Image Processing Pipeline

For Over-Frame art and Spine summoning animations (Cut-In), this tool implements a highly integrated image reconstruction algorithm and 2D animation skeleton mathematical mapping.

### 11. Premultiplied Alpha Edge Border Purification
Spine skeletal animations typically use Premultiplied Alpha blending in the Unity engine. Directly importing ordinary RGBA images causes severe black borders and anti-aliasing distortion on semi-transparent edges. This tool's `apply_premultiplied_alpha` algorithm utilizes NumPy's vectorized operations to normalize and multiply RGB color values with the Alpha channel:
```python
Color_new = Color_orig * (Alpha / 255.0)
```
This matrix operation completely eliminates edge noise, reproducing factory-level transparent gradients and glowing bloom effects.

### 12. Chroma Key & Despill Algorithm
For imported MP4 or live-action video footage, the system has a built-in Chroma Key engine powered purely by matrix operations:
* **Color Space Euclidean Distance**: Calculates the 3D distance `sqrt((r-tr)^2 + (g-tg)^2 + (b-tb)^2)` between each pixel and the Target Color. If the distance is greater than the Tolerance, it is determined to be a preserved area, and supports GaussianBlur for edge feathering.
* **Despill**: Video edges often reflect light from the green screen. The algorithm determines if the current pixel is dominated by green (`g > r` and `g > b`). If so, it suppresses the green channel to the maximum of the red and blue channels `min(g, max(r, b))`, and blends in the original color based on the despill intensity ratio, restoring natural lighting to the edges.

### 13. Descending Shelf Packing & Anti-Bleed Padding
To integrate multiple frames into a texture atlas, the algorithm packs them by sorting their sub-image heights in descending order.
* **2-Pixel Anti-Bleed Padding**: Forces the insertion of a `padding_val = 2` gap during packing. This completely solves the long-standing pain point where the Unity engine, during Spine animation POP UP magnification, causes GPU Bilinear Filtering to incorrectly sample neighboring image edge pixels, generating mysterious black lines and noisy borders.
* **POT Memory Alignment**: After packing is complete, the canvas dimensions are rounded up to the nearest Power-of-Two, significantly optimizing texture compression performance.

### 14. Spine 4.2.43 Skeleton Translation & Viewport Sinking Defense
When dynamically generating the `js-hd.json` skeleton descriptor, this tool implements precise world coordinate conversion:
* **Lossless Pixel Translation**: Abandons the traditional image cropping translation method, converting the user-input X/Y pixel offsets into world scale (`Offset / Canvas * 4800.0`), directly written into the Spine skeleton's `root` node, ensuring image assets are absolutely never cut off by canvas edges.
* **Viewport Sinking Evasion**: Forcibly depresses the skeleton's default `y` coordinate from the factory `-1350.0` down to `-1470.0`, perfectly evading the cropping boundaries of the top UI in the battle screen.

### 15. Dual-Layer Over-Frame Synthesis & Alpha Geometric Boolean Punch-Hole (Z-Order Synthesis)
Over-Frame card art processing is not just scaling and cropping. In `MODE_OVERFRAME` mode, the algorithm executes complex layer synthesis and mask calculation:
* **Multi-Layer Rendering Mechanism**: Drawn sequentially from bottom to top: Background base (`-bg`) -> Card Back Background -> Effect Text Box -> Card Art Frame -> Effect Frame -> Card Name Box -> Outer Frame -> Character Layer (`-ch`).
* **Geometric Purification and Boolean Intersection**: To allow the character layer to "pass through" the physical card frames without being obscured by them, the algorithm uses NumPy to extract pure Alpha masks of the frames. It performs a bitwise AND intersection (`m_ch_art & m_3frames_clean`) between the "Character Layer Alpha > 0" area and the "Three Major Frames (Outer Frame, Art Frame, Effect Frame)" masks.
* **Automatic Punch Hole**: The calculated intersected area is forcibly voided in the final synthesized image's Alpha channel (`data[m_final_zero, 3] = 0`). This makes the frame portions transparent during the game's 3D shader rendering, filled by the character layer behind them, realizing seamless 3D frame-breaking stereoscopy.

### 16. In-Game Foil Shader Simulation
To make UI previews and baked effects outputted on card artworks perfectly restore the diamond/royal finish particle effects in-game, this project carves out a complete Shader using advanced mathematics in Python:
* **IQ Cosine Palette Generation**: Uses the formula `a + b * cos(2pi * (c*t + d))` to calculate smoothly transitioning rainbow/champagne gold/platinum diamond color scale matrices based on pixel X/Y coordinates, rotation angles, and band frequencies.
* **High-Pass Focus**: Calculates luminance using the human visual brightness formula `0.299R + 0.587G + 0.114B`, and exponentially amplifies it `power(lum, sharpness)` to calculate a brightness ratio matrix. Multiplying this ratio back into the RGB channels successfully focuses the soft spectrum into sharp laser reflection bands without causing hue shifts.
* **Pegtop Soft Light Blending Engine**: Adopts the standard Pegtop soft light blending formula: `(1 - 2*Foil) * Base^2 + 2*Base*Foil`. Unlike traditional Screen or Additive modes, this algorithm perfectly preserves the bump textures and dark contours of the underlying card artwork, making the foil effect penetrate the layers as if it were physically printed.

### 17. PSD Multi-Layer Fallback Isolation Rendering Algorithm (Fallback Layer Isolation)
To automatically read card frame templates, the tool integrates `psd-tools`. Considering that smart layers or special channel blending modes might cause direct Composite rendering to crash, the program implements dual-track isolation rendering:
* Track One: Attempts conventional localized layer rendering and offset alignment.
* Track Two (Fallback Global Isolation Rendering): If Track One throws an exception, the system enables the `vis_backup` dictionary, backing up the "Visibility" status of all PSD layers, then sets them all to hidden. It exclusively turns on the target layer and its parent group channels and invokes global rendering. After rendering, a `finally` block flawlessly restores the lighting status of the entire PSD, preventing the loss of components when subsequently extracting other frames. This method bypasses local rendering limitations, making it compatible with all complex smart layer styles.

---

## Memory Safe Direct Injection & Registry Reconstruction

For large lobby backgrounds and Over-Frame whitelisting registries, this tool implements lossless binary data modification, completely evading the structural damage risks brought by unpacking and repacking.

### 18. Unity Bundle Texture Color Space & Data Stream Injection
* **Stream Severing**: When processing lobby backgrounds (like `data.unity3d`) or repairing old mod streams, the program forcibly clears the `path`, `offset`, and `size` in the `m_StreamData` structure to 0, severing the Unity engine's dependence and addressing on massive external resource files (.resS).
* **Direct Overwriting**: Converts image data processed by PIL or OpenCV into raw bytes, and directly assigns them to the `image_data` property of Texture2D.
* **Gamma Space Correction**: When a replaced file matches the regex pattern for `p\d+` (summoning animation textures), the program intervenes in the data stream, forcibly overwriting Unity's `m_ColorSpace` property to `0` (Linear space). This eliminates the possibility of the engine applying secondary Gamma corrections to sRGB images, completely solving the long-standing pain point of mod animations appearing washed out and losing saturation after entering the game.

### 18.5 System Core Large File (`data.unity3d`) Exclusive State Machine & Manifest History Tracking
Targeting lobby system files that are hundreds of MBs large and manage game UIs, the program abandons conventional card processing logic and establishes a completely independent asynchronous management ecosystem (`task_batch_replace_data_unity3d`):
* **Atomic Operations & Forced Release**: Uses `safe_copy_file` to create a `.tmp` temporary file followed by instantaneous replacement. After writing, it forcibly invokes `gc.collect()` consecutively, purging massive bytearray buffers left in RAM by UnityPy, completely eliminating Out-Of-Memory (OOM) crashes triggered by continuously replacing large files.
* **Tri-State Manifest Tracking System**: Creates `data_mod_manifest.json` in a dedicated workspace, tracking the "size and modification time of the official pristine version", "last injection status", and "list of registered mods" in real-time. This system allows the UI to accurately read whether the current state is "✅ Official Pristine", "⚡ Mod Applied", or "⚠️ Mod Invalidated Due to Major Game Update", realizing a highly flexible manual repair and seamless transfer mechanism.

### 19. `of_card_asset` Registry Binary Reconstruction & Incremental Merging
The whitelist for stereoscopic Over-Frame card arts is stored in the `of_card_asset` file. This tool loads it as a TextAsset and implements an absolutely safe modification mechanism:
* **Unpacking**: Uses `struct.unpack("<HH", ...)` to unpack the script byte stream in groups of 4 bytes into two little-endian 16-bit unsigned short integers (Trigger ID and Target ID).
* **Incremental Diff**: Every time the registry is read, the system looks for a pure `.pristine` original backup in the cache directory. Using Python dictionary comprehension to compare the two, it precisely extracts "the difference set composed purely of custom modifications by the player".
* **Conflict Interception & Writing**: When writing a new registration list, the system compares the target IDs entered by the player. If it encounters official special placeholders (pointing to 0) or logical contradictions where the same item points to different targets, it triggers a safe interruption. Upon passing validation, the difference set is merged with the latest official baseline, repacked into a binary stream via `struct.pack("<HH")`, and written back into the asset. This technology ensures that even if the game undergoes a major version update, the Over-Frame whitelist painstakingly built by the player can be seamlessly transferred across versions.
* **Cross-Generation Survival System (Three-Stage Major Update Defense)**: When an unannounced major official update causes the old Hash to fail, the system activates `task_auto_repair_gate` to perform a three-stage rescue:
  1. **Historical Fast Track**: Reads `hash_history.json` to attempt blind testing with previously successful Hashes, achieving O(1) light-speed localization.
  2. **FAST Brute-Force**: Initiates multi-process scanning; the moment any core discovers the `of_card_asset` signature, it immediately uses IPC to send a `stop_event`, instantly halting I/O scanning for all other cores.
  3. **Auto Extraction & Injection**: After finding the latest official file, the system calculates `user_diff` (extracting all the player's past custom registrations) in the background, and seamlessly injects them incrementally into the new official file.

---

## Virtual Mount Transactions & Safe Rollback Mechanisms

The Virtual Mod Manager utilizes Windows Symbolic Link (Symlink) technology, aiming to achieve real-time mod application and testing with zero hard drive space occupation.

### 20. Symbolic Link Transaction Defense & Pre-flight Check
Before creating soft links (Symlink), to prevent "half-mounted" crippled states caused by insufficient permissions or file locks mid-process, the tool implements strict Atomic Transactions:
* **Pre-flight Check**: Before executing any modifications, the system pre-emptively conducts `os.access(target_dir, os.W_OK)` simulated permission tests on all target paths. Ensuring "either it all succeeds, or it's rejected from the start".
* **Global Rollback**: The program records the trajectory in real-time in `symlink_state.json`. If a system exception is encountered during creation, the rollback engine immediately intervenes, forcibly unlinking already created ghost links (`os.unlink`) and restoring backups, ensuring the game folder structure leaves no broken fragments.

### 21. Smart Longest Prefix Match & Boundary Check
To allow users to customize more recognizable image file names, this tool discards the rigid `split('_')[0]` and implements Longest Prefix Matching.
* **Boundary Defense Barrier**: If the dictionary has Card IDs `123` and `12345`, and the user imports `12345_AltArt.png`, to prevent the program from mistakenly identifying it as `123` appended with `45_AltArt`, the algorithm enforces strict boundary validation (`is_valid_match`): The first character following the matched string **must** be a legal separator (underscore, hyphen, dot, space) or the end of the string, completely cutting off false-positive filename parsing.

---

## Static Analysis & Dynamic Multi-Language Extraction

To provide comprehensive internationalization (i18n) support without increasing maintenance costs, this project implements Abstract Syntax Tree (AST) analysis.

### 22. AST Abstract Syntax Tree Static String Extraction
This tool utilizes Python's `ast` module to perform Static Analysis on the source code, constructing an abstract syntax tree without actually executing the code.
The algorithm traverses all `ast.Call` (call nodes) and `ast.keyword` (keyword argument nodes), accurately extracting all plaintext strings wrapped in `_("...")`, inside `placeholder="..."` watermarks, and definitions within the `DEFAULT_TABS` dictionary on the sidebar. Subsequently, the algorithm automatically compares keys with the `zh-tw.json` in the Languages directory, retains the translation content already manually adjusted by players, incrementally appends new sentences added in the code, re-sorts the dictionary, and writes it back to JSON, achieving zero-manual-intervention high-automation multi-language dictionary iterations.

---

## Developer & Build Environment Compatibility Support

### 23. PyInstaller FMOD Dynamic Virtualization (Mocking)
When compiling and packing the project into a standalone Windows executable (EXE), native game engine FMOD audio module dependencies (like `fmod_toolkit`, `pyfmodex`) often cause the compiled program to throw an `ImportError` crash at launch due to missing underlying C++ runtime dynamic link libraries (DLL) in the build environment.
To lift this underlying dependency restriction, the tool defines a `MockModule` class (inheriting from `types.ModuleType`) at the very top level of the program. Before the Python interpreter attempts to load other modules, it intercepts via the `__getattr__` magic method, returning an empty anonymous function (`lambda *args, **kwargs: None`), and dynamically Mock-overwrites all interfaces of FMOD in the `sys.modules` dictionary. This virtualization technique perfectly eliminates physical DLL dependencies during packaging, ensuring the lightweight and portable nature of the toolset.

### 24. Qt Low-Level Event Hijacking & Decimal Scroll Accumulator (Event Hijacking)
Addressing issues like stiff handling, inertial oscillation, and scroll wheel penetration when dragging built-in Qt components, this project implements a hacker-level Event Filter:
* **Decimal Scroll Accumulator (`scroll_accumulator`)**: Physical displacements calculated by mouse dragging lists are often decimals (e.g., 0.4 px), but Qt scrollbars only accept integers, causing the interface to freeze during fine-tuning. The filter temporarily stores decimals in a bucket; when accumulated beyond 1.0, an integer is extracted and given to Qt for scrolling, while the remaining decimal is kept. This achieves a web-level stop-on-a-dime, ultra-smooth fine-tuning feel.
* **Global Scroll Wheel Absorption (`prevent_scroll_propagation`)**: When a sub-list scrolls to the bottom, the native Qt scroll wheel event "penetrates" to the parent window, causing the entire UI to jump. The program completely absorbs the momentum by overriding `wheelEvent` and calling `event.accept()`, severing the transmission of UI oscillation.

### 25. Non-Destructive Mapping of Sandbox Visualization
After performing sandbox culling in the Graphical Gallery (Tab 12) and bringing the results back to the extraction list, the program does not directly overwrite the text box, but employs non-destructive mapping (`apply_visual_filter_result`). The system breaks down and compares the original list; if an ID was not deleted, it is preserved entirely "along with the player's handwritten annotations and formatting." This ensures that remarks painstakingly marked by players are not lost due to visualization filtering.

---

### Directory Structure Explanation
* `MD_AstellarTool.py`: Main program entry point and interface logic.
* `requirements.txt`: Python dependency list.
* `MD_Tool_Essential/`: Static resource directory.
  * `Languages/`: Stores multi-language JSON files exported via AST and customized by users.
  * `CardFrame/`: Stores PSD templates used for Over-Frame rendering and PNG fallback images used for degradation.

---

## Special Thanks

The establishment and perfection of an open-source project rely heavily on the selfless sharing and research of community seniors. Special thanks to the following contributors and communities:

* **TranLinhVy**: Special thanks to NexusMods creator [TranLinhVy](https://www.nexusmods.com/profile/TLVv) for their excellent work and technical inspiration, which immensely aided the development of this project.
* **Master Duel Datamining & Modding Community**: Salutes to all researchers who have contributed to the asset unpacking, database analysis, and tool development of *Yu-Gi-Oh! Master Duel*. MD AstellarTool was born because of your dedication to underlying technology and selfless sharing.

### Developer Information
* Author Pixiv: [LonelyMaJo](https://www.pixiv.net/users/126514098)