---
name: mermaid
repo: mermaid-js/mermaid
ref: develop
commit: 3f5f7a6781cc8c788b8b5fa3d4e62edce9288f60
source_path: packages/mermaid/src/docs/config/tidy-tree.md
title: Tidy-tree Layout
version: 0.0.0
fetched_at: 2026-09-13
---
# Tidy-tree Layout

The **tidy-tree** layout arranges nodes in a hierarchical, tree-like structure. It is especially useful for diagrams where parent-child relationships are important, such as mindmaps.

## Features

- Organizes nodes in a tidy, non-overlapping tree
- Ideal for mindmaps and hierarchical data
- Automatically adjusts spacing for readability

## Example Usage

```mermaid-example
---
config:
  layout: tidy-tree
---
mindmap
root((mindmap is a long thing))
  A
  B
  C
  D
```

```mermaid-example
---
config:
  layout: tidy-tree
---
mindmap
root((mindmap))
    Origins
      Long history
      ::icon(fa fa-book)
      Popularisation
        British popular psychology author Tony Buzan
    Research
      On effectiveness<br/>and features
      On Automatic creation
        Uses
            Creative techniques
            Strategic planning
            Argument mapping
```

## Note

- Currently, tidy-tree is primarily supported for mindmap diagrams.
