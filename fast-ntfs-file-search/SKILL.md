---
name: fast-ntfs-file-search
description: 使用 `~/bin/fast-ntfs.exe` 进行本机文件搜索。
---

# fast-ntfs-file-search Skill

This skill searches local files through `~/bin/fast-ntfs.exe`.

## Usage

Preferred:

```bash
~/bin/fast-ntfs.exe search --query rg.exe
```

Optional flags:

```bash
~/bin/fast-ntfs.exe search --query "keyword" --match name --type file --limit 20
~/bin/fast-ntfs.exe search --query "keyword" --match path --type dir --limit 20
~/bin/fast-ntfs.exe search --query "keyword" --match all --type all --limit 20
```
