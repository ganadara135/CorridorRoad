<!-- SPDX-License-Identifier: LGPL-2.1-or-later -->
<!-- SPDX-FileNotice: Part of the Corridor Road addon. -->

# CorridorRoad Wiki TOC (Draft)

This folder contains draft pages to publish to GitHub Wiki.

## Page List
1. `Home.md`
2. `Quick-Start.md`
3. `Workflow.md`
4. `Menu-Reference.md`
5. `Screenshot-Checklist.md`
6. `CSV-Format.md`
7. `Troubleshooting.md`
8. `Developer-Guide.md`
9. `_Sidebar.md`

## Page Purpose
| Page | Purpose | Main Audience |
|---|---|---|
| `Home.md` | Top-level entry and navigation | All users |
| `Quick-Start.md` | First successful run in 10-15 minutes | New users |
| `Workflow.md` | End-to-end command sequence and data flow | Designers |
| `Menu-Reference.md` | Detailed option meaning for key task panels | Daily users |
| `Screenshot-Checklist.md` | Capture plan and file-by-file screenshot checklist | Documentation maintainers |
| `CSV-Format.md` | Point cloud/alignment CSV schema and validation rules | Survey + design users |
| `Troubleshooting.md` | Known issues and direct fixes | All users |
| `Developer-Guide.md` | Code map, object responsibilities, and update policy | Developers |
| `_Sidebar.md` | Wiki side navigation | All users |

## Publish Order
1. Publish `Home.md` and `_Sidebar.md` first.
2. Publish `Quick-Start.md` and `CSV-Format.md`.
3. Publish `Workflow.md`, `Menu-Reference.md`, and `Screenshot-Checklist.md`.
4. Publish `Troubleshooting.md`.
5. Publish `Developer-Guide.md`.

## Draft-to-Wiki Sync Notes
1. Enable GitHub Wiki in repository settings first.
2. Clone wiki repo: `https://github.com/ganadara135/CorridorRoad.wiki.git`
3. Copy files in `docs/wiki/*.md` to wiki repo root.
4. Commit and push.

## Current Sample Files For Testing
- `tests/samples/pointcloud_utm_realistic_hilly.csv`
- `tests/samples/alignment_utm_realistic_hilly.csv`
- `tests/samples/structure_utm_realistic_hilly.csv`

## Screenshot Collection Plan
1. Capture one screenshot per major workflow stage.
2. Use file naming prefix: `wiki-<page>-<topic>.png`.
3. Store originals in a local staging folder, then upload to GitHub Wiki image path.

## Wiki Image Markdown Template
Use this format in wiki pages after uploading images to `images/`:
`![Screenshot Title](images/wiki-page-topic.png)`
