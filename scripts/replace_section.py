#!/usr/bin/env python3
"""按小节替换/删除 storyboard.md 的 shot 段落，无需 OldString。

用法（新内容经 stdin 传入，heredoc 分隔符必须用引号包裹防止 shell 展开）：

  python3 replace_section.py <storyboard.md路径> replace shot_03 <<'SECTION_EOF'
  ## shot_03
  ...整节新内容，必须以对应的 ## shot_NN 标题行开头...
  SECTION_EOF

  python3 replace_section.py <storyboard.md路径> delete shot_03

小节边界：从 `## shot_NN` 标题行（允许标题带后缀，如 `## shot_02（⇐01，衔接上段画面状态）`）
到下一个 `## ` 标题或文件末尾。replace 的新内容标题必须与目标段号一致，防止错位替换。
"""
import re
import sys


def find_section(lines: list[str], shot: str) -> tuple[int, int]:
    pat = re.compile(rf"^## {re.escape(shot)}(\b|（|\()")
    start = next((i for i, l in enumerate(lines) if pat.match(l)), -1)
    if start == -1:
        sys.exit(f"错误：未找到小节 ## {shot}")
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    return start, end


def main() -> None:
    if len(sys.argv) != 4 or sys.argv[2] not in ("replace", "delete"):
        sys.exit(__doc__)
    path, op, shot = sys.argv[1], sys.argv[2], sys.argv[3]
    if not re.fullmatch(r"shot_\d{2,}", shot):
        sys.exit(f"错误：段号格式应为 shot_NN，收到 {shot}")

    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines(keepends=True)
    start, end = find_section(lines, shot)

    if op == "delete":
        new_lines = lines[:start] + lines[end:]
        summary = f"已删除 {shot}（原 {end - start} 行）"
    else:
        content = sys.stdin.read()
        if not content.strip():
            sys.exit("错误：stdin 未收到新内容（heredoc 是否传入？）")
        header = content.lstrip().splitlines()[0]
        if not re.match(rf"^## {re.escape(shot)}(\b|（|\()", header):
            sys.exit(f"错误：新内容首行是「{header[:40]}」，必须以 ## {shot} 标题开头（防错位替换）")
        if not content.endswith("\n"):
            content += "\n"
        new_lines = lines[:start] + [content] + lines[end:]
        summary = f"已替换 {shot}：旧 {end - start} 行 → 新 {len(content.splitlines())} 行"

    with open(path, "w", encoding="utf-8") as f:
        f.write("".join(new_lines))
    print(summary)


if __name__ == "__main__":
    main()
