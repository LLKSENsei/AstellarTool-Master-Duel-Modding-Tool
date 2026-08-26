--- START OF FILE TUTORIAL_en.md ---

[繁體中文](TUTORIAL.md) | [English](TUTORIAL_en.md)

***

# MD AstellarTool Engineering Operations and In-Depth Technical Manual

This manual serves as the complete engineering specification and technical usage guide for "MD AstellarTool". This document avoids all hyperbolic language or emojis, aiming to precisely, deeply, and rigorously reveal the underlying operational mechanisms, image processing algorithms, memory management strategies, binary data flows, and security protection architectures of this tool.

Users will be able to understand the physical significance of every input parameter, the system-level behaviors triggered behind all buttons and switches, the operational steps for independent tabs, and cross-module practical combination cases.

---

## Chapter 1: System Paths and Resource Naming Specifications

The batch automation engine of the tool highly relies on precise path mounting and Regular Expression (Regex) extraction of filenames. Before using, you must ensure compliance with the following specifications.

### 1.1 Core Physical Path Definitions
* **Game 0000 File Directory (0000 Directory)**
  The root directory storing the game's main card and primary asset binary AssetBundles.
  Default path format: `[Drive]:\SteamLibrary\steamapps\common\Yu-Gi-Oh! Master Duel\LocalData\[8-digit Player ID]\0000\`
* **Game StreamingAssets Directory (StreamingAssets Directory)**
  The directory storing high-resolution materials or large data packages.
  Default path format: `[Drive]:\SteamLibrary\steamapps\common\Yu-Gi-Oh! Master Duel\masterduel_Data\StreamingAssets\AssetBundle\`
* **Game Lobby Background Data Packet (Lobby Background Data)**
  A single binary packet file storing interface resources, including the lobby background texture `ShopBGBase02`.
  Default path format: `[Drive]:\SteamLibrary\steamapps\common\Yu-Gi-Oh! Master Duel\masterduel_Data\data.unity3d`

### 1.2 Resource Naming and Normalization Parsing Mechanisms
When the tool performs binary packaging or database matching, it uses Python's `re` module to strip user-defined prefixes/suffixes.

* **Card Image File Naming Conventions**
  * **Rule**: `[CardID]_[Any Custom Tag].[Extension]` or `[CardID].[Extension]`
  * **Underlying Mechanism**: The tool uses `^([a-zA-Z]*)(\d+)(.*)$` for extraction. The system ignores leading English letters, strictly targets the "continuous block of numbers" in the string as the Card ID, and treats all subsequent characters (including underscores, spaces, etc.) as invalid suffixes to be stripped.
  * **Correct Examples**: `20570.png`, `20570_Albaz.png`, `Alt17069_CustomArt.jpg`.
  * **Incorrect Example**: `Albaz_20570.png` (The parser will fail to capture the number at the beginning of the string, resulting in a match failure).
* **Non-Card Visual Assets (UI / Fields / Protectors)**
  * **Rule**: Must exactly match the names extracted from the game's reference table (case-insensitive).
  * **Underlying Mechanism**: The tool uses `unicodedata.normalize('NFKC', text).lower()` for bi-directional assimilation matching, eliminating full-width/half-width and case differences.
  * **Examples**: `Mat_001_BaseColor.png`, `ProfileIcon1020001.png`.

---

## Chapter 2: Full Interface Tab Analysis and Single-Page SOPs

This chapter details the interface components, input fields, switches, buttons, and Standard Operating Procedures (SOPs) for all tabs, following the software's default sequence.

---

### 1. Settings & Appearance (Tab 7, `t7_settings`) [Primary Configuration Page]

<img width="1095" height="847" alt="Settings" src="https://github.com/user-attachments/assets/c87beb83-5276-48bf-b9c5-3f5c7a3ef661" />

#### Technical Mechanisms and Operating Principles
This module is the global configuration hub of the tool, responsible for writing and reading JSON configuration files, emitting cross-tab path synchronization signals, and rendering dynamic QSS stylesheets.
* **Atomic Write Anti-Corruption Mechanism (`_atomic_write_json`)**: When clicking to write settings, the system first uses `RLock` to lock the thread, excludes massive memory caches (e.g., `t2_extraction_list`), writes the clean dictionary to a `.tmp` temporary file, and finally uses `os.replace` for physical atomic substitution. This mechanism ensures that even if a power outage occurs during writing, the configuration file will not become a corrupted 0KB file.
* **AST (Abstract Syntax Tree) Source Code Parser (`task_generate_translation_template`)**: Once activated, it invokes the Python `ast` module to traverse the main program's source code, grabs all strings wrapped in `_("...")` and UI `placeholder`s, automatically generates the `MD_Tool_Essential/Languages/raw.json` locale template, and losslessly fills in any missing items in `zh-tw.json`.

#### Full Interface Components and Input Fields Details
* **Cross-Tab Path Synchronization (Checkbox)**: When enabled, modifying the "Project Root Directory", "0000 Source", or "CSV Dictionary" paths on any page will broadcast updates to corresponding input fields across all pages via ConfigSignals.
* **Auto-Switch Tabs on Completion (Checkbox)**: When enabled, the system automatically jumps to the next corresponding processing page upon completion of a single task.
* **Language (Requires Restart) (ComboBox)**: Sets the interface language (default `zh-tw`, `en-us`). You can manually input other language codes (e.g., `ja-jp`), and the system will automatically attempt to load `Languages/[Code].json`.
* **Max Compute (Threads) (ComboBox)**: Sets the CPU core count for the multi-processing pool (`ProcessPoolExecutor`). You can enter a number or set it to `Auto`. When set to `Auto`, the system automatically reserves 1 to 4 cores for OS operations to prevent UI freezing caused by 100% CPU usage.
* **Specify Font (ComboBox)**: Selects the interface display font.
* **Custom 5-Dimension Color Palette (Buttons)**: Provides 5 color blocks: "Accent", "Background", "Text", "Sidebar Background", and "Border". Clicking pops up a `QColorDialog` supporting Alpha channel selection, instantly rebuilding the QSS stylesheet and applying it to the entire window.
* **Global Project Folder Naming Settings (LineEdits)**: Sets the default names for folders such as "Original Files", "Original Card Arts", "File Backups", "Modded Arts", "Completed Files", and "CSV Dictionary".
* **Sidebar Tab Sorting and Renaming (ListWidget & LineEdit)**: Lists all tabs. You can select an item and use the [▲], [▼] buttons to adjust the sidebar order, or enter a new name in the input box and click [Rename].
* **Background Image (Path Row)**: Sets a local image as the GUI background.
* **Transparency (Slider)**: Adjusts the interface translucency (0 to 100%).
* **Brightness (Slider)**: Adjusts the background image brightness (10 to 200%).
* **9-Grid Anchor (LinkAnchorPicker)**: Provides 9-grid position selection, determining the fixed anchor point of the background image when the window is resized.

#### Button Functions Details
* **[Write JSON Config (Save All Changes)]** (One at the top, one at the bottom): Saves the current settings to `md_tool_config.json`.
* **[Export Translation Template (raw.json)]**: Executes AST parsing to output a locale template file.

#### Independent Operations SOP and Path Saving Specifications for This Tab
1. In "Global Project Folder Naming Settings", verify that the folder names align with your workflow habits.
2. **Important Path Saving Specifications**: When clicking [Write JSON Config], the system records all input fields on the UI. To prevent saving one-time temporary project paths into the global configuration, please clear the temporary project subdirectories entered in other tabs before saving. Retain only the "0000 Game Directory", "Main CSV Reference Path", and "Default Folder Names".
3. Click **[Write JSON Config (Save All Changes)]**. The next time the tool is opened, temporary fields will remain blank, making it easy to directly paste new project paths.

---

### 2. Beginner's Guide and Operation Journey (Tab 0, `t0_guide`)

#### Technical Mechanisms and Operating Principles
This module is a static information display page using a read-only `QPlainTextEdit` to render system guides and statements, consuming no system computing resources.

#### Interface Components and Operations
* Built-in full instructional text allowing users to browse standard project workflows, quick pipelines, and descriptions of each tab's functions.

---

### 3. Brute-Force Scan & Append (Tab 1, `t1_scan`)

<img width="1093" height="844" alt="Scan" src="https://github.com/user-attachments/assets/9b6cfa84-eaf0-4183-8976-28b62c36321a" />

#### Technical Mechanisms and Operating Principles
This module traverses the binary files in the 0000 directory to construct a CSV dictionary correlating Card IDs, real names, effect texts, and Hash codes.
* **XOR Dynamic Decryption Engine**: Official card text databases are encrypted. The system defaults to using `0x3D (61)` for XOR bitwise inversion. If official updates cause decryption failure, the engine triggers the `auto_crack_key` function, conducting a brute-force poll within the 0 to 1023 range, unpacks and verifies the zlib packet structure, and upon success, automatically captures the new key and writes it back to the config file.
* **6-bit Physical Mask Determination**: For attribute determination, the engine directly reads the `card_prop.bytes` binary offsets. If the bit value is `0x020D`, it's classified as a Spell Card; for Monster Cards, it extracts the first 6 bits (6-bit mask) for physical signature matching (e.g., `0x19`, `0x24` corresponding to Pendulum), supplemented by NLP effect text keyword scanning for precise card classification.
* **IL2CPP Metadata Collision**: For accessory assets without Card IDs (e.g., Icons, Fields), it reads `global-metadata.dat` to extract ID strings, calculates the CRC32 hash, and performs a two-way collision match with `ids_item.bytes` to restore the names.
* **Memory Failsafe Monitoring**: During multi-process scanning, it calls the Windows `GlobalMemoryStatusEx` API. When physical memory load reaches the 85% threshold, it forces hibernation and waits for Garbage Collection (GC) recovery to prevent system crashes.

#### Full Interface Components and 10 Main Switches Detail Breakdown
* **Target Directory (0000)**: Specifies the game's 0000 folder path.
* **Save Root Directory**: Project output location; all subsequent operations are based on this.
* **TXT / CSV Naming (LineEdits)**: Sets the output names for the list file and dictionary file.
* **1. Enable Size Filter (Checkbox, `t1_size_filter`)**:
  * **ON**: Restricts scanning to Bundle files whose sizes fall between "Lower Limit (KB)" and "Upper Limit (KB)", avoiding irrelevant micro-files and massive files.
  * **OFF**: Indiscriminately scans all Bundle files in the target directory.
* **2. Scan Cards Only (Checkbox, `t1_only_numbers`)**:
  * **ON**: Extracts only card assets with pure numerical IDs, ignoring accessories like fields and sleeves that contain English letters.
  * **OFF**: Extracts both pure numerical cards and accessory assets containing English letters.
* **3. Generate Content List (TXT) (Checkbox, `t1_gen_txt`)**:
  * **ON**: Automatically generates a TXT list containing all IDs.
  * **OFF**: Does not generate a TXT list.
* **4. Generate Reference Table (CSV) (Checkbox, `t1_gen_csv`)**:
  * **ON**: Automatically exports the main CSV dictionary containing directories, Containers, Hashes, and IDs.
  * **OFF**: Does not export the CSV reference table (used when reverse-exporting TXT from an already modified directory).
* **5. Include Card Names (Checkbox, `t1_ext_name`)**:
  * **ON**: Writes the card names of the specified locale into the CSV.
  * **OFF**: Does not write card names to the CSV.
* **6. Include Card Descriptions (Checkbox, `t1_ext_desc`)**:
  * **ON**: Writes card effect text into the CSV, facilitating future searches by effect keywords.
  * **OFF**: Does not write effect text, significantly reducing CSV size and speeding up read times.
* **7. Include Accessory Names (Checkbox, `t1_parse_meta`)**:
  * **ON**: Reads `global-metadata.dat` to restore names of accessories like sleeves and icons.
  * **OFF**: Does not parse Metadata; accessories will display raw codes.
* **8. Prioritize Cache (Checkbox, `t1_use_cache`)**:
  * **ON**: Reads temporary files left from previous decryptions in `MD_Tool_Temp/` to achieve sub-second scanning.
  * **OFF**: Forces re-decryption of game Bundles. Must be turned off after major game updates to acquire new data.
* **9. Deep Scan (Checkbox, `t1_deep_scan`)**:
  * **ON**: Deeply unpacks all objects inside Bundles, extracting field textures or lobby backgrounds hidden within massive asset packages.
  * **OFF**: Only matches top-level Container paths, resulting in extremely fast scan speeds.
* **10. Process Visual Objects Only (Fields/Sleeves/Icons) (Checkbox, `enable_visual_only_filter`)**:
  * **ON**: Filters out pure numerical regular cards; scan results will only retain accessory assets.
  * **OFF**: Scans all assets according to regular rules.
* **Language (ComboBox) / XOR Key (LineEdit)**: Decryption language and key.
* **CSV to Expand (Path Row)**: Path of an old CSV to be used by the Append/Expand function.

#### Button Functions Details
* **[Start Scan]**: Initiates multi-process scanning; upon completion, generates the TXT list and CSV dictionary.
* **[Execute Append / Expand]**: Reads the "CSV to Expand" and appends new locale columns to the right side of the CSV.
* **[Stop Scan / Abort Operation]**: Sends a `multiprocessing.Event()` interrupt signal to terminate child processes.

#### Independent Operations SOP for This Tab
* **SOP 1.1: Full Game 0000 Directory Scan**
  1. Fill in "Target Directory (0000)" and "Save Root Directory".
  2. Check "Generate Reference Table (CSV)", "Include Card Names", and "Include Accessory Names".
  3. Click **[Start Scan]**. Once completed, `2DTexture_Mapping.csv` will be generated in the root directory.
* **SOP 1.2: Old CSV Multi-Language Reference Expansion**
  1. Select a previously created CSV file in "CSV to Expand".
  2. Switch the "Language" to the target new language (e.g., `ja-jp`).
  3. Click **[Execute Append / Expand]**. The system will automatically populate the new language column and save it.

---

### 4. Find Files (Tab 2, `t2_find`)

<img width="1096" height="842" alt="Find" src="https://github.com/user-attachments/assets/3f22366e-02d1-465c-a389-159fdeea75b0" />

#### Technical Mechanisms and Operating Principles
Based on the CSV dictionary, it accurately locates and copies out target binary Hash files from the 0000 directory.
* **Google-like Advanced Tokenization Search Engine (`search_cards_advanced`)**: The system features a high-performance memory search matrix supporting Boolean logic and precise affix filtering. The following syntax can be used in the search box:
  * **Space Separation**: Treated as `AND` logic; all keywords must be met simultaneously.
  * **Quotation Marks (`"keyword"`)**: Forces exact matching of the entire phrase within quotes, without tokenization.
  * **Mandatory Inclusion (`+keyword`)**: The target must contain this keyword (applies to both card name or effect text).
  * **Mandatory Exclusion (`-keyword`)**: If the target contains this keyword, it is immediately excluded (e.g., excluding specific archetypes).
* **Matrix-based Attribute Filtering (Matrix Filter)**: By parsing the 6-bit physical mask of `card_prop.bytes`, it provides precise cross-referencing for 3 major categories (Monster, Spell, Trap) and 18 sub-attributes.
* **Inertia-less Linear Scrolling (`LinearDragScrollFilter`)**: Injects an underlying EventFilter that translates mouse drags into decimal step accumulations, achieving web-level instant-stop scrolling, completely eliminating Qt's default oscillation and rebound.
* **Dynamic Memory Pagination Slicing**: Search results support instant 0ms rendering slices ranging from 50 items to infinity per page, avoiding thread freezing caused by writing tens of thousands of records to the UI simultaneously.

#### Full Interface Components and Input Fields Details
* **Selection Mode (ComboBox)**:
  * `MODE_NORMAL` (Standard Extraction): Purely copies Hash files to the "Original Files" folder.
  * `MODE_QUICK` (Quick Overframe Switch): Launches a fully automated Overframe write pipeline. Important limitation: Quick Overframe Switch mode is only applicable to original game card art. For custom card art, use Tab 8 instead.
* **Reference Language and Search Box (ComboBox & LineEdit)**: Sets the search target language. The search box supports the advanced search syntax mentioned above.
* **Collapsible Filter Panel (Filter Panel)**:
  * **Monster Section**: Provides filters for Effect, Normal, Fusion, Synchro, Xyz, Link, Ritual, Pendulum, and Token physical card types.
  * **Spell Section**: Provides filters for Normal, Quick-Play, Continuous, Field, Equip, and Ritual.
  * **Trap Section**: Provides filters for Normal, Counter, and Continuous.
  * **Auxiliary & Advanced Section**: Contains the "Process Visual Objects Only" switch, a fuzzy matching fault-tolerance switch for card names and effect texts (algorithm based on `SequenceMatcher` sliding window), and single-page display limit settings.
* **Reference Table (CSV) / Load from TXT / File Source (0000) / Save Root Directory (Path Rows)**: Sets the read/write paths for various stages. If a path fails to refresh immediately, click inside the input box, press the spacebar, and then delete it to forcefully trigger an update.
* **New Folder Name (LineEdit)**: The folder name for storing copied binary files (default `Original Files`).
* **Pagination Navigation Bar (Navigation Bar)**: Provides Previous Page, Next Page switching, and batch writing buttons for "Add All on Current Page" and "Add All Search Results".
* **Search Results List (ListWidget) / Extraction List (PlainTextEdit)**: Displays searched items and the final ID list to be extracted.

#### Button Functions Details
* **[Start Extracting Original Files] / [Start Automated Overframe Modification]** (Top and Bottom): Executes file copying or initiates the automated Overframe pipeline.
* **[Load TXT]**: Loads IDs from an external text file into the Extraction List.
* **[Normalize Names]**: Reverses the lookup in the CSV dictionary to reformat the IDs in the text box into the `ID (Name) [Hash]` format.
* **[Visual Filtering]**: Launches Sandbox mode, sending IDs in the extraction list to Tab 12 to generate image caches for manual visual culling.
* **[Confirm IDs and Return to Overframe Register]**: (Conditionally visible) Carries the IDs from the list and jumps back to Tab 13.
* **List Double-Click and Right-Click Operations**: Double-clicking a search result list item, or highlighting and right-clicking, quickly adds the item to the extraction list.

#### Independent Operations SOP for This Tab
* **SOP 2.1: Standard Original File Extraction**
  1. Ensure the Mode menu is set to "Standard Extraction".
  2. Expand the "Filter" panel to set card types, or enter advanced syntax in the search box (e.g., `"Albaz" -Fusion`).
  3. Double-click items in the result list or click "Add All on Current Page" on the pagination bar to send IDs to the extraction list.
  4. Click **[Start Extracting Original Files]**. Target binary files will be copied to `Project Directory/Original Files/`.
* **SOP 2.2: Original Art Quick Overframe Fully Automated Processing**
  1. Switch the Mode menu to "Quick Overframe Switch".
  2. Enter the original game Card ID in the extraction list.
  3. Click **[Start Automated Overframe Modification]**.
  4. The internal pipeline sequentially automates: Extract Original File -> Unpack Original Image and Backup Bundle -> Copy Image -> Execute 11:16 Cropping and PSD Frame Compositing -> Write Back to Bundle -> Carry Card ID and send to Tab 13 Register.

---

### 5. Extract Data (Tab 3, `t3_extract`)

<img width="1076" height="842" alt="Extract" src="https://github.com/user-attachments/assets/91e4e574-9103-4825-9c8a-2a18666cf79e" />

#### Technical Mechanisms and Operating Principles
Uses UnityPy to unpack Bundles, exporting `Texture2D` (image files) and `TextAsset` (text descriptions).
* **Area Protection Mechanism**: Before writing images, it compares total pixel area `(w * h) <= (ext_img.w * ext_img.h)`. If the unpacked resolution is smaller than an existing file on disk, writing is aborted to protect already modified high-resolution image files.
* **Texture Filtering (`is_valuable_texture`)**: Automatically blocks 3D render textures, exporting only useful 2D visual assets.

#### Full Interface Components and Input Fields Details
* **Folder Containing Files to Extract (Path Row)**: Specifies the input path (usually pointing to `Original Files`).
* **Export CSV / Export Images / Export Text Data / Backup Files (Checkboxes)**: Controls unpacking export items.
* **Process Visual Objects Only (Checkbox)**: Filters out non-card assets.
* **Image Folder Name (LineEdit)**: Directory for exported images (default `Original Card Arts`).

#### Button Functions Details
* **[Start Extracting Contents]**: Initiates multi-process unpacking. Images are written to `Original Card Arts/`, and original Bundles are copied to `File Backups/`.

#### Independent Operations SOP for This Tab: Unpacking Export
1. Verify "Folder Containing Files to Extract" points to `Project Directory/Original Files`.
2. Check "Export Images" and "Backup Files".
3. Click **[Start Extracting Contents]**. Exported PNGs will be saved in `Project Directory/Original Card Arts/`.

---

### 6. Replace Art (Tab 4, `t4_replace`)

<img width="1093" height="845" alt="Replace" src="https://github.com/user-attachments/assets/da18dfc5-efeb-470a-904e-b9bb1584c97b" />

#### Technical Mechanisms and Operating Principles
Re-stitches and writes externally modified images back into the binary Bundle.
* **Lanczos Resampling (`MODE_FIT_VISUAL`)**: For non-card UI assets, the system forces the Lanczos algorithm to scale exactly to original specifications to prevent UI tearing.
* **Color Space Correction**: For Spine animation textures (`p[number]`), it forces `m_ColorSpace` to `0` (Gamma space) upon writing, eliminating fluorescent color shifts.
* **Atomic Writing**: Writes to `.tmp` followed by `os.replace` physical substitution to prevent generating 0KB corrupted files during power loss.

#### Full Interface Components and Input Fields Details
* **Dictionary (CSV) File / Project Root Directory Position (Path Rows)**: Global read/write paths.
* **Backup Position (LineEdit)**: Directory storing unmodified Bundles (default `File Backups`).
* **Modified Art Position (LineEdit)**: Directory storing modified PNGs/JPGs (default `Modded Arts`).

#### Button Functions Details
* **[Start Replacement]**: Reads images from "Modded Arts", writes them back to the corresponding Bundle in "File Backups", and saves the product to `Modified Files/`.

#### Independent Operations SOP for This Tab: Writing Images Back to Bundle
1. Name your modified image as `[CardID].png` and place it in `Project Directory/Modded Arts/`.
2. Verify Backup Position points to `File Backups`.
3. Click **[Start Replacement]**. The modified Bundle will be generated in `Project Directory/Modified Files/`.

---

### 7. Package Module (Tab 5, `t5_package`)

<img width="1089" height="843" alt="Package" src="https://github.com/user-attachments/assets/3fa4427a-a506-4be0-b216-30cd440d5573" />

#### Technical Mechanisms and Operating Principles
Reconstructs the directory level of modified Bundles according to the original Master Duel file system specifications.
* **Hash Directory Splitting**: Based on the CSV reference table, if it belongs to `0000` resources, it automatically extracts the first two characters of the Hash code (e.g., `a589...` -> `a5`), creates an `0000/a5/` subdirectory, and moves the file there.

#### Full Interface Components and Input Fields Details
* **Dictionary (CSV) File / Project Root Directory (Path Rows)**: Read/write paths.
* **Folder Naming (LineEdit)**: Output module directory name (default `ModFolder`).
* **Include "Modded Arts" / Include ReadMe.txt / Compress into ZIP Simultaneously (Checkboxes)**: Packaging controls.
* **ReadMe Default Text (PlainTextEdit)**: Custom instructional document content.

#### Button Functions Details
* **[Start Packaging]**: Creates structures, copies files, and executes ZIP compression.

#### Independent Operations SOP for This Tab: Packaging and Release
1. Set "Folder Naming", and check "Compress into ZIP Simultaneously".
2. Click **[Start Packaging]**. A release-ready module compressed file will be produced in the root directory.

---

### 8. Smart Chain Execution (Tab 6, `t6_chain`)

<img width="1097" height="847" alt="Chain" src="https://github.com/user-attachments/assets/e7c4eb7d-f103-42f6-bb21-b08d96276016" />

#### Technical Mechanisms and Operating Principles
Implements an asynchronous Callback Queue driven architecture for unattended automated multi-step execution.

#### Full Interface Components and Buttons
* Checkboxes: [2] Find Files, [3] Extract Data, [8] Pendulum Post-Processing, [4] Replace Art, [5] Package Module.
* **[▶ Start Automated Task]**: Executes checked tasks sequentially.

#### Independent Operations SOP for This Tab: One-Click Automation
1. Ensure paths and settings in relevant tabs are completely filled out.
2. Check the steps to execute (e.g., [2], [3], [4], [5]).
3. Click **[▶ Start Automated Task]**.

---

### 9. Pendulum & Overframe Post-Processing (Tab 8, `t8_pendulum`)

<img width="1095" height="853" alt="Post-Processing" src="https://github.com/user-attachments/assets/59a8b6b5-fd86-4b94-ab31-a6a1a9eb0c65" />

#### Technical Mechanisms and Operating Principles
This module serves as the tool's core image processing hub, offering 4 major processing modes and an extremely high-freedom layer rendering pipeline:
1. **Pendulum Card Art Post-Processing (`MODE_PENDULUM`)**: Fills the bottom of the image with a transparent background (based on the `pad_pct` ratio), correcting the square stretch distortion of Pendulum card arts in-game.
2. **Overframe Card Art Post-Processing (`MODE_OVERFRAME`)**:
   * **Single-Layer Refinement & Dual-Layer Compositing (-ch / -bg Logic)**: If the input images are named `[ID]-ch.png` (Character layer) and `[ID]-bg.png` (Background layer), the system automatically launches an advanced dual-layer workshop, allowing independent adjustment of character and background X/Y translation, scaling, and rotation. If it's a standard single image, it automatically executes 11:16 full-bleed cropping.
   * **Dynamic Z-Order Geometric Compositing**: Reads `CardFrame/` PSD files, allowing users to customize the top-to-bottom stacking order of 8 major layers (Character, Background, Outer Frame, Name Box, Art Frame, Effect Box, Effect Text Bar, Card Base Background).
   * **Foil Gloss and Mask Generation Matrix (Foil Studio)**: Built-in IQ Cosine Palette and dual-track blending system (Pegtop Soft Blend / Vivid Overdrive), providing four optical simulations: Pearl Pastel, Neon Spectrum, Champagne Gold, and Platinum Diamond. It independently controls Preview illumination, physical Baking, and Dirty Alpha transparency for each component.
3. **Card Animation Post-Processing (`MODE_CUTIN`)**: Reads PSD, MP4, GIF, or single static images.
   * **Chroma Key & Despill**: Built-in green screen removal algorithms featuring Despill color spill correction to suppress hue shifting from green reflections on character edges.
   * **Spine Bone Generation & PMA (Premultiplied Alpha)**: Generates Spine 4.2.43 compatible JSON animation data via a 4-point `popup_curve` timeline. Prior to export, it forces PMA execution to completely eliminate edge black line noise during Unity rendering, and automatically outputs HD and SD dual-spec atlases fitting a 16:9 ratio.
4. **Pendulum Original Art Processing (`MODE_PENDULUM_ORIGINAL_CROP`)**: Subjects the extracted distorted original game image to a 1.25x horizontal stretch and performs a 1:1 square crop from the top vertex to restore it.

#### Full Interface Components and Input Fields Details
* **Processing Mode (ComboBox)**: Switches between the 4 operating pipelines mentioned above.
* **Project and Path Settings Area**: Configures the CSV Dictionary, Project Root Directory, Modded Arts Position, and Original Art Position. Includes Pendulum fill ratio and backup folder naming controls.
* **Overframe Element Transparency Controls (Sliders)**: Fine-tunes the Alpha transparency (0~100%) for 6 major PSD components.
* **Foil Gloss and Mask Settings (Foil Studio)**:
  * **3x6 Control Matrix**: Controls whether 6 components like the Outer Frame and Name Box participate in "Preview Simulation", "Bake Texture", and "Transparent Mask (Alpha 0)".
  * **Optical Parameter Sliders**: Spectrum Style, Blending Mode, Pearlescent Base Lightness, Highlight Sharpness, Gloss Intensity, Color Density, Flare Frequency, and Lighting Angle.
* **Real-Time Preview Panel**: Provides single-frame light-speed memory frame extraction previews. Checking "Simulate In-Game Foil Gloss" allows real-time viewing of Foil algorithm overlay effects.
* **Advanced Dual-Layer Overframe Workshop (Exclusive for -ch / -bg)**:
  * Provides independent X/Y translation, scale, and rotation sliders for Character and Background layers.
  * Allows customizing a solid color backboard when there is no background via a color picker.
  * **Free Layer Sorting Panel (Z-Order)**: Change the 8 major layers' top-to-bottom coverage relationships freely via dragging or buttons.
* **Material and Canvas Settings Area (Exclusive for Cut-In Animations)**: Sets HD output resolution (1920x1080 / 1280x720), canvas fill mode (Crop to Fill / Fit with Borders / Stretch), rotation angle, and overall X/Y translation. Checking "Enable Hard Drive Temp (Prevent OOM)" avoids memory overflow when processing long videos.
* **Keyframe Preview Time Control Area (Exclusive for Cut-In Animations)**: Preview timestamp fine-tuning slider, providing quick buttons to jump to the Initial Point, Peak, Settle, and End Point.
* **Chroma Key and Color Correction Area (Exclusive for Cut-In Animations)**: Includes Chroma Key toggle, Despill toggle, and Key Color Palette. Provides sliders for Key Tolerance, Edge Feathering, Despill Strength, Brightness, Contrast, and Vignette Border Strength.
* **Time Control and POP UP Effects Area (Exclusive for Cut-In Animations)**: Sets Clip Start Time, Total Animation Length, Output FPS, and Playback Speed. Contains 4-point Spine scaling curve settings (Time and Size), and offers a "Generate Full-Size Real Preview GIF" feature.
* **Pending Task List (PlainTextEdit)**: Manually input or load qualified IDs via "Auto Scan Target Directory". Clicking an ID in the list automatically brings it into the preview path.

#### Independent Operations SOP for This Tab
* **SOP 8.1: Pendulum Image Fill and Original Art Restoration**
  1. Select Mode "Pendulum Card Art Post-Processing" or "Pendulum Original Art Processing".
  2. Click **[Auto Scan Target Directory]** to load IDs.
  3. Click **[🚀 Start Post-Processing]** to overwrite products.
* **SOP 8.2: Overframe Dual-Layer (-ch/-bg) Creation and Z-Order Adjustment**
  1. Name the background-removed character `12345-ch.png` and background `12345-bg.png`, placing them in the `Modded Arts/` directory.
  2. Select Mode "Overframe Card Art Post-Processing", click **[Auto Scan Target Directory]**.
  3. Select an item in the list and expand the Preview Panel.
  4. Expand "Advanced Dual-Layer Overframe Workshop", adjust character scale and translation, and drag the Z-Order panel to move "Effect Text Bar (EffBox)" to the very bottom to hide it.
  5. Expand "Foil Gloss and Mask Settings", check "Transparent Mask" for the Outer Frame and Art Frame to achieve a 3D character breaking-the-frame effect.
  6. Click **[🚀 Start Post-Processing]** to export the composite image and automatically jump to Tab 13.
* **SOP 8.3: Spine Cut-In Animation Chroma Key and Output**
  1. Select Mode "Card Animation Post-Processing".
  2. Place green screen videos (e.g., `p18533.mp4`) in `Modded Arts/`, click **[Auto Scan Target Directory]**.
  3. Click an ID in the text box to auto-load the preview, expand the Preview Panel.
  4. Check "Enable Chroma Key" and "Enable Despill", click **[🎨 Select Key Color]** to pick the background green. Adjust Tolerance and Despill Strength until character edges have no green glow.
  5. Set the 4-point POP UP scaling curve, click **[Generate Full-Size Real Preview GIF]** to verify the dynamic effect.
  6. Click **[🚀 Start Post-Processing]**. The system will execute PMA and export `-hd.png`, `-hd.atlas.txt`, `js-hd.json` along with corresponding SD atlases to `Modded Arts/`.

---

### 10. Quick Single-Card Mod (Tab 9, `t9_quick_mod`)

<img width="1095" height="848" alt="Single Card" src="https://github.com/user-attachments/assets/d357a412-561b-413a-9225-cfda5ad694aa" />

#### Technical Mechanisms and Operating Principles
Bypasses project creation, directly performing binary injection on a single file.
* **Lobby Background Overwrite (`MODE_LOBBY_BG`)**: Precisely targets the `ShopBGBase02` texture in `masterduel_Data/data.unity3d`, executes binary injection, and calls `gc.collect()` to force memory release.

#### Full Interface Components and Input Fields Details
* **Category Selection (ComboBox)**: "Standard Art Mod", "Overframe Art Mod", "Modify Lobby Background".
* **Search and Selection Area**: Reference Language menu, Search Box, Process Visual Objects Only toggle, Search List.
* **Dictionary (CSV) / Original File Source (0000) / Save Root Directory / New Image Path (Path Rows)**: Read/write paths.
* **Target Card ID (LineEdit)**: The Card ID to replace.
* **Directly Overwrite Game File (Checkbox)**: Dangerous operation; modifies the 0000 original file directly.

#### Button Functions Details
* **[Start Replacement]**: Executes single-file injection.
* **[Send to Overframe Art Post-Processing]**: In Overframe mode, carries the path and ID and jumps to Tab 8.

#### Independent Operations SOP for This Tab
* **SOP 9.1: Quick Single-Card Replacement**
  1. Select Category "Standard Art Mod".
  2. Search for the card in the Search Box, double-click to bring the ID into "Target Card ID".
  3. Select the replacement image in "New Image Path", click **[Start Replacement]**.
* **SOP 9.2: Lobby Background Overwrite**
  1. Select Category "Modify Lobby Background".
  2. Set "Original File Source (0000)" and "Save Root Directory".
  3. Select a high-resolution image in "New Image Path".
  4. Click **[Start Replacement]**. The modified `data.unity3d` will be generated in `Modified Files/`.

---

### 11. Overframe Card Register (Tab 13, `t13_overframe`)

<img width="1092" height="845" alt="Overframe" src="https://github.com/user-attachments/assets/900b1745-7aa6-4d1e-8a13-690644eacbf2" />

#### Technical Mechanisms and Operating Principles
Reads, writes, and decodes the `of_card_asset` registry that dictates Overframe rendering.
* **Pure Pristine Baseline (.pristine)**: Creates a read-only `.pristine` backup upon first load. All future writes calculate the net difference via "UI Content - pristine baseline", and then merge and resolve conflicts with the latest official data.

#### Full Interface Components and Input Fields Details
* **Dictionary (CSV) / Game Original File Source (0000) / Save Root Directory (Path Rows)**: Path settings.
* **Target Registry (Hash) (ComboBox)**: The Hash code of the current `of_card_asset`.
* **Registry for Merging (Path Row)**: An external registry used for the merge function.
* **Current Whitelist Loading and Management (First Block Text Box)**: Displays existing Overframe registered data inside the game.
* **Add Registration and Write (Second Block Text Box)**: For inputting Card IDs to add. Supports directly pasting formats extracted from Tab 2, or manual entry (Syntax format: `Trigger ID -> Target Base Image ID`. If no target base image, entering just `Trigger ID` suffices. The system automatically ignores text and comments starting with `#` or `=`).

#### Button Functions Details (10 Major Buttons)
1. **[🛠️ Manual Brute-Force Fix (For Post-Major Updates)]**: Scans 0000 directory to find the latest `of_card_asset` and automatically migrates the list.
2. **[📥 Load Existing Original File]**: Decodes binary and displays in the first block.
3. **[🧹 Clear Cache Registry]**: Deletes the `.pristine` baseline file.
4. **[💾 Save Existing Whitelist]**: Only saves modifications from the first block.
5. **[🔗 Merge with "Registry for Merging"]**: Merges an external registry and resolves conflicts.
6. **[🔍 Go to "Find Files" Page to Pick Cards]**: Carries data and jumps to Tab 2.
7. **[📜 Load History of Successful Registrations]**: Loads past registration footprint into the second block.
8. **[✨ Normalize Names]**: Reverse looks up CSV dictionary, auto-fills names, and aligns formatting.
9. **[🧹 Clear History]**: Deletes `registered_history.json`.
10. **[🚀 Verify Conflicts and Output File]**: Merges the first and second blocks, writes, and exports the Bundle.

#### Independent Operations SOP for This Tab
* **SOP 13.1: Add Overframe Card Registration**
  1. Set paths, click **[📥 Load Existing Original File]** to verify successful loading in the first block.
  2. Input IDs in the second block (or click **[🔍 Go to "Find Files" Page to Pick Cards]** to jump and pick, or click **[📜 Load History of Successful Registrations]** to load history).
  3. Click **[✨ Normalize Names]** to check naming formats.
  4. Click **[🚀 Verify Conflicts and Output File]**. The registry Bundle will be generated in `Project Directory/Modified Files/`.
  5. **Critical Physical Overwrite Step**: You must manually copy the `of_card_asset` Bundle inside `Modified Files/` and paste it back into the Game's 0000 directory (or virtually mount via Tab 11) for it to officially take effect in-game.
* **SOP 13.2: Delete Whitelist Items**
  1. Click **[📥 Load Existing Original File]**.
  2. Directly manually delete the target card rows inside the first block's text box.
  3. Click **[💾 Save Existing Whitelist]** (or [🚀 Verify Conflicts and Output File]); the updated Bundle will be generated in `Modified Files/`.
  4. **Critical Physical Overwrite Step**: Manually copy the Bundle back into the Game's 0000 directory (or virtually mount via Tab 11).

---

### 12. Graphical Gallery (Tab 12, `t12_gallery`)

<img width="1053" height="837" alt="Gallery" src="https://github.com/user-attachments/assets/2f553750-194c-4165-8ce7-420b45f93171" />

#### Technical Mechanisms and Operating Principles
Provides thumbnail previews and trace-less sandbox filtering for 8 major non-card assets.
* **Memory Lookup Cache Mechanism**: Upon initial loading, it extracts Texture2D from the AssetBundle to generate a cache. Subsequent loads will bypass Hard Drive I/O and render directly from the cache, vastly increasing viewing speed.
* **Inertia-less Grid Scrolling**: Introduces a linear scrolling filter for grid lists, achieving straight up-and-down web-style operation, thoroughly eradicating Qt's built-in scrolling bounce issues.
* **Sandbox Visual Filtering (`CAT_FILTER`)**: An exclusive temporary lifecycle container. When a batch of IDs is sent here from Tab 2, the system creates a dedicated sandbox cache. Users can perform graphical deletion operations here, and upon completion, losslessly return the streamlined list to Tab 2.
* **Double-Click Quick Single-Card Mapping**: Double-clicking any thumbnail item in the list will cause the system to automatically send that asset's true ID to Tab 9 (Quick Single-Card Mod) and automatically jump there.

#### Full Interface Components and Button Functions
* **Category Selection (ComboBox)**: Provides 8 filtering dimensions: Fields, Coins, Card Cases, Icon Frames, Icons, Protectors, Lobby Backgrounds, and File Filter (Sandbox Mode).
* **[Load Selected Category Thumbnails]**: Scans the reference table and generates/loads the cache rendering grid.
* **[🧹 Clear Gallery Cache]**: Safely deletes the `gallery_cache` folder to free up hard drive space.
* **[Send to "Find Files"]**: Sends the selected item and its associated variants (e.g., selecting the coin front will automatically package the coin back) to Tab 2's extraction list.
* **[Send to "Quick Single-Card Mod"]**: Sends the selected ID to Tab 9.
* **[✨ Confirm Modifications and Return]**: (Visible only in Sandbox mode) Returns the streamlined ID list back to Tab 2 and automatically destroys the sandbox.
* **Shortcut Operations**: After selecting an item, press `Delete` or `Backspace` to delete it; press `Ctrl+Z` to undo the deletion.

#### Independent Operations SOP for This Tab
* **SOP 12.1: Asset Viewing and Double-Click Quick Mod**
  1. Select a category (e.g., "Icons"), click **[Load Selected Category Thumbnails]**.
  2. Browse the grid to find the target asset, **directly double-click the thumbnail**, and the system will automatically carry the ID and jump to Tab 9 entering the single-card replacement flow.
* **SOP 12.2: Tab 2 Linked Sandbox Visual Culling**
  1. After loading a large number of IDs (or TXT) in Tab 2, click **[🔍 Visual Filtering]** to jump to this page's "File Filter" mode.
  2. The system automatically generates thumbnails for all files in the list.
  3. Marquee select inappropriate or mis-searched thumbnails, press `Delete` to remove them (press `Ctrl+Z` to undo if deleted by mistake).
  4. Click **[✨ Confirm Modifications and Return]**. The system will automatically return the streamlined, pure ID list back to Tab 2 and execute normalization alignment.

---

### 13. Mod Streaming Updater (Tab 10, `t10_updater`)

<img width="1101" height="841" alt="Updater" src="https://github.com/user-attachments/assets/6434cb46-c528-48d8-a799-486f0e45e16c" />

#### Technical Mechanisms and Operating Principles
Solves issues of black screens or crashes caused by major game updates breaking old Mods.
* **Inline Texture Injection**: Reads the "Latest Official Original File", zeros out its `m_StreamData` external links, and forcefully embeds the binary pixel data of the old Mod into the new version Bundle, completing a lossless upgrade.

#### Full Interface Components and Button Functions
* **1. Old Mod Directory / 2. Game Original File (0000) / 3. Output Root Directory (Path Rows)**: Path settings.
* **Overwrite Old Mod (Checkbox)**: Dangerous operation, directly replaces the old file.
* **[Start Streaming Fix]**: Executes binary injection.

#### Independent Operations SOP for This Tab: Old Mod Cross-Version Fix
1. Set the Old Mod Directory and the latest version 0000 Original File directory.
2. Click **[Start Streaming Fix]**. Repaired files will be exported to the `FIXED_MOD/` folder.

---

### 14. Virtual Mod Manager (Tab 11, `t11_virtual`)

<img width="1065" height="841" alt="Virtual" src="https://github.com/user-attachments/assets/53fa520d-d56b-43b5-ad74-b7a9a06cd143" />

#### Technical Mechanisms and Operating Principles
Uses Windows `os.symlink` to achieve copy-free, zero-hard-drive-footprint, sub-second toggling of modules.
* **Transaction Rollback**: Before creating links, renames original files to `.vanilla_backup` and records them in `symlink_state.json`. If a permission anomaly occurs, it instantly triggers a global rollback restoring original files.
* **Real-Time Hot-Reload Core Advantage**: After mounting the symlink, the symlink locks onto the physical file inside the Mod folder. While the game is open, if you modify and re-export packaged resources to that Mod folder, **the game will instantly read the newest data the next time that asset is played or loaded, without needing to remount, copy/paste files, or restart the game.**

#### Full Interface Components and Button Functions
* **Mod Storage Root Directory / Game 0000 Directory (Path Rows)**: Path settings.
* **Scan Depth (ComboBox)**: Maximum level to penetrate searching for `0000` (1~5).
* **Enabled and Disabled Lists (ListWidgets)**: Left side is enabled, right side is disabled.
* **[Refresh]**: Rescans the Mod root directory.
* **[>>] / [<<]**: Disable all / Enable all selected items.
* **[▲] / [▼]**: Adjusts enablement priority (Top overwrites bottom).
* **[▶ Apply and Save]**: Executes symlink mounting and backup.

#### Independent Operations SOP for This Tab: Virtual Mounting and Hot-Reload
1. Place multiple Mod folders into the "Mod Storage Root Directory".
2. Click **[Refresh]**, double-click items to move Mods you want to enable to the left list.
3. Click **[▶ Apply and Save]** (Administrator privileges required).
4. **Hot-Reload**: Keep the game open. If a new Bundle is repackaged via Tab 8 or Tab 4 into that Mod folder, the newest effect can be seen instantly the next time that asset is triggered in-game, without restarting the game.

---

## Chapter 3: Full-Scenario Real-World Case Library (End-to-End Workflows)

This chapter provides cross-tab combined workflow SOPs.

### Case 1: Creating a Standard Art Replacement Mod from Scratch
1. **Tab 1 (Scan)**: Set the 0000 directory, click **[Start Scan]** to generate `2DTexture_Mapping.csv`.
2. **Tab 2 (Find)**: Enter the card name or ID, add to list, click **[Start Extracting Original Files]** to copy binary files to `Original Files/`.
3. **Tab 3 (Extract)**: Click **[Start Extracting Contents]** to unpack and export editable PNGs to `Original Card Arts/`.
4. **Art Modification**: Use image software to modify the PNG, save it to `Modded Arts/`.
5. **Tab 4 (Replace)**: Click **[Start Replacement]**, writing new images back to the Bundle, exporting to `Modified Files/`.
6. **Tab 5 (Package)**: Check packaging options, click **[Start Packaging]** to generate a complete Mod zip file.

### Case 2: Upgrading a Normal Card into a Brand New Overframe Card
1. **Tab 1 -> Tab 2 -> Tab 3**: Follow the flow in Case 1 to extract the original card art.
2. **Tab 8 (Post-Processing)**: Select "Overframe Card Art Post-Processing", adjust the 5 PSD layer transparencies, click **[🚀 Start Post-Processing]**, generating an 11:16 Overframe composite into `Modded Arts/`.
3. **Tab 4 (Replace)**: Click **[Start Replacement]** to write the Overframe image back into the Bundle, exporting to `Modified Files/`.
4. **Tab 13 (Register)**: Click **[📥 Load Existing Original File]**, enter the Card ID in the second block, click **[✨ Normalize Names]**, then click **[🚀 Verify Conflicts and Output File]** to export `of_card_asset` to `Modified Files/`.
5. **Physical Overwrite**: Copy all Bundles inside `Modified Files/` and paste them back into the Game's 0000 directory (or mount via Tab 11).

### Case 3: Creating and Replacing a Card Cut-In Animation (Spine Cut-In) from Scratch
1. Prepare a static image, green screen video, or sequential images placed in a PSD or folder, name it `p18533.png` or `p18533.mp4`... and save it to `Modded Arts/`.
2. **Tab 8 (Post-Processing)**: Select "Card Animation Post-Processing", select Key Color and adjust Despill and POP UP curves, click **[🚀 Start Post-Processing]** to generate Spine atlases.
3. **Tab 4 (Replace)**: Click **[Start Replacement]** to write the animation back into the Bundle; the tool automatically calibrates Gamma color space.
4. **Tab 5 (Package)**: Package and release.

### Case 4: Fixing a Broken Overframe Registry After a Major Game Update
1. After a major game update, enter **Tab 13 (Register)**.
2. Click **[🛠️ Manual Brute-Force Fix (For Post-Major Updates)]**. The system auto-scans the newest 0000 directory for the latest Hash and seamlessly migrates historical registration lists.
3. Click **[🚀 Verify Conflicts and Output File]** to generate the newest registry Bundle.
4. Copy the exported Bundle back into the Game's 0000 directory.

### Case 5: Old Version Broken Mod Rescue and Hot-Testing
1. **Tab 10 (Updater)**: Set Old Mod Directory and the newest 0000 directory, click **[Start Streaming Fix]** to export fixed Bundles.
2. **Tab 11 (Virtual Mounting)**: Place the fixed Mod into the Mod Root Directory, click **[▶ Apply and Save]**. Open the game directly to verify, allowing real-time previews without restarting the game.

---

## Chapter 4: Advanced Engineering Techniques

### Advanced Technique 1: Reverse Scanning "Modified Files" to Quickly Export Mod List (TXT)
* **Scenario**: When you obtain a pre-made Mod pack or `Modified Files/` folder and wish to quickly acquire all Card IDs within it to bring into Tab 13 for Overframe registration or Tab 2 for referencing.
* **Operation SOP**:
  1. Go to **Tab 1 (Scan & Append)**.
  2. **Manually point the "Target Directory (0000)" path to "Modified Files" or the Mod folder**.
  3. Only check "Generate Content List (TXT)" and uncheck "Generate Reference Table (CSV)" to save time.
  4. Click **[Start Scan]**.
  5. The system will read all Bundles in that folder, reverse-extract all textures and asset IDs, and generate `Extracted_Names.txt` in the output directory.
  6. This TXT can be directly loaded into Tab 2 or pasted into Tab 13, saving the trouble of manual line-by-line entry.

### Advanced Technique 2: Ultra-Fast Animation/Art Hot-Testing without Restarting Using Virtual Mounting (Tab 11)
* After mounting the symlink, while the game is open, if you repackage resources into the Mod folder, the game will directly read the new data in real-time the next time that asset is played or loaded, without needing to remount, copy/paste, or restart the game.

### Advanced Technique 3: Bi-directional Flow with Tab 2 and Tab 12 Sandbox Visual Culling
* After entering batch IDs in Tab 2, click **[Search / Visual Filtering]** to jump to Tab 12, press `Delete` to remove mismatches, and click **[✨ Confirm Modifications and Return]** to automatically carry back the streamlined ID list, or you can double-click a targeted object to send it directly to Quick Single-Card Mod.

### Advanced Technique 4: Keyboard Shortcuts and Spacebar Forced Path Refresh Trick
* When a path linkage in Tab 2 doesn't immediately update to Tab 3, click inside the middle of the Tab 2 path input box, **press the spacebar once, and then delete that space**, to forcefully trigger a `textChanged` signal and complete a full-page path refresh.

---

## Chapter 5: Troubleshooting Guide

1. **`PermissionError: Insufficient Permissions`**
   * **Cause**: `2DTexture_Mapping.csv` is currently opened by Microsoft Excel or another program, preventing Python from acquiring a Write Lock.
   * **Solution**: Close Excel or the relevant editor and run it again.

2. **Out of Memory (OOM) or Interface Freezing**
   * **Solution**: Go to **Tab 7 (Settings & Appearance)** and lower the "Max Compute (Threads)" from `Auto` to 2 or 4. When processing animations, check "Enable Hard Drive Temp (Prevent OOM)".

3. **`.pristine` Baseline File Protection and Restoration**
   * **Warning**: Do not randomly delete `.pristine` files inside `MD_Tool_Temp/of_card_asset_backups/`. If the baseline file is lost and anomalies occur, click **[🛠️ Manual Brute-Force Fix]** in Tab 13 to rebuild the newest baseline.