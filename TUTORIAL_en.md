[Traditional Chinese](TUTORIAL.md) | [English](TUTORIAL_en.md)

***

# MD AstellarTool Engineering Operations and Technical Depth Manual

This manual is the complete engineering specification and technical usage guide for "MD AstellarTool". This document uses no exaggerated terminology or emojis and aims to accurately, deeply, and rigorously reveal the underlying operational mechanisms, image algorithms, memory management strategies, binary data flows, and safety protection architecture of this tool.

Users will be able to understand the physical significance of every input parameter, the system-level behaviors triggered behind all buttons and switches, the operational steps of individual tabs, and practical cross-module workflow combinations through this document.

---

## Chapter 1: System Paths and Resource Naming Specifications

The tool's batch automation engine highly depends on accurate path mounting and Regular Expression (Regex) extraction of filenames. Before starting usage, ensure compliance with the following specifications.

### 1.1 Core Physical Path Definitions
* **Game 0000 Directory**
  The root directory storing the game's core cards and main asset binary AssetBundles.
  Default path format: `[Drive]:\SteamLibrary\steamapps\common\Yu-Gi-Oh! Master Duel\LocalData\[8-digit player ID]\0000\`
* **Game StreamingAssets Directory**
  The directory storing high-resolution materials or large data packages.
  Default path format: `[Drive]:\SteamLibrary\steamapps\common\Yu-Gi-Oh! Master Duel\masterduel_Data\StreamingAssets\AssetBundle\`
* **Lobby Background Data File**
  A single binary package file storing interface resources including the lobby background texture `ShopBGBase02`.
  Default path format: `[Drive]:\SteamLibrary\steamapps\common\Yu-Gi-Oh! Master Duel\masterduel_Data\data.unity3d`

### 1.2 Resource Naming & Normalized Parsing Mechanism
When encapsulating binaries or matching against the database, the tool strips user-customized suffixes using Python's `re` module.

* **Card Image File Naming Conventions**
  * **Rule**: `[Card ID]_[Any Custom Tag].[Extension]` or `[Card ID].[Extension]`
  * **Underlying Mechanism**: The tool uses `^([a-zA-Z]*)(\d+)(.*)$` for extraction. The system ignores leading alphabetical letters, forcibly locks onto the "continuous block of numbers" in the string as the Card ID, and treats all subsequent characters (including underscores, spaces, etc.) as invalid suffixes and strips them.
  * **Correct Examples**: `20570.png`, `20570_Aluber.png`, `Alt17069_CustomArt.jpg`.
  * **Incorrect Example**: `Aluber_20570.png` (The parser cannot capture numbers at the start of the string, leading to a match failure).
* **Non-Card Visual Assets (UI / Field / Protector)**
  * **Rule**: Must exactly match the reference table name extracted from the game verbatim (case-insensitive).
  * **Underlying Mechanism**: The tool uses `unicodedata.normalize('NFKC', text).lower()` for bidirectional assimilation matching, eliminating full/half-width and case differences.
  * **Examples**: `Mat_001_BaseColor.png`, `ProfileIcon1020001.png`.

---

## Chapter 2: Full Interface Tab Function Breakdown and Single-Page SOPs

This chapter dissects the UI components, input boxes, switches, buttons, and operational SOPs for all tabs, following the default software interface order.

---

### 1. Settings & Appearance (Tab 7, `t7_settings`) [Primary Configuration Page]

<img width="1095" height="847" alt="設定" src="https://github.com/user-attachments/assets/c87beb83-5276-48bf-b9c5-3f5c7a3ef661" />

#### Technical Mechanism & Operational Principle
This module is the tool's global configuration hub, responsible for reading and writing JSON config files, dispatching Cross-Tab Path Synchronization signals, and dynamic QSS stylesheet rendering.
* **Atomic Writing and RLock Thread Locks (`_atomic_write_json`)**: When clicking to write settings, the system first locks the thread using `threading.RLock()`, solving Deadlocks caused by multi-thread simultaneous save triggers. It then writes a clean dictionary to a `.tmp` temp file, and finally uses `os.replace` for physical atomic replacement, ensuring the config file won't corrupt into a 0KB file even in a power outage.
* **URI Scheme Smart Path Sanitization (`clean_path`)**: All path input fields have built-in fool-proof sanitization. If a user drags in a URL format with `file://` or `//localhost/` from a browser or elsewhere, the system automatically strips the prefix and normalizes it to standard Windows paths.
* **Global Scroll Wheel Nullification (`block_wheelEvent`)**: Forcibly absorbs all scroll wheel events for dropdown menus and number spin-boxes, preventing users from unintentionally altering core settings due to accidental cursor placement while scrolling down a long page.
* **AST Abstract Syntax Tree Source Code Parser (`task_generate_translation_template`)**: Once initiated, it invokes the Python `ast` module, traverses the main program's source code, grabs all strings wrapped in `_("...")` and UI `placeholder` tags, automatically generates the `MD_Tool_Essential/Languages/raw.json` locale template, and losslessly fills in any missing items in `zh-tw.json`.

#### Full UI Components and Input Fields Detail
* **Cross-Tab Path Synchronization (Checkbox)**: When enabled, modifying the "Project Root Directory", "0000 Source", or "CSV Dictionary" paths on any page will broadcast updates to corresponding input boxes across all pages via ConfigSignals.
* **Auto-Switch Tab After Completion (Checkbox)**: When enabled, the system will automatically jump to the next corresponding processing page upon completion of a single task.
* **Language (Requires Restart) (ComboBox)**: Sets the interface language (default `zh-tw`, `en-us`). You can freely input other language codes manually (e.g., `ja-jp`), and the system will automatically attempt to read `Languages/[Code].json`.
* **Max Compute Power (Threads) (ComboBox)**: Sets the number of CPU cores for the multi-process pool (`ProcessPoolExecutor`). You can enter a number or set it to `Auto`. When `Auto`, the system automatically reserves 1 to 4 cores for OS operations, preventing 100% CPU usage from freezing the UI.
* **Specific Font (ComboBox)**: Chooses the interface display font.
* **Custom 5-Dimension Color Palette (Buttons)**: Provides 5 color blocks: "Accent Color", "Background Color", "Text Color", "Sidebar Background Color", "Border Color". Clicking opens `QColorDialog`, supports Alpha channel color picking, and instantly rebuilds the QSS stylesheet to apply to the whole window.
* **Global Project Folder Naming Settings (LineEdits)**: Sets the default names for "Raw Files", "Raw Card Art", "File Backups", "Card Art Mod", "Modified Files", and "CSV Dictionary" folders.
* **Sidebar Tab Sorting & Renaming (ListWidget & LineEdit)**: Lists all tabs. Select an item and use [▲], [▼] buttons to adjust sidebar order, or enter a new name in the input box and click [Rename].
* **Background Image (Path Row)**: Sets a local image as the GUI background.
* **Transparency (Slider)**: Adjusts UI semi-transparency (0 to 100%).
* **Brightness (Slider)**: Adjusts background image brightness (10 to 200%).
* **3x3 Grid Anchor (LinkAnchorPicker)**: Provides 9-grid position selection to determine the fixed anchor point of the background image during window resizing.

#### Button Functions Detail
* **[Write JSON Config (Save All Changes)]** (One at the top, one at the bottom): Saves current settings to `md_tool_config.json`.
* **[Export Translation Template (raw.json)]**: Executes AST parsing to output a locale template file.

#### Single-Page SOP and Path Saving Specifications
1. In "Global Project Folder Naming Settings", verify that folder names match your workflow habits.
2. **Important Path Saving Specs**: When clicking [Write JSON Config], the system records all input boxes on the interface. To avoid writing one-off temporary project paths into global settings, please clear temporary project sub-directories entered in other tabs before saving, retaining only the "0000 Game Directory", "Main CSV Dictionary Path", and "Default Folder Names".
3. Click **[Write JSON Config (Save All Changes)]**. Next time you open the tool, temporary fields will remain blank, making it easy to directly paste a new project path.

---

### 2. Beginner's Guide & Operation Journey (Tab 0, `t0_guide`)

#### Technical Mechanism & Operational Principle
This module is a static information display page utilizing a read-only `QPlainTextEdit` to render system guides and statements, consuming no system compute resources.

#### UI Components & Operation
* Built-in full instructional text where users can browse standard project workflows, quick pipelines, and the function introductions of each tab.

---

### 3. Bruteforce Scan & Append (Tab 1, `t1_scan`)

<img width="1093" height="844" alt="爆搜" src="https://github.com/user-attachments/assets/9b6cfa84-eaf0-4183-8976-28b62c36321a" />

#### Technical Mechanism & Operational Principle
This module is responsible for traversing binary files under the 0000 directory to build a relational CSV dictionary of Card IDs, true names, effect texts, and Hash encodings.
* **XOR Dynamic Cracking Engine**: The official encrypts the card text library. The system defaults to using `0x3D (61)` for XOR bit inversion. If an official update causes decryption to fail, the engine triggers the `auto_crack_key` function, brute-forcing a loop from 0 to 1023, decompresses and validates the zlib package structure, and upon success automatically captures the new key and writes it back to the config.
* **6-bit Physical Masking Evaluation**: For property reading, the engine directly reads the `card_prop.bytes` binary shift. If the bit value is `0x020D`, it's identified as a Spell card; for Monster cards, it extracts the first 6 bits (6-bit mask) to compare physical signature codes (e.g., `0x19`, `0x24` corresponding to Pendulum), supplemented by NLP effect text keyword scanning to achieve precise card classification.
* **IL2CPP Metadata Collision**: For accessory assets without Card IDs (e.g., Icons, Fields), reads `global-metadata.dat` to extract ID strings, calculates CRC32 hashes, and performs a two-way collision comparison with `ids_item.bytes` to restore names.
* **Memory Failsafe Monitoring & 30-Second Tolerance (`check_memory_limit`)**: Invokes Windows APIs to monitor physical memory. When the load reaches the 85% threshold, it forcibly sleeps and waits for GC. If memory doesn't drop after 30 seconds, the system forcibly releases the lock, preventing the failsafe from causing a permanent program deadlock.
* **Dual-Track CSV Header Fault-Tolerant Parsing (`find_lang_column_index`)**: Reads CSV using `strict=False` loose assimilation, compatible as long as the header contains "名" or "Name"; however, when executing "Append/Expand" on this tab, it forcibly switches to `strict=True` strict mode. If there's no standard language header, it automatically expands a new column to the right and absolutely never overwrites old data.
* **Exceptional Card Debug Report (`generate_exception_report`)**: After scanning, for abnormal cards in the database whose properties cannot be parsed, it automatically generates a `Unknown_Cards_Report.json` (for developers) and an `Exception_IDs_List.txt` (for users) dual report in the output directory.

#### Full UI Components and 10 Major Switches Detail
* **Target Folder (0000)**: Specifies the game's 0000 folder path.
* **Save Root Directory**: Project output location; all subsequent operations are based on this.
* **TXT / CSV Naming (LineEdits)**: Sets output list and dictionary filenames.
* **1. Enable Size Filter (Checkbox, `t1_size_filter`)**:
  * **ON**: Limits scanning to Bundle files whose sizes are within the "Min (KB)" and "Max (KB)" range, bypassing irrelevant micro-files and giant files.
  * **OFF**: Indiscriminately scans all Bundle files in the target directory.
* **2. Scan Only Cards (Checkbox, `t1_only_numbers`)**:
  * **ON**: Only extracts pure number ID card assets, ignoring accessories with English letters like fields and protectors.
  * **OFF**: Extracts both pure number cards and English-letter accessory assets.
* **3. Generate Content List (TXT) (Checkbox, `t1_gen_txt`)**:
  * **ON**: Automatically generates a TXT list containing all IDs.
  * **OFF**: Does not generate a TXT list.
* **4. Generate Mapping Table (CSV) (Checkbox, `t1_gen_csv`)**:
  * **ON**: Automatically exports the main CSV dictionary containing directories, Containers, Hashes, and IDs.
  * **OFF**: Does not export a CSV mapping table (Used when reverse exporting TXT from modified directories).
* **5. Include Card Names (Checkbox, `t1_ext_name`)**:
  * **ON**: Writes card names in the specified language to the CSV.
  * **OFF**: CSV does not write card names.
* **6. Include Card Effects (Checkbox, `t1_ext_desc`)**:
  * **ON**: Writes card effect text to the CSV, handy for searching by effect keywords later.
  * **OFF**: CSV does not write effect text, greatly reducing CSV size and speeding up read times.
* **7. Parse Accessory Names (Checkbox, `t1_parse_meta`)**:
  * **ON**: Reads `global-metadata.dat` to restore names of accessories like Protectors and Icons.
  * **OFF**: Does not parse Metadata; accessories show original codes.
* **8. Use Cache First (Checkbox, `t1_use_cache`)**:
  * **ON**: Reads temporary files left from previous decryptions in `MD_Tool_Temp/`, achieving second-level scanning.
  * **OFF**: Forcibly re-decrypts game Bundles. MUST be turned OFF after a major game update to acquire new data.
* **9. Deep Scan (Checkbox, `t1_deep_scan`)**:
  * **ON**: Deeply unpacks all objects inside Bundles, extracting field textures or lobby backgrounds hidden within massive asset packages.
  * **OFF**: Only matches top-level Container paths; scanning speed is extremely fast.
* **10. Process Only Fields/Protectors/Icons, etc. (Checkbox, `enable_visual_only_filter`)**:
  * **ON**: Filters out pure number regular cards; scan results only keep accessory assets.
  * **OFF**: Scans all assets by regular rules.
* **Language (ComboBox) / XOR Key (LineEdit)**: Decryption language and key.
* **CSV to Expand (Path Row)**: Path to an old CSV used for the Append function.

#### Button Functions Detail
* **[Start Scan]**: Initiates multi-process scanning, generating a TXT list and CSV dictionary upon completion.
* **[Execute Append / Expand]**: Reads the "CSV to Expand", appending the new language column to the right of the CSV.
* **[Stop Bruteforce / Abort Job]**: Sends `multiprocessing.Event()` as a `stop_event` signal. Subprocesses immediately `break` early out of the `os.walk` recursion or decryption loop upon receiving the signal, safely release memory, and exit, completely avoiding Zombie Processes left by abruptly killing tasks.

#### Single-Page SOP
* **SOP 1.1: Full Game 0000 Directory Scan**
  1. Fill in "Target Folder (0000)" and "Save Root Directory".
  2. Check "Generate Mapping Table (CSV)", "Include Card Names", "Parse Accessory Names".
  3. Click **[Start Scan]**. Upon completion, `2DTexture_Mapping.csv` is produced in the root directory.
* **SOP 1.2: Expanding an Old CSV Multi-Language Mapping Table**
  1. Select previously created CSV in "CSV to Expand".
  2. Switch "Language" to the target new language (e.g., `ja-jp`).
  3. Click **[Execute Append / Expand]**. The system automatically appends the new language column and saves.

---

### 4. Find Files (Tab 2, `t2_find`)

<img width="1096" height="842" alt="找出" src="https://github.com/user-attachments/assets/3f22366e-02d1-465c-a389-159fdeea75b0" />

#### Technical Mechanism & Operational Principle
Accurately finds and copies target binary Hash files from the 0000 directory based on the CSV dictionary.
* **Google-like Advanced Tokenization Search Engine (`search_cards_advanced`)**: The system has a built-in high-performance memory retrieval matrix supporting boolean logic and precise affix filtering. You can use the following syntax in the search box:
  * **Space separation**: Treated as `AND` logic, must satisfy all keywords simultaneously.
  * **Quote lock (`"keyword"`)**: Forcibly strict matches the complete phrase inside quotes, no tokenization.
  * **Mandatory inclusion (`+keyword`)**: The target must contain this keyword (card name or effect).
  * **Mandatory exclusion (`-keyword`)**: If the target contains this keyword, it's directly culled (e.g., excluding specific archetypes).
* **Matrix Property Filtering (Matrix Filter)**: By parsing the 6-bit physical mask of `card_prop.bytes`, it provides precise cross-matching of 18 sub-properties across three main categories (Monster, Spell, Trap).
* **Inertial-less Linear Scrolling (`LinearDragScrollFilter`)**: Injects an underlying EventFilter, converting mouse drags into decimal step accumulations, realizing web-level stop-on-a-dime scrolling, completely eliminating Qt's default oscillation and bounce back.
* **Dynamic Memory Pagination Slicing**: Search results support instant 0ms rendering slices from 50 items to infinity per page, preventing thread freezes caused by writing tens of thousands of data entries to the UI simultaneously.

#### Full UI Components and Input Fields Detail
* **Select Mode (ComboBox)**:
  * `MODE_NORMAL` (Standard Extraction): Purely copies Hash files to the "Raw Files" folder.
  * `MODE_QUICK` (Quick Over-Frame Switch): Activates a fully automated Over-Frame write pipeline. Important limitation: Quick Over-Frame mode only applies to official game card art. For custom art, please use Tab 8.
* **Language & Search Box (ComboBox & LineEdit)**: Sets search target language. Search box supports the advanced syntax mentioned above.
* **Collapsible Filter Panel (Filter Panel)**:
  * **Monster Area**: Provides Effect, Normal, Fusion, Synchro, Xyz, Link, Ritual, Pendulum, Token, etc., physical card type filtering.
  * **Spell Area**: Provides Normal, Quick-Play, Continuous, Field, Equip, Ritual filtering.
  * **Trap Area**: Provides Normal, Counter, Continuous filtering.
  * **Auxiliary & Advanced Area**: Contains "Process Only Fields/Protectors/Icons" switch, Fuzzy match tolerance switches for card names and effects (Algorithm based on SequenceMatcher sliding window), and items-per-page limit settings.
* **Dictionary (CSV) / TXT to Load / File Source (0000) / Save Root Directory (Path Rows)**: Set read/write paths for each stage. If paths do not refresh instantly, click the spacebar inside the input box and delete it to force an update.
* **New Folder Name (LineEdit)**: The name of the folder storing the copied binary files (default `Raw Files`).
* **Pagination Navigation Bar (Navigation Bar)**: Provides previous/next page switching, and "Add All Current Page" and "Add All Search Results" batch write buttons.
* **Search Results List (ListWidget) / Extraction List (PlainTextEdit)**: Displays searched items and the final ID list to be extracted.

#### Button Functions Detail
* **[Start Extracting Raw Files] / [Start Auto Over-Frame Mod]** (Top and bottom): Executes file copying or starts the automated Over-Frame pipeline.
* **[Load TXT]**: Loads IDs from an external text file into the Extraction List.
* **[Normalize Names]**: Looks up the CSV dictionary, reformatting IDs in the text box into `ID (Name) [Hash]` format.
* **[Visual Sandbox Filter]**: Initiates sandbox mode, sending IDs from the Extraction List to Tab 12 to generate image caches for manual visual culling.
* **[Confirm IDs & Return to Over-Frame Register]**: (Linked display) Carries the IDs in the list and jumps back to Tab 13.
* **Double Click & Right Click on List**: Double-clicking a search result item, or highlighting and right-clicking, quickly adds the item to the Extraction List.

#### Single-Page SOP
* **SOP 2.1: Standard Raw File Extraction**
  1. Ensure the mode is "Standard Extraction".
  2. Expand the "Filter" panel to set card types, or use advanced syntax in the search box (e.g., `"Albaz" -Fusion`).
  3. Double click items in the results list, or click "Add All Current Page" on the pagination bar to send IDs to the Extraction List.
  4. Click **[Start Extracting Raw Files]**. Target binary files are copied to `Project Directory/Raw Files/`.
* **SOP 2.2: Official Card Art Quick Over-Frame Full Automation**
  1. Switch Mode to "Quick Over-Frame Switch".
  2. Enter official Card IDs into the Extraction List.
  3. Click **[Start Auto Over-Frame Mod]**.
  4. Internal pipelines automatically execute in sequence: Extract Raw Files -> Unpack Original Art & Backup Bundle -> Copy Image -> Execute 11:16 Crop & PSD Frame Synthesis -> Write Back to Bundle -> Bring Card IDs to Tab 13 Register.
* **🎯 System Large File Targeted Extraction Defense (`Data_Unity3d_Targets.txt`)**
  When your search results contain system large files like `data.unity3d` or `StreamingAssets` that are hundreds of MBs, clicking [Start Extracting Raw Files] will **not** directly copy these giant files. The system intelligently intercepts this, and generates a `Data_Unity3d_Targets.txt` targeted list in the project root directory and hands it to Tab 3, thereby avoiding hard drive I/O explosions and invalid file copying.
---

### 5. Extract Data (Tab 3, `t3_extract`)

<img width="1076" height="842" alt="提取" src="https://github.com/user-attachments/assets/91e4e574-9103-4825-9c8a-2a18666cf79e" />

#### Technical Mechanism & Operational Principle
Uses UnityPy to unpack Bundles, exporting `Texture2D` (images) and `TextAsset` (text descriptions).
* **Area Protection Mechanism**: Compares pixel total area before writing images `(w * h) <= (ext_img.w * ext_img.h)`. If the unpacked resolution is smaller than the existing hard drive file, it abandons writing, protecting already modified high-resolution images.
* **Strict Blacklist/Whitelist Filtering (`is_valuable_texture`)**: Built-in extremely strict blacklist (blocks `_normal`, `_metallic`, `lightmap`, `_ao` 3D rendering textures) and whitelist (allows `basecolor`, `coin`, `deck`, `profileicon`, etc.), ensuring only meaningful visual assets are exported.
* **0000 Root Directory Failsafe Barrier**: If it detects the user selected the game's original `0000` root folder as the source, the system pops up a severe warning and forcibly blocks it, preventing the program from unpacking tens of GBs of game resources at once and paralyzing the computer.

#### Full UI Components and Input Fields Detail
* **Folder containing files to extract (Path Row)**: Specifies the input path (usually points to `Raw Files`).
* **Export CSV / Export Images / Export Text Data / Backup Files (Checkboxes)**: Controls unpack export items.
* **Process Only Fields/Protectors/Icons, etc. (Checkbox)**: Filters non-card assets.
* **Image Folder Name (LineEdit)**: Export directory for images (default `Raw Card Art`).

#### Button Functions Detail
* **[Start Extracting Contents]**: Starts multi-process unpacking. Images are written to `Raw Card Art/`, original Bundles are copied to `File Backups/`.

#### Single-Page SOP: Unpack & Export
1. Ensure "Folder containing files to extract" points to `Project Directory/Raw Files`.
2. Check "Export Images" and "Backup Files".
3. Click **[Start Extracting Contents]**. Exported PNGs will be saved to `Project Directory/Raw Card Art/`.

---

### 6. Replace Artwork (Tab 4, `t4_replace`)

<img width="1093" height="845" alt="改圖" src="https://github.com/user-attachments/assets/da18dfc5-efeb-470a-904e-b9bb1584c97b" />

#### Technical Mechanism & Operational Principle
Re-stitches externally modified images back into binary Bundles.
* **Lanczos Resampling (`MODE_FIT_VISUAL`)**: If it's a non-card UI asset, the system forcibly applies the Lanczos algorithm to scale it strictly identical to official specs, preventing UI artifacting.
* **Color Space Correction**: For Spine animation textures (`p[Number]`), forcibly sets `m_ColorSpace` to `0` (Gamma Space) upon writing, eliminating neon color shifts.
* **Atomic Writing**: Writes to `.tmp` then physically replaces via `os.replace`, preventing 0KB corrupted files from power outages.

#### Full UI Components and Input Fields Detail
* **Dictionary (CSV) / Project Root Directory Location (Path Rows)**: Global read/write paths.
* **Backup Location (LineEdit)**: Directory storing unmodified Bundles (default `File Backups`).
* **Mod Art Location (LineEdit)**: Directory storing modified PNG/JPGs (default `Card Art Mod`).

#### Button Functions Detail
* **[Start Replacement]**: Reads images from "Card Art Mod", writes them back to the corresponding Bundles in "File Backups", and saves outputs to `Modified Files/`.

#### System Large File Exclusive Management (data.unity3d State Machine)
To combat modification risks for hundreds-of-MBs large files, the system established a completely independent management ecosystem for `data.unity3d`:
* **Tri-State UI Smart Identification**: Reads the history file `MD_Tool_Temp/data_unity3d_workspace/data_mod_manifest.json`. By comparing file sizes and modification times between the official pure version (`pristine`) and the last injected state (`last_injected`), the UI accurately displays whether the current status is: "✅ Official Pristine", "⚡ Mod Applied", or "⚠️ Mod Invalidated Due to Major Game Update".
* **Atomic Replacement & Forced GC (`task_batch_replace_data_unity3d`)**: When writing large files, it strictly uses `.tmp` atomic replacement. After `env.file.save()`, it consecutively calls `gc.collect()` twice, instantly purging the massive buffers left by UnityPy in RAM, completely eradicating OOM crashes.

#### Single-Page SOP: Write Image Back to Bundle
1. Name your modified image `[Card ID].png` and place it in `Project Directory/Card Art Mod/`.
2. Ensure Backup Location points to `File Backups`.
3. Click **[Start Replacement]**. Modified Bundles will be generated in `Project Directory/Modified Files/`.

---

### 7. Package Mod (Tab 5, `t5_package`)

<img width="1089" height="843" alt="打包" src="https://github.com/user-attachments/assets/3fa4427a-a506-4be0-b216-30cd440d5573" />

#### Technical Mechanism & Operational Principle
Reconstructs modified Bundles strictly according to the Master Duel official file system directory specifications.
* **Hash Directory Segmentation**: Based on the CSV table, if it's a `0000` resource, it automatically extracts the first two characters of the Hash code (e.g., `a589...` -> `a5`), creates an `0000/a5/` subdirectory, and moves the file inside.

#### Full UI Components and Input Fields Detail
* **Dictionary (CSV) / Project Root Directory (Path Rows)**: Read/write paths.
* **Folder Naming (LineEdit)**: Output mod directory name (default `ModFolder`).
* **Include "Card Art Mod" / Include ReadMe.txt / Compress into ZIP (Checkboxes)**: Packaging controls.
* **ReadMe Default Text (PlainTextEdit)**: Custom instructions text.

#### Button Functions Detail
* **[Start Packaging]**: Builds structure, copies files, and executes ZIP compression.

#### Single-Page SOP: Package for Release
1. Set "Folder Naming", and check "Compress into ZIP".
2. Click **[Start Packaging]**. A mod compressed file ready for release will be generated in the root directory.

---

### 8. Smart Chain Execution (Tab 6, `t6_chain`)

<img width="1097" height="847" alt="串聯" src="https://github.com/user-attachments/assets/e7c4eb7d-f103-42f6-bb21-b08d96276016" />

#### Technical Mechanism & Operational Principle
Implements an asynchronous Callback Queue queue-driven system, automating multiple steps unattended.

#### Full UI Components and Buttons
* Checkboxes: [2] Find Files, [3] Extract Data, [8] Pendulum Post-Processing, [4] Replace Artwork, [5] Package Mod.
* **[▶ Start Automated Task]**: Executes checked tasks sequentially.

#### Single-Page SOP: One-Click Automation
1. Ensure paths and settings on relevant tabs are completely filled out.
2. Check desired steps (e.g., [2], [3], [4], [5]).
3. Click **[▶ Start Automated Task]**.

---

### 9. Pendulum & Over-Frame Art Post-Processing (Tab 8, `t8_pendulum`)

<img width="1095" height="853" alt="後處理" src="https://github.com/user-attachments/assets/59a8b6b5-fd86-4b94-ab31-a6a1a9eb0c65" />

#### Technical Mechanism & Operational Principle
This module is the core image processing hub of the tool, providing 4 major processing pipelines and a highly flexible layer rendering pipeline:
1. **Pendulum Post-Processing (`MODE_PENDULUM`)**: Fills the bottom of the image with a transparent background (based on `pad_pct` ratio), correcting the square stretching distortion of Pendulum artworks in-game.
2. **Over-Frame Art Post-Processing (`MODE_OVERFRAME`)**:
   * **Single Layer Refinement & Dual Layer Synthesis (-ch / -bg logic)**: If input images are named `[ID]-ch.png` (Character Layer) and `[ID]-bg.png` (Background Layer), the system automatically launches the advanced Dual-Layer Studio, allowing independent adjustment of X/Y translation, scaling, and rotation for both Character and Background. If a normal single image is provided, it automatically performs an 11:16 full-bleed crop.
   * **Dynamic Z-Order Geometric Synthesis**: Reads `CardFrame/` PSD files, allowing users to customize the top-bottom stacking order of 8 major layers (Character, Background, Outer Frame, Card Name Box, Art Frame, Effect Frame, Effect Text Box, Card Back Background).
   * **Foil Shader & Mask Generation Matrix (Foil Studio)**: Built-in IQ Cosine Palette modulation and dual-track blending system (Pegtop Soft Blend / Vivid Overdrive), providing Pearl Pastel, Neon Spectrum, Champagne Gold, and Platinum Diamond optical simulations. Independently controls Preview simulation, physical bake (Bake), and transparent punch-hole (Dirty Alpha) for each component.
3. **Cut-In Animation Post-Processing (`MODE_CUTIN`)**: Reads PSD, MP4, GIF, or static images.
   * **Regex Protection Lock & PMA Premultiplication**: Strictly verifies if the passed filename matches `p+Number` and has `-hd` / `-sd` tags (`parse_cutin_tag_and_base`). Forcibly executes PMA pixel premultiplication before export, and adds a `padding_val = 2` 2-pixel anti-bleed pad, completely eliminating black edges caused by Unity bilinear filtering.
   * **Viewport Sinking Evasion (`build_spine_42_json_text`)**: When generating skeletons, apart from converting pixel offsets to world scales, it forcibly depresses the skeleton `y` coordinate from the factory `-1350.0` down to `-1470.0`, perfectly evading the top UI cropping boundary in the battle screen.
4. **Pendulum Original Art Processing (`MODE_PENDULUM_ORIGINAL_CROP`)**: Applies a 1.25x horizontal stretch to the extracted distorted official image, and performs a 1:1 square crop from the top vertex to restore it.

#### Full UI Components and Input Fields Detail
* **Processing Mode (ComboBox)**: Switches between the 4 pipelines mentioned above.
* **Project & Path Settings Area**: Sets CSV dictionary, Project Root, Mod Art location, and Raw Card Art location. Includes Pendulum padding ratio and Backup Folder Name controls.
* **Over-Frame Element Transparency Controls (Sliders)**: Finely adjusts Alpha transparency (0~100%) for 6 major PSD components.
* **Foil Shader & Mask Settings (Foil Studio)**:
  * **3x6 Control Matrix**: Controls whether 6 components like Outer Frame and Card Name Box participate in "Preview Simulation", "Bake to Texture", and "Alpha 0 Mask".
  * **Optical Parameter Sliders**: Spectrum Style, Blending Mode, Pearl Base Luminance, High-Pass Focus (Sharpness), Gloss Intensity, Color Density, Fleck Frequency, and Light Angle.
* **Dual Real-Time Preview Panel (Dual Canvas Preview)**: Provides single-frame memory light-speed extraction previews. The interface is forcibly split into left and right dual views:
  * **Left Side (In-Game Simulation)**: Forcibly pads transparent backgrounds and overlays Foil shaders, truly reflecting the complete state before entering the game's 3D shaders.
  * **Right Side (Actual Output Image)**: Applies the program's self-drawn transparent checkerboard base, accurately displaying the Alpha channel status after "Character Over-Frame Intersection Punch-Hole", What You See Is What You Get.
* **Advanced Dual-Layer Over-Frame Studio (Exclusive to -ch / -bg)**:
  * Provides independent X/Y translation, scaling, and rotation sliders for Character and Background layers.
  * A pure color baseplate can be customized via the color picker when there is no background.
  * **Layer Free Sorting Panel (Z-Order)**: Drag or use buttons to freely change the stacking order of 8 major layers.
* **Material & Canvas Settings Area (Exclusive to Cut-In Animation)**: Sets HD output resolution (1920x1080 / 1280x720), canvas fill mode (Crop / Fit / Stretch), rotation angle, and global X/Y translation. Checking "Enable Hard Drive Cache" prevents out-of-memory errors when processing long videos.
* **Keyframe Preview Time Control Area (Exclusive to Cut-In Animation)**: Preview time point fine-tuning slider, providing quick buttons to jump to Start, Peak, Settle, and End points.
* **Chroma Key & Color Modification Area (Exclusive to Cut-In Animation)**: Includes Chroma Key switch, Despill switch, Color Picker. Provides sliders for Key Tolerance, Edge Feathering, Despill Intensity, Brightness, Contrast, and Vignette Border Intensity.
* **Time Control & POP UP Effects Area (Exclusive to Cut-In Animation)**: Sets clip start, total animation duration, output Frame Rate (FPS), playback speed. Includes 4-point Spine scaling curve settings (Time and Size), and provides "Generate Full Size True Preview GIF" function.
* **Pending List (PlainTextEdit)**: Manually input or load IDs meeting criteria via "Auto Scan Target Directory". Clicking an ID in the list automatically loads the preview path.

#### Single-Page SOP
* **SOP 8.1: Pendulum Image Padding & Original Art Restoration**
  1. Select Mode "Pendulum Post-Processing" or "Pendulum Original Art Processing".
  2. Click **[Auto Scan Target Directory]** to load IDs.
  3. Click **[🚀 Start Execution Post-Processing]** to overwrite output.
* **SOP 8.2: Over-Frame Art Dual-Layer (-ch/-bg) Creation & Z-Order Adjustment**
  1. Name the keyed character `12345-ch.png`, the background `12345-bg.png`, and place them in the `Card Art Mod/` directory.
  2. Select Mode "Over-Frame Art Post-Processing", click **[Auto Scan Target Directory]**.
  3. Click an item in the list to expand the preview panel.
  4. Expand "Advanced Dual-Layer Over-Frame Studio", adjust character scale and translation, and drag the Z-Order panel to move "Effect Text Box (EffBox)" to the very bottom to hide it.
  5. Expand "Foil Shader & Mask Settings", check "Alpha 0 Mask" for Outer Frame and Art Frame to realize the stereoscopic effect of characters breaking the border.
  6. Click **[🚀 Start Execution Post-Processing]**, export synthesized images, and automatically jump to Tab 13.
* **SOP 8.3: Spine Cut-In Animation Chroma Key & Output**
  1. Select Mode "Cut-In Animation Post-Processing".
  2. Place a green screen video (e.g., `p18533.mp4`) into `Card Art Mod/`, click **[Auto Scan Target Directory]**.
  3. Click the ID in the text box to automatically load the preview, expand the preview panel.
  4. Check "Enable Chroma Key" and "Enable Despill", click **[🎨 Pick Key Color]** to pick the background green. Adjust Key Tolerance and Despill Intensity until character edges have no green glow.
  5. Set the 4-point POP UP scaling curve, click **[Generate Full Size True Preview GIF]** to confirm dynamic effects.
  6. Click **[🚀 Start Execution Post-Processing]**. The system executes PMA premultiplication and exports `-hd.png`, `-hd.atlas.txt`, `js-hd.json` along with corresponding SD atlases to `Card Art Mod/`.

---

### 10. Quick Single Card Mod (Tab 9, `t9_quick_mod`)

<img width="1095" height="848" alt="單卡" src="https://github.com/user-attachments/assets/d357a412-561b-413a-9225-cfda5ad694aa" />

#### Technical Mechanism & Operational Principle
Skips project creation, executing binary injections directly onto single files.
* **Lobby Background Overwrite (`MODE_LOBBY_BG`)**: Precisely targets the `ShopBGBase02` texture inside `masterduel_Data/data.unity3d`, executes binary injection, and calls `gc.collect()` to forcibly release memory.

#### Full UI Components and Input Fields Detail
* **Select Category (ComboBox)**: "Standard Mod", "Over-Frame Mod", "Modify Lobby Background".
* **Search & Select Area**: Language ComboBox, Search box, Process Only Fields/Protectors switch, Search list.
* **Dictionary (CSV) / Raw File Source (0000) / Save Root Directory / New Image Path (Path Rows)**: Read/write paths.
* **Target Card ID (LineEdit)**: Card ID to replace.
* **Directly Overwrite Game Files (Checkbox)**: Dangerous operation, directly modifies the 0000 source file.

#### Button Functions Detail
* **[Start Replacement]**: Executes single file injection.
* **[Send to Over-Frame Post-Processing]**: In Over-Frame mode, brings the path and ID to jump to Tab 8.

#### Single-Page SOP
* **SOP 9.1: Quick Single Card Replacement**
  1. Category select "Standard Mod".
  2. Search for a card in the search box, double click to bring ID to "Target Card ID".
  3. Select the replacement image in "New Image Path", click **[Start Replacement]**.
* **SOP 9.2: Lobby Background Overwrite**
  1. Category select "Modify Lobby Background".
  2. Set "Raw File Source (0000)" and "Save Root Directory".
  3. Select a high-res image in "New Image Path".
  4. Click **[Start Replacement]**. The modified `data.unity3d` is generated in `Modified Files/`.

---

### 11. Over-Frame Card Register (Tab 13, `t13_overframe`)

<img width="1092" height="845" alt="超框" src="https://github.com/user-attachments/assets/900b1745-7aa6-4d1e-8a13-690644eacbf2" />

#### Technical Mechanism & Operational Principle
Reads, decodes, and decides the `of_card_asset` registry for Over-Frame rendering.
* **Pure Baseline File (.pristine)**: Creates a read-only `.pristine` backup upon first reading. Future writing calculates the net difference strictly from "UI Content - pristine baseline", and then merges and handles conflicts with the latest official data.

#### Full UI Components and Input Fields Detail
* **Dictionary (CSV) / Game Raw File Source (0000) / Save Root Directory (Path Rows)**: Path settings.
* **Target Registry (Hash) (ComboBox)**: The Hash code of the current `of_card_asset`.
* **Registry to Merge (Path Row)**: External registry used for the merge function.
* **Existing Whitelist Read & Manage (Area 1 Textbox)**: Displays existing Over-Frame registered data inside the game.
* **New Registration & Writing (Area 2 Textbox)**: For inputting new Card IDs to register. Supports directly pasting formats extracted from Tab 2, or manual input (Syntax: `Trigger ID -> Target Base Image ID`. If no target base image, simply fill `Trigger ID`. System automatically ignores texts and comments starting with `#` or `=`).

#### Button Functions Detail (10 Major Buttons)
1. **[🛠️ Manual Bruteforce Fix (For After Major Updates)]**: Fights against unannounced official major game updates via a three-stage defense:
   - Line 1 (Historical Fast Track): Reads `hash_history.json` blind testing historical Hashes, achieving O(1) light-speed localization.
   - Line 2 (FAST Bruteforce): Initiates multi-process scanning; sends `stop_event` instantly upon discovering signatures, saving computing power.
   - Line 3 (Incremental Transfer): After locating the new official file, extracts player's `user_diff` in the background and seamlessly injects it.
2. **[📥 Read Existing Raw File]**: Decodes binary and displays it in Area 1.
3. **[🧹 Clear Cached Registry]**: Deletes the `.pristine` baseline file.
4. **[💾 Save Existing Whitelist]**: Only saves modifications from Area 1.
5. **[🔗 Merge with "Registry to Merge"]**: Merges an external registry and eliminates conflicts.
6. **[🔍 Go to "Find Files" to Pick Cards]**: Carries data and jumps to Tab 2.
7. **[📜 Read History of Past Successful Registrations]**: Loads past registration footprints into Area 2.
8. **[✨ Normalize Names]**: Looks up the CSV dictionary, automatically adding Chinese names. The underlying algorithm (`unicodedata.east_asian_width`) precisely calculates the "East Asian visual width" of full/half-width characters to ensure the `->` arrows output in the textbox perfectly align vertically.
9. **[🧹 Clear History Record]**: Deletes `registered_history.json`.
10. **[🚀 Verify Conflicts & Output File]**: Merges Area 1 and Area 2, writes to export Bundle.

#### Single-Page SOP
* **SOP 13.1: Add New Over-Frame Card Registration**
  1. Set paths, click **[📥 Read Existing Raw File]** to verify Area 1 successfully loaded the list.
  2. Input IDs in Area 2 (or click **[🔍 Go to "Find Files" to Pick Cards]** to jump and pick, or click **[📜 Read History of Past Successful Registrations]** to load history).
  3. Click **[✨ Normalize Names]** to check naming format.
  4. Click **[🚀 Verify Conflicts & Output File]**. The registry Bundle is generated in `Project Directory/Modified Files/`.
  5. **Crucial Physical Overwrite Step**: Manually copy the `of_card_asset` Bundle inside `Modified Files/` and paste it back into the game 0000 directory (or mount via Tab 11) for it to officially take effect in-game.
* **SOP 13.2: Delete Whitelist Items**
  1. Click **[📥 Read Existing Raw File]**.
  2. Directly manually delete the target card rows inside the Area 1 Textbox.
  3. Click **[💾 Save Existing Whitelist]** (or [🚀 Verify Conflicts & Output File]). The updated Bundle is generated in `Modified Files/`.
  4. **Crucial Physical Overwrite Step**: Manually copy the Bundle back into the game 0000 directory (or mount via Tab 11).

---

### 12. Graphical Gallery (Tab 12, `t12_gallery`)

<img width="1053" height="837" alt="瀏覽" src="https://github.com/user-attachments/assets/2f553750-194c-4165-8ce7-420b45f93171" />

#### Technical Mechanism & Operational Principle
Provides thumbnail previews and incognito sandbox filtering for 8 major non-card assets.
* **Memory Lookup Table Caching**: Upon first read, extracts Texture2D from AssetBundles to generate caches; subsequent reads skip HDD I/O and render directly from caches, massively boosting view speeds.
* **Inertial-less Grid Scrolling**: Imports linear scroll filters for grid lists, achieving web-style straight-up straight-down operation, entirely rooting out Qt's built-in scroll oscillation.
* **Sandbox Visual Filtering (`CAT_FILTER`)**: A dedicated temporary lifecycle container. When batch IDs are sent here from Tab 2, the system builds exclusive sandbox caches. Users can graphically delete items here; once finished, the streamlined list is losslessly returned to Tab 2.
* **Double Click Quick Single Card Mapping**: Double-clicking any thumbnail in the list automatically sends that asset's true ID to Tab 9 (Quick Single Card Mod) and jumps automatically.
* **Ctrl + Scroll Wheel Adaptive Scaling (`instant_wheel_scroll`)**: Intercepts underlying Qt events. Holding `Ctrl` while scrolling directly ties into changing thumbnail dimensions, implementing a smooth scaling experience like modern web browsers.
* **Protector Forced Reshaping & Variant Deduplication**: When loading the `protectoricon` category, forcibly switches draw mode to `Qt.IgnoreAspectRatio`, stretching image height to 1.5x of width to match in-game ratios. It simultaneously auto-detects and hides thumbnails with `_L` / `_l` suffixes, preventing the list from being flooded with redundant large-size variants.

#### Full UI Components and Button Functions
* **Select Category (ComboBox)**: Provides Field, Coin, Deck, Icon Frame, Icon, Protector, Lobby Background, and File Filter (Sandbox) 8 filtering dimensions.
* **[Load Selected Category Thumbnails]**: Scans the mapping table and generates/reads caches to render the grid.
* **[🧹 Clear Gallery Cache]**: Safely deletes the `gallery_cache` folder, freeing up hard drive space.
* **[Send to "Find Files"]**: Sends the selected item and its associated variants (e.g.: selecting a Coin Front automatically packages Coin Back) to Tab 2's Extraction List.
* **[Send to "Quick Single Card Mod"]**: Sends the selected ID to Tab 9.
* **[✨ Confirm Edits & Return]**: (Only visible in Sandbox mode) Brings the filtered streamlined ID list back to Tab 2 and automatically destroys the Sandbox.
* **Shortcut Operations**: After selecting an item, pressing `Delete` or `Backspace` deletes it; pressing `Ctrl+Z` undoes the deletion.

#### Single-Page SOP
* **SOP 12.1: Asset Viewing & Double Click Quick Mod**
  1. Select a category (e.g., "Icon"), click **[Load Selected Category Thumbnails]**.
  2. Browse the grid for the target asset. **Directly double-click that thumbnail**, and the system will automatically bring the ID and jump to Tab 9 to enter the single card replacement workflow.
* **SOP 12.2: Tab 2 Linked Sandbox Visual Culling**
  1. After loading massive IDs (or a TXT) in Tab 2, click **[🔍 Visual Sandbox Filter]** to jump to this page's "File Filter" mode.
  2. The system automatically generates thumbnails for all files in the list.
  3. Box-select inappropriate or mis-searched thumbnails, press `Delete` to cull them (press `Ctrl+Z` to undo if mistaken).
  4. Click **[✨ Confirm Edits & Return]**, and the system automatically brings back the streamlined pure ID list to Tab 2 and performs normalization alignment.
---

### 13. Mod Stream Updater (Tab 10, `t10_updater`)

<img width="1101" height="841" alt="修復" src="https://github.com/user-attachments/assets/6434cb46-c528-48d8-a799-486f0e45e16c" />

#### Technical Mechanism & Operational Principle
Solves black image or crash issues for old Mods caused by major game updates.
* **Inline Texture Injection**: Reads the "latest official raw file", zeroes out its `m_StreamData` external links, and forcibly injects/embeds the binary pixel data of the old Mod into the new version Bundle, achieving a lossless upgrade.

#### Full UI Components and Button Functions
* **1. Old Mod Directory / 2. Game Raw File (0000) / 3. Output Root Directory (Path Rows)**: Path settings.
* **Overwrite Old Mod (Checkbox)**: Dangerous operation, directly replaces old files.
* **[Start Stream Fix]**: Executes binary transplantation.

#### Single-Page SOP: Old Mod Cross-Version Fix
1. Set Old Mod Directory and Latest 0000 Raw File Directory.
2. Click **[Start Stream Fix]**. Fixed files will be exported to the `FIXED_MOD/` folder.

---

### 14. Virtual Mod Manager (Tab 11, `t11_virtual`)

<img width="1065" height="841" alt="虛擬" src="https://github.com/user-attachments/assets/53fa520d-d56b-43b5-ad74-b7a9a06cd143" />

#### Technical Mechanism & Operational Principle
Uses Windows `os.symlink` (Soft Links) to realize instant mod toggling without copying and zero HDD usage.
* **Pre-flight Check & Atomic Transactions**: Before establishing links, the system preemptively conducts `os.access` simulated write permission tests on all target paths, ensuring "either it all succeeds, or it's rejected from the start". If an OS lock exception occurs midway, the rollback engine reads `symlink_state.json` to intervene instantly, forcibly dissolving ghost links (`os.unlink`) and restoring backups, ensuring no broken fragments are left in the game structure.
* **Hot-Reload Core Advantage**: After mounting soft links, they physically target files inside your Mod folder. When the game is open, if you modify and repackage output resources into that Mod folder, **the game will instantly read the latest data in real-time the next time the asset is played or loaded, requiring absolutely no re-linking, no copy/pasting, and definitely no restarting the game**.

#### Full UI Components and Button Functions
* **Mod Storage Root Directory / Game 0000 Folder (Path Rows)**: Path settings.
* **Scan Depth (ComboBox)**: Max levels to penetrate searching for `0000` (1~5).
* **Enabled & Disabled Lists (ListWidgets)**: Left is enabled, right is disabled.
* **[Refresh]**: Re-scans the Mod root directory.
* **[>>] / [<<]**: Disable All / Enable All selected items.
* **Middle/Right Click Quick Transfer**: Implemented `UIHelper.setup_quick_transfer` event hijacking. Simply right-click or middle-click a list item to instantly toss it between the "Enabled List" and "Disabled List", bypassing the hassle of dragging or clicking buttons.
* **[▲] / [▼]**: Adjusts enable priority (Top overwrites bottom).
* **[▶ Apply & Save]**: Executes Symlink mounting and backup.

#### Single-Page SOP: Virtual Mount & Hot-Reload
1. Place multiple Mod folders into "Mod Storage Root Directory".
2. Click **[Refresh]**, double-click items to move desired mods to the left list.
3. Click **[▶ Apply & Save]** (Requires Admin Privileges).
4. **Hot-Reload**: Keep the game open. If you re-output new Bundles to that Mod folder via Tab 8 or Tab 4, the game will reflect the latest effects in real-time the next time that asset triggers, without needing a restart.

---

## Chapter 3: Full Scenario Practical Case Library (End-to-End Workflow Combinations)

This chapter provides cross-tab combined workflow SOPs.

### Case 1: Creating a Standard Card Art Mod from Scratch
1. **Tab 1 (Scan)**: Set 0000 directory, click **[Start Scan]** to generate `2DTexture_Mapping.csv`.
2. **Tab 2 (Find)**: Enter card name or ID, add to list, click **[Start Extracting Raw Files]** to copy binary files to `Raw Files/`.
3. **Tab 3 (Extract)**: Click **[Start Extracting Contents]**, unpack editable PNGs to `Raw Card Art/`.
4. **Art Modification**: Edit PNGs using image software, save into `Card Art Mod/`.
5. **Tab 4 (Replace)**: Click **[Start Replacement]**, write new images back to Bundles, exporting to `Modified Files/`.
6. **Tab 5 (Package)**: Check packaging options, click **[Start Packaging]** to generate full mod zip.

### Case 2: Upgrading a Normal Card into Brand New Over-Frame Art
1. **Tab 1 -> Tab 2 -> Tab 3**: Follow Case 1 to extract original card art.
2. **Tab 8 (Post-Processing)**: Select "Over-Frame Art Post-Processing", adjust PSD 5-layer transparency, click **[🚀 Start Execution Post-Processing]**, generating 11:16 Over-Frame composite image to `Card Art Mod/`.
3. **Tab 4 (Replace)**: Click **[Start Replacement]**, writing Over-Frame image back to Bundle, exporting to `Modified Files/`.
4. **Tab 13 (Register)**: Click **[📥 Read Existing Raw File]**, input that Card ID in Area 2, click **[✨ Normalize Names]**, click **[🚀 Verify Conflicts & Output File]** exporting `of_card_asset` to `Modified Files/`.
5. **Physical Overwrite**: Copy all Bundles inside `Modified Files/` and paste back into the game 0000 directory (or mount via Tab 11).

### Case 3: Creating and Replacing a Card Cut-In Animation from Scratch (Spine Cut-In)
1. Prepare a static image, a green screen video, or sequential images in a PSD or folder. Name it `p18533.png` or `p18533.mp4`... and save to `Card Art Mod/`.
2. **Tab 8 (Post-Processing)**: Select "Cut-In Animation Post-Processing", pick key color and adjust Despill intensity and POP UP curves, click **[🚀 Start Execution Post-Processing]** to generate Spine atlases.
3. **Tab 4 (Replace)**: Click **[Start Replacement]**, write back animation Bundles. Tool auto-corrects Gamma color space.
4. **Tab 5 (Package)**: Package and release.

### Case 4: Fixing Broken Over-Frame Registries After Major Game Updates
1. After a major game update, enter **Tab 13 (Register)**.
2. Click **[🛠️ Manual Bruteforce Fix (For After Major Updates)]**. The system auto-scans the newest 0000 directory, finding the new Hash and seamlessly transferring historical registrations.
3. Click **[🚀 Verify Conflicts & Output File]** to generate the newest Registry Bundle.
4. Copy the exported Bundle back into the game 0000 directory.

### Case 5: Old Broken Mod Rescue & Hot-Reload
1. **Tab 10 (Updater)**: Set Old Mod Directory and newest 0000 Directory, click **[Start Stream Fix]** to export fixed Bundles.
2. **Tab 11 (Virtual Mount)**: Place fixed mod into Mod Root Directory, click **[▶ Apply & Save]**. Open the game directly to verify, achieving real-time preview without restarting.

---

## Chapter 4: Advanced Engineering Techniques (Advanced Techniques)

### Advanced Technique 1: Reverse Scan "Modified Files" to Quickly Export a TXT List
* **Scenario**: When acquiring a ready-made Mod pack or `Modified Files/` folder, and you want to quickly grab all Card IDs inside to bring into Tab 13 for Over-Frame registration or Tab 2 for cross-referencing.
* **Operation SOP**:
  1. Go to **Tab 1 (Bruteforce Scan & Append)**.
  2. Manually point the "Target Folder (0000)" path to **"Modified Files" or the Mod Folder**.
  3. ONLY check "Generate Content List (TXT)", uncheck "Generate Mapping Table (CSV)" to save time.
  4. Click **[Start Scan]**.
  5. The system reads all Bundles inside, reverse extracting all Texture and Asset IDs, and outputs `Extracted_Names.txt` in the output directory.
  6. This TXT can be directly loaded in Tab 2 or pasted into Tab 13, saving manual entry hassle.

### Advanced Technique 2: Using Virtual Mount (Tab 11) for Extreme Animation/Art Hot-Reloads
* After mounting soft links, while the game is running, if you output and repackage resources into the mod folder, the game directly reads the new data real-time the next time that asset plays, requiring zero re-linking, zero copying, and definitely zero game restarts.

### Advanced Technique 3: Tab 2 & Tab 12 Sandbox Visual Culling Two-Way Flow
* Input batch IDs in Tab 2, click **[Visual Sandbox Filter]** jumping to Tab 12. Press `Delete` to cull mismatches, click **[✨ Confirm Edits & Return]** to auto bring back streamlined IDs. Alternatively, you can double-click any item you want to select to send it directly to Quick Single Card Mod.

### Advanced Technique 4: Shortcut Keys & Path Spacebar Force Refresh Trick
* When a path update on Tab 2 doesn't immediately link to Tab 3, simply click the middle of Tab 2's path input box, **type a spacebar, and delete that spacebar**. This forces the `textChanged` signal to trigger a full-page path refresh.

---

## Chapter 5: System Troubleshooting Guide (Troubleshooting)

1. **`PermissionError: Insufficient Permissions`**
   * **Cause**: `2DTexture_Mapping.csv` is being held open by Microsoft Excel or another program, causing Python to fail to acquire a Write Lock.
   * **Solution**: Close Excel or relevant editors and retry.

2. **Out Of Memory (OOM) or Interface Freezing**
   * **Solution**: Go to **Tab 7 (Settings & Appearance)** and lower "Max Compute Power (Threads)" from `Auto` to 2 or 4. When processing animations, check "Enable Hard Drive Cache".

3. **`.pristine` Baseline File Protection and Restoration**
   * **Warning**: Do not randomly delete `.pristine` files inside `MD_Tool_Temp/of_card_asset_backups/`. If the baseline file is lost and anomalies occur, click **[🛠️ Manual Bruteforce Fix]** in Tab 13 to re-establish the newest baseline.