<p align="center"></p>

<p align="center"><img src="src/assets/logo.png" width="256" height="256" alt="logo" /></p>
<p align="center">
  Immich-Deduper<br/>
  <small>(Previously: Immich MediaKit)</small>
</p>
<p align="center">
<small>
duplicate photo finder and remover for <a href="https://github.com/immich-app/immich">Immich</a>.<br/>
Find and remove similar/duplicate images using deep learning.
</small>
</p>
<p align="center">
<a href="https://buymeacoffee.com/razgrizhsu" target="_blank"><img src="https://img.shields.io/badge/Buy%20Me%20A%20Coffee-Support-yellow.svg?style=flat-square&logo=buy-me-a-coffee" alt="Buy Me A Coffee"/></a>
</p>

## Features

- **Visual Similarity Detection**: Find duplicates by how photos look
- **Search from Photo**: Find similar photos starting from any specific image
- **Multi Mode**: Process up to 50 duplicate groups at once
- **Cross-User Detection**: Find duplicates across multiple Immich users
- **Flexible Threshold**: Adjust from exact duplicates (0.97+) to similar shots (0.60+)
- **Auto-Selection**: Pick best photo by date, size, EXIF, and more
- **Related Tree**: Discover connected similarities - find photos related to related photos
- **Exclude Filters**: Skip specific extensions (.dng, .png) or filename patterns
- **Safe Deletion**: Removed photos go to Immich trash, fully recoverable
- **Metadata Merge** *(BETA)*: Transfer metadata from deleted photos to kept ones (albums, favorites, tags, rating, description, location)


## Preview

<p align="center">
<img src="docs/intro.jpg" alt="preview" />
</p>

### Processing
<p align="center">
<img src="docs/intro.gif" alt="preview" />
</p>

---

## How It Works

1. Fetches Users & Assets data from the Immich PostgreSQL database
2. Processes images through ResNet152 to extract feature vectors
3. Stores vectors in the Qdrant vector database
4. Uses vector similarity to identify similar/duplicate photos
   - **Multi-user scope**: Duplicate detection operates across all imported users
   - Import single user: duplicates detected within that user only
   - Import multiple users: duplicates detected across all imported users
5. Displays similar photo groups based on the configured threshold
6. Manages asset deletion by updating Immich database directly:
   - Follows Immich's deletion logic for compatibility
   - **Important**: Enable trash feature in Immich settings first
   - Deleted assets appear in Immich's trash where you can permanently delete or restore them


---

### Metadata Merge (BETA)

<p align="center">
<img src="docs/metadata.jpg" alt="metadata" />
</p>

> ⚠️ **This feature is experimental and under active testing.**
> If you are not willing to participate in testing and accept potential risks, please do not enable this feature.
>
> **Safe Testing:**
> 1. Copy a photo to create fake duplicates
> 2. Upload copies to Immich and add different metadata to each (albums, tags, ratings)
> 3. Run Deduper and use Metadata Merge
> 4. Verify the kept photo has merged metadata from all copies
>
> Do not test on photos you care about.

When deleting duplicates, Metadata Merge can transfer metadata from deleted photos to kept ones:

- **Albums**: Add kept photos to all albums that contained any photo in the group
- **Favorites**: Mark kept photos as favorite if any photo was favorited
- **Tags**: Merge all tags from the group to kept photos
- **Rating**: Apply highest rating from the group
- **Description**: Merge descriptions (deduplicated line by line)
- **Location**: Apply most common GPS coordinates
- **Visibility**: Apply strictest visibility setting (locked > hidden > archive > timeline)

**How It Works:**

1. **Database Update**: Writes merged metadata directly to Immich PostgreSQL database
2. **XMP Sidecar**: Creates/updates `.xmp` sidecar files alongside kept photos with:
   - Description, Rating, GPS coordinates, Tags
   - Prevents Immich's "Refresh Metadata" from overwriting merged values
3. **Atomic Operation**: All changes (DB + XMP) are committed together; if any step fails, everything rolls back

**Requirements:**
- **exiftool CLI**: Required for XMP sidecar writing
  - Docker: Pre-installed
  - Source install: `brew install exiftool` (macOS) or `apt install libimage-exiftool-perl` (Linux)
- **File Access**: Deduper needs write permission to photo directories for XMP files

**Important Notes:**
- **External Libraries**: Configure library paths in Fetch page before using Metadata Merge
- **Backup XMP**: Existing `.xmp` files are backed up to `.xmp.bak` during merge; restored on failure, removed on success
- **New XMP Files**: For photos without existing sidecar, Deduper creates new `.xmp` and updates Immich's `sidecarPath`
- **Immich Sync**: After merge, Immich will read the XMP sidecar on next "Refresh Metadata" without losing merged values

**Troubleshooting:**
- Check logs at `DEDUP_DATA/logs/` for detailed error messages
- Common errors:
  - `exiftool CLI not found`: Install exiftool (see Requirements above)
  - `File not found`: Configure external library paths in Fetch page
  - `No write permission`: Ensure Deduper has write access to photo directories

⚠️ **Warning**: This feature writes directly to Immich database and creates XMP sidecar files. Always backup your database and photos before use.

---

## Usage Guide

### Basic Operations

- `Find Similar`
  - Starts searching for the next photo that matches your `Threshold Min` settings and shows it in the `current` tab
  - When photo groups appear in the `current` tab, you can click on a photo's header to select it. This lights up the four action buttons on the top right. After using one of these actions, the kept photos in that group will be marked as resolved
  - If you don't do anything with a searched group, it'll show up in the `pending` tab waiting for you to handle it later

- `Clear records & Keep resolved`
  - Clears out search records that haven't been resolved yet
  - This keeps all the records you've already marked as resolved

- `Reset records`
  - Resets all search records, including the ones you've marked as resolved


### Search Configuration

- `Path Filter`
  - Only show groups where at least one asset's path contains the filter pattern
  - Useful for focusing on duplicates within a specific folder or external library
  - Groups not matching the filter are auto-resolved. Use `Reset Records` to search them again

- `Exclude Settings`
  - **Similar Less**: Auto-resolve groups with fewer than N similar photos and continue search
    - Example: Setting "< 2" means skip groups with 1 or 0 similar photos (requires at least 3 total photos)
    - Useful for focusing only on groups with enough duplicates to warrant attention
  - **NameFilter**: Exclude specific files from similarity search by filename patterns or extensions
    - **Extension format**: `.png,.gif,.dng` - Files with these extensions won't be selected as main image or appear in similar results
    - **Filename pattern**: `IMG_,DSC,screenshot` - Files containing these patterns will be excluded
    - **Mixed format**: `.png,IMG_,screenshot` - Combine extensions and patterns
    - **Use case**: Perfect for drone photography where you shoot both RAW (.dng) and JPEG simultaneously but want to keep both formats without them being flagged as duplicates

- Make the most of `Auto Selection`
  - When you enable auto selection, it'll automatically choose which photos to keep or delete after you run `Find Similar`. Just scroll through to review, then hit one of the four action buttons at the top

- `Multi Mode` search feature
  - By default (when `Multi Mode` is off), it only searches for one group of photos at a time
  - Turn this on and set the `Max Group` number when you've got tons of photos to filter through - super handy for big cleanups
  - **Note: Multi Mode and Related Tree are mutually exclusive**

- `Related Tree`
  - **Only available in single group mode (when Multi Mode is off)**
  - When `Related Tree` is off, `Find Similar` only shows photos directly related to the main photo
  - Turn it on and it'll also search for photos related to those related photos, creating a comprehensive similarity tree
  - **Cannot be used together with Multi Mode for performance and clarity reasons**
  - `MaxItems` limits how deep the search goes. Say you set the threshold to `(0.5, 1)` - that might trigger endless searching if you have 100k photos, so this cap keeps things under control
  - Note: The number of photos directly related to the main photo isn't limited by `MaxItems`

**Mode Selection**: Choose Single Mode + Related Tree for comprehensive similarity trees, or Multi Mode for quick processing of multiple separate groups.

---

### Auto Selection

Automatically select the best photo in each duplicate group based on configurable criteria.

<p align="center">
<img src="docs/ausl.png" alt="Auto Selection showing selection reason tooltip" />
</p>

- Each criterion has a weight (0-5). Score = weight × 10
- The photo with the highest total score in each group gets selected
- Selected photos show an "Auto-Selected ？" badge, Hover to see the scoring breakdown
- Each group header has an "auto select log" button, Click to view detailed scoring for all photos
- Settings changes trigger automatic recalculation

**Selection Criteria:**

| Category | Criterion | Description |
|----------|-----------|-------------|
| **Options** | Skip Low Similarity | Skip groups containing photos with similarity < 0.96 |
| | All LivePhotos | Select all LivePhoto assets in group (ignores other criteria) |
| **DateTime** | Earlier / Later | Prefer photos taken earlier or later |
| **EXIF** | Rich / Poor | Prefer photos with more or fewer EXIF fields |
| **Filename** | Longer / Shorter | Prefer longer or shorter filenames |
| **FileSize** | Bigger / Smaller | Prefer larger or smaller file sizes |
| **Dimension** | Bigger / Smaller | Prefer higher or lower resolution |
| **FileType** | JPG / PNG / HEIC | Prefer specific file formats |
| **Immich** | Favorite / In Album | Prefer photos marked as favorite or added to albums |
| **User** | Priority User | Prefer photos owned by a specific Immich user |
| **Path** | Contains | Prefer photos whose path contains a specific string |


**Tips:**
- Use "Earlier" + high weight when you want to keep original captures over edited versions
- Use "Path Contains" to prioritize photos from a specific folder (e.g., `/library/keep/`)
- Combine multiple criteria: FileSize+3, Earlier+2 gives preference to larger files, with date as tiebreaker
- Toggle Enable off/on to clear and re-run auto-selection



---

### Advanced Strategies

- **Progressive cleaning approach**
  - Start with the highest similarity threshold and work your way down:
    - First, get rid of exact duplicates `(0.97-1.00)`
    - Then find near-duplicates `(0.90-0.97)`
    - Finally, catch similar but different shots `(0.80-0.90)`
  - This way you tackle the obvious duplicates first, then deal with the photos that need more careful judgment

- **Clear and rescan strategy**
  - Before changing your threshold settings, use `Reset Records` to wipe all similarity data
  - This lets you rescan all photos with new thresholds and avoid missing anything or getting false matches

- **Auto Selection workflow**
  - See [Auto Selection](#auto-selection) for detailed criteria configuration
  - Recommended: Set criteria first, then run Find Similar to see pre-selected results
  - Always review auto-selected photos before using batch actions

- **Large collection tips**
  - For 8000+ photos: Enable Multi Mode with appropriate Max Group settings
  - Use batch operations for efficiency

- **Finding similar content (reverse approach)**
  - For finding similar themes (memes, similar scenes, burst shots):
    - Start with low threshold (0.60-0.70) + `Multi Mode` with limited `Max Group`
    - Progressively raise threshold to filter out less similar matches
  - This is the reverse of duplicate cleaning - work your way up instead of down
  - Always limit `Max Group` when using low thresholds to avoid overwhelming results

- **External library considerations**
  - Ensure external library paths are not set to read-only if using Docker Compose
  - Enable Immich's recycle bin feature before processing external libraries
  - Remember that Deduper reads from Immich thumbnails, so original file locations don't affect similarity detection

---

## System Startup

When Deduper starts up, it performs several system checks as shown below:

<p align="center">
<img src="docs/chk.gif" alt="System startup checks" />
</p>

**Important startup notes:**
- Pay attention to the startup messages displayed during initialization
- The system will show proper status indicators and perform version checks
- If any components are outdated or incompatible, you'll receive update prompts
- Ensure all checks pass before proceeding with operations

If you encounter any startup errors or version mismatches, follow the update instructions above or check the logs for detailed error information.

### **Why Deduper Connects to the Internet:**
- **Version Check**: Compares local version with GitHub to notify you of updates
- **Immich Logic Verification**: Validates that Deduper's delete/restore operations match Immich's current implementation, preventing potential data corruption from API changes

For air-gapped environments, see [Offline Mode](#offline-mode).

---

## Installation & Setup

### Installation Method Selection Guide

Choose the installation method that suits your needs:

| Installation Method | Use Case | Advantages | Disadvantages |
|---------------------|----------|------------|---------------|
| **Docker Compose (CPU)** | Non-GPU hosts, smaller image | One-click install, auto Qdrant setup, smaller image size | CPU processing only |
| **Docker Compose (GPU)** | Linux users with NVIDIA GPU | One-click install, auto Qdrant setup, GPU acceleration | Linux + NVIDIA GPU only |
| **Source Installation** | Custom environment, development | Multi-platform GPU support (CUDA/MPS), customizable | Manual Qdrant and dependency setup |

**Recommended Choice:**
- **Linux users with NVIDIA GPU**: Use Docker Compose (GPU version, default image tag)
- **Non-GPU hosts or smaller image needs**: Use Docker Compose (CPU version)
- **macOS users needing GPU**: Use source installation (MPS support)
- **Custom development or specific requirements**: Use source installation

### Prerequisites

- Access to an Immich installation with trash feature enabled
- A configured `.env` file (see below)

### Set up your Immich database
Before you can use deduper, you need to set your database up, so Deduper can connect to it. This explanation covers only Immich installations via docker compose.

#### Immich on the same host as deduper
If your Immich installation is on the same machine than you want to install Deduper on, a docker network can be used to connect to the db.
To create the network execute the following command (on the host, not in the docker container):
```bash
docker network create immich-deduper
```

Then add the network to your immich database container and to the docker compose:
```yaml
services:
  database:
    container_name: immich_postgres
    image: ghcr.io/immich-app/postgres:14-vectorchord0.3.0-pgvectors0.2.0
    networks: # Add the immich-deduper network to the db to allow immich-deduper to access the db
      - immich-deduper


networks: # Add the immich-deduper network to the immich docker compose without any indentation
  immich-deduper:
    external: true
```

After updating, restart Immich to apply the changes. The `PSQL_HOST` in your `.env` file should match the container name of the database.

#### Immich on a different host as deduper
If your Immich installation is on a different machine than you want to install Deduper on, you need to expose the PostgreSQL port. Note that this exposes your database to anyone in the hosts network, so use a secure password!
Add the following port mapping to your Immich's docker compose:

```yaml
services:
  database:
    container_name: immich_postgres
    image: ghcr.io/immich-app/postgres:14-vectorchord0.3.0-pgvectors0.2.0
    ports:
      - "5432:5432"  # Add this line to expose PostgreSQL
```

After updating, restart Immich to apply the changes. The exposed port (5432 in this example) should match the `PSQL_PORT` setting in your Deduper `.env` file.


### Option 1: Docker Compose
Using Docker Compose is the easiest installation method, automatically including the Qdrant vector database.

**Installation Steps:**

1. **Copy Docker Configuration Files**

   The compose has a few differences when you're installing Deduper on the same host vs on a different host than Immich. Choose the same as you have for setting up the database.

   **Same host configuration:**
   - [docker-compose.yml](./docker/same-host/docker-compose.yml)
   - [docker-compose-immich.yml](./docker/same-host/docker-compose-immich.yml)
   - [.env](./docker/same-host/.env)

   **Different host configuration:**
   - [docker-compose.yml](./docker/different-host/docker-compose.yml)
   - [docker-compose-immich.yml](./docker/different-host/docker-compose-immich.yml)
   - [.env](./docker/different-host/.env)

2. **Configure Environment Variables**

   Choose the appropriate `.env` file based on your setup and modify:
   - `PSQL_HOST`: Database connection (service name for same-host, IP address for different-host)
   - `IMMICH_PATH`: Path to your Immich upload directory
   - `IMMICH_THUMB`: (Optional) Path for separate thumbnail directory (requires additional volume mount)
   - `DEDUP_DATA`: Directory for Deduper data storage
   - `DEDUP_IMAGE`: Deduper image tag to run (`latest` default CPU, `latest-cuda`, or `latest-cpu`)
   - `QDRANT_URL`: (Optional) Custom Qdrant database URL for non-Docker environments or custom container setups
   - `OFFLINE`: (Optional) Set to `true` for air-gapped environments (see [Offline Mode](#offline-mode))

3. **Create Docker Network (Same-host only)**

   If using same-host setup, create the shared network:
   ```bash
   docker network create immich-deduper
   ```

4. **Update Immich Configuration (Required)**

   Modify your existing Immich docker-compose.yml file according to the example provided:
   - **Same-host**: Add networks configuration to enable communication
   - **Different-host**: Expose PostgreSQL port for external access

5. **Choose Image Tag**

   Set `DEDUP_IMAGE` in your `.env`:

   ```env
   # Default (CPU)
   DEDUP_IMAGE=razgrizhsu/immich-deduper:latest
   ```

   ```env
   # Much smaller image size (CPU only)
   DEDUP_IMAGE=razgrizhsu/immich-deduper:latest-cpu
   ```

   If using a GPU image (`latest-cuda`), add (or uncomment) GPU device reservation in `docker-compose.yml`:

   ```yaml
   deploy:
     resources:
       reservations:
         devices:
           - driver: nvidia
             count: 1
             capabilities: [gpu]
   ```

   **Prerequisites for CUDA image:**
   - NVIDIA GPU with CUDA support
   - NVIDIA Container Toolkit / Docker GPU runtime installed
   - Linux host system

   **Note:** Docker GPU support is Linux + NVIDIA only. For macOS MPS or Windows GPU acceleration, use source installation.

6. **Start Services**
   ```bash
   docker compose up -d
   ```

7. **Access Application**
   - Open browser to `http://localhost:8086`

8. **Updating Deduper**
   To update Deduper when using Docker Compose, run:
   ```bash
   docker compose down && docker compose pull && docker compose up -d
   ```

   To switch between tags (for example CPU -> CUDA), update `DEDUP_IMAGE` in `.env` and then run:
   ```bash
   docker compose down && docker compose pull && docker compose up -d
   ```

### Docker Image Tags

- `latest`: default CPU image tag (compose default)
- `latest-cuda`: explicit CUDA-enabled image for Linux + NVIDIA GPU
- `latest-cpu`: CPU-only image, much smaller than CUDA

If you build locally, you can create equivalent tags:

```bash
# CPU
docker build -t immich-deduper:latest-cpu --build-arg DEVICE=cpu .

# CUDA
docker build -t immich-deduper:latest-cuda --build-arg DEVICE=cuda .

```


### Option 2: Source Installation
For custom environments and development needs.

**Use Cases:**
- Want to customize Python environment
- Need to modify source code
- Prefer manual control over dependencies

**Installation Steps:**

1. **Install Qdrant Server**
   ```bash
   # Install Qdrant using Docker
   docker run -p 6333:6333 qdrant/qdrant:v1.16.3
   ```

2. **Clone Source Code**
   ```bash
   git clone https://github.com/RazgrizHsu/immich-deduper.git
   cd immich-deduper
   ```

3. **Configure Environment Variables**
   Create `.env` file and set connection information (refer to the example above)

4. **Install Python Dependencies**
   
   **CPU/macOS-compatible version (default):**
   ```bash
   pip install -r requirements.txt
   ```

   **GPU acceleration:**
   ```bash
   # Linux with NVIDIA GPU (CUDA)
   pip install -r requirements-cuda.txt
   
   # macOS with Apple Silicon (MPS)
   pip install -r requirements.txt
   
   # Windows with NVIDIA GPU
   pip install -r requirements-cuda.txt
   ```

   **Platform-specific notes:**
   - **Linux**: Install CUDA drivers and corresponding PyTorch version first
   - **macOS**: Apple Silicon automatically supports MPS acceleration
   - **Windows**: Requires NVIDIA GPU and CUDA drivers
   - May need additional system packages: `sudo apt-get install python3-dev libffi-dev` (Linux)

5. **Start Application**
   ```bash
   python -m src.app
   ```

---

### Environment Variables Reference

**Path Variables:**
- `DEDUP_DATA`: Deduper data directory (database, logs, cache).
  - **Docker**: Compose mounts to `/app/data`.
  - **Source**: Used directly.
- **Docker**:
  - `IMMICH_PATH`: Your Immich `UPLOAD_LOCATION` path (folder containing `thumbs`, `library`). Compose mounts it to `/immich`.
  - `IMMICH_THUMB`: (Optional) Separate thumbnail directory. Compose mounts it to `/thumbs`.
- **Source**: `IMMICH_PATH`, `IMMICH_THUMB` refer directly to your filesystem paths.

**Path Mapping (Docker only):**
> If your Immich database stores original host paths (e.g., `/mnt/photos/upload/...`),
> Deduper automatically detects and translates them to container paths (`/immich/...`).

---

## Offline Mode

For air-gapped environments without internet access, Deduper supports offline operation.

**Setup Steps:**

1. **Download Model Weights** (on a machine with internet)
   ```bash
   # Using the provided script (downloads to project_root/data/models/checkpoints/)
   python scripts/download-model.py

   # Or specify custom path via environment variable
   DEDUP_DATA=/your/path python scripts/download-model.py

   # Or manually download ResNet152 weights
   # Check the download URL from: python -c "from torchvision.models import ResNet152_Weights; print(ResNet152_Weights.DEFAULT.url)"
   ```

2. **Transfer Files to Offline Environment**
   - Copy `data/models/` directory (or your custom `DEDUP_DATA/models/`) to the offline machine's `DEDUP_DATA/models/`

3. **Enable Offline Mode**
   ```bash
   # In your .env file
   OFFLINE=true
   ```

**What Offline Mode Does:**
- Skips GitHub version checks
- Skips Immich logic verification
- Uses locally cached model weights
- All core functionality remains available

**Note:** In offline mode, you are responsible for ensuring version compatibility between Deduper and Immich.

---

## Logging

Deduper automatically logs system operations and errors to help with troubleshooting.

**Log Location:**
- Logs are stored in the `DEDUP_DATA/logs/` directory
- Log files are rotated daily for better organization

**Troubleshooting:**
- If you encounter any issues or unexpected behavior, check the log files in the logs directory
- The logs contain detailed information about system operations, errors, and warnings
- Log files can help identify configuration issues, database connection problems, or processing errors

---

## Version Compatibility

**Deduper v0.1.11+** supports all Immich versions through automatic schema detection.

**Automatic Schema Detection:**
Deduper automatically detects and adapts to your Immich database schema:
- Table names (plural vs singular: assets/asset, albums/album, tags/tag, users/user)
- Junction table column names (plural vs singular: albumsId/albumId, assetsId/assetId, tagsId/tagId)

No manual configuration needed - Deduper works seamlessly across all Immich versions.

**Immich Schema Evolution:**
- **Immich v1.136.0**: Changed main table names from plural to singular (assets → asset, albums → album, tags → tag, users → user)
- **Immich v2.3.0**: Changed junction table column names from plural to singular (albumsId → albumId, assetsId → assetId, tagsId → tagId)
- Deduper automatically handles all these variations

---



## Developer Notes

Initially, I was planning to build this with Electron + React frontend + Node.js backend, but given how much easier it is to integrate machine learning stuff with Python, I ended up going the Python route.

I usually use Gradio for quick AI demos, but it gets pretty limiting when you want more customization. Same story with Streamlit - they're great for prototypes but not so flexible for complex UIs. After trying a bunch of different options, I settled on Dash by Plotly. Sure, it still needs a lot of custom work to get exactly what I want, but it gets the job done pretty well.

What started as a simple little tool to help me clean up duplicate photos somehow turned into this whole complex system... funny how these things grow, right?

Hope this tool helps anyone who's dealing with the same photo organization headaches! :)

by raz


## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

If you find this project helpful, consider buying me a coffee:

[![Buy Me A Coffee](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://buymeacoffee.com/razgrizhsu)

## License

This project is licensed under the [GNU General Public License v3.0 (GPLv3)](https://www.gnu.org/licenses/gpl-3.0.en.html).

Commercial use is permitted, but any derivative works must also be open-sourced under the same license. If you modify and distribute this software, you must make your source code publicly available.

## Disclaimer

This tool interacts with your Immich photo library and database.
While designed to be safe, it is still under active development and may contain unexpected behaviors.
Please consider the following:

- Always backup your Immich database before performing operations that modify data
- Use the similarity threshold carefully when identifying duplicates to avoid false positives
- The developers are not responsible for any data loss that may occur from using this tool

Immich-Deduper is provided "as is" without warranty of any kind. By using this software, you acknowledge the potential risks involved in managing and potentially modifying your photo collection.

Happy organizing! I hope this tool enhances your Immich experience by helping you maintain a clean, duplicate-free library.
