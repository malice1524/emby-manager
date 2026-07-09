# File Organizer Published-Date Artwork and NFO Design

## Goal

Make the File Organizer workflow handle PornHub downloads produced by MeTube with filenames like:

```text
2025-07-16_Title_68781106ba7d5.mp4
2025-07-16_Title_68781106ba7d5.jpg
```

The organizer should let the user translate titles first, then assign episode numbers by PornHub published date from oldest to newest, move/rename the video, rename the matching episode artwork, and generate an episode NFO with the same title and published date.

## Non-Goals

- Do not call PornHub during organization.
- Do not require `.info.json` metadata for the first implementation.
- Do not change the existing NFO automation image-upload workflow.
- Do not automatically push to GitHub.

## Inputs

The source directory is under the configured Cloud115 root and contains completed videos. A video may have a matching image in the same directory.

Supported video suffixes remain the existing `VIDEO_SUFFIXES`.

Supported artwork suffixes should use the existing metadata/image suffixes:

```text
.jpg .jpeg .png .webp
```

Published date is parsed from the beginning of the video filename. Supported forms:

```text
YYYY-MM-DD_Title_id.mp4
YYYYMMDD_Title_id.mp4
```

The normalized date stored in API responses and NFO output is `YYYY-MM-DD`.

## Matching Artwork

Artwork matching is deterministic and does not depend on list order.

For each video, find one image in the same directory using this priority:

1. Same stem as the video: `video.stem + image_suffix`.
2. Same PornHub viewkey if both names contain a trailing 11-16 character alphanumeric id before the extension.

If no image is found, organization can still proceed; the row should show that artwork is missing.

When a matching image exists and the video is executed, the image is copied or moved with the video to the same final stem:

```text
Actor.S01E01.Chinese Title.mp4
Actor.S01E01.Chinese Title.jpg
```

Use `rename`/move for image files to match existing video move behavior. Precheck must reject target image collisions.

## Sorting and Episode Assignment

Add a scan sort option for published date:

```text
published_date
```

For `published_date`, rows with a parsed date sort first by:

```text
published_date asc, natural filename, relative path
```

Rows without a parsed date sort after dated rows by:

```text
mtime asc, natural filename, relative path
```

The frontend keeps the existing behavior where the displayed row order determines episode numbers:

```text
episode = startEpisode + rowIndex
```

After translation, row order stays unchanged unless the user rescans or manually moves rows. Chinese titles do not affect ordering.

## Final Filename

The final video filename continues to use the existing pattern:

```text
Actor.S01E02.Chinese Title.ext
```

The original date prefix and original viewkey are not included in the final media filename.

## Episode NFO Generation

Add an option in File Organizer:

```text
Generate episode NFO
```

When enabled, `plannedItems()` includes NFO information for each row:

- title: final Chinese title, falling back to original title
- season
- episode
- published_date when available
- target_nfo_path: same final stem with `.nfo`

Execution writes a same-stem `.nfo` after the video move succeeds. NFO format:

```xml
<episodedetails>
  <title>Chinese Title</title>
  <season>1</season>
  <episode>1</episode>
  <aired>2025-07-16</aired>
  <premiered>2025-07-16</premiered>
</episodedetails>
```

If no published date exists, omit `aired` and `premiered` rather than writing an invalid date.

Precheck must reject existing NFO target paths when generation is enabled.

## API Changes

`POST /api/file-organizer/scan` accepts existing `sort`, now including `published_date`.

Each scan item adds:

```json
{
  "published_date": "2025-07-16",
  "published_date_source": "filename",
  "artwork_path": "/CloudDrive115/.../2025-07-16_Title_id.jpg",
  "artwork_name": "2025-07-16_Title_id.jpg",
  "artwork_suffix": ".jpg"
}
```

When not found, nullable fields are empty/null and `published_date_source` is empty.

`precheck` and `execute` accept optional fields per item:

```json
{
  "target_artwork_path": "/CloudDrive115/.../Actor.S01E01.Title.jpg",
  "target_nfo_path": "/CloudDrive115/.../Actor.S01E01.Title.nfo",
  "nfo": {
    "title": "Title",
    "season": 1,
    "episode": 1,
    "published_date": "2025-07-16"
  }
}
```

## Frontend Changes

- Add sort option: `按发布时间从早到晚`.
- Show `发布时间` and `图片` columns in the scan table.
- Add `生成每集 NFO` checkbox in the confirmation section.
- In planned items, include target artwork and target NFO when applicable.
- The final preview remains based on current table order.

## Error Handling

- Missing published date is allowed; row is sorted after dated files and displays `未识别`.
- Missing artwork is allowed; row displays `无同名图片`.
- Existing target video, artwork, or NFO paths fail precheck.
- Video move failure skips image move and NFO write for that row.
- Image move failure marks that row failed even if the video moved; log records the error.
- NFO write failure marks that row failed; log records the error.

## Tests

Add backend tests for:

- Parsing `YYYY-MM-DD` and `YYYYMMDD` filename dates.
- Published-date sorting with undated fallback.
- Same-stem artwork matching.
- Viewkey artwork matching fallback.
- Precheck target collision for artwork and NFO.
- Execute moves video and artwork and writes NFO.

Add frontend tests for:

- Published-date sort option exists.
- Scan table shows published date and artwork columns.
- Generate NFO checkbox exists.
- `plannedItems()` includes artwork and NFO targets.
