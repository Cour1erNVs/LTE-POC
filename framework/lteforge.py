#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import inspect
import os
import re
import sys
import textwrap

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List

from blessed import Terminal


THIS_FILE = Path(__file__).resolve()
VERSION = "Version 0.1.0"
BLUE = 39


def blue(term: Terminal, text: str) -> str:
    return term.color(BLUE) + text + term.normal


def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def find_project_root(start: Path) -> Path:
    for path in [start, *start.parents]:
        labs_dir = path / "framework" / "labs"

        if labs_dir.exists() and labs_dir.is_dir():
            return path

    print("[LTEForge] Could not find project root.")
    print("[LTEForge] Expected framework/labs.")
    sys.exit(1)


PROJECT_ROOT = find_project_root(THIS_FILE.parent)
LABS_DIR = PROJECT_ROOT / "framework" / "labs"


@dataclass(frozen=True)
class LabInfo:
    name: str
    desc: str
    file: Path
    function: Callable[[], object]


ASCII_ART = r"""
                                                    BBBB
                                                    BBBB
                                              BBBB  BBBB
                                              BBBB  BBBB
                                        BBBB  BBBB  BBBB
                                        BBBB  BBBB  BBBB
                                  BBBB  BBBB  BBBB  BBBB
                                  BBBB  BBBB  BBBB  BBBB
                            BBBB  BBBB  BBBB  BBBB  BBBB
                            BBBB  BBBB  BBBB  BBBB  BBBB

              ██╗     ████████╗███████╗███████╗ ██████╗ ██████╗  ██████╗ ███████╗
              ██║     ╚══██╔══╝██╔════╝██╔════╝██╔═══██╗██╔══██╗██╔════╝ ██╔════╝
              ██║        ██║   █████╗  █████╗  ██║   ██║██████╔╝██║  ███╗█████╗
              ██║        ██║   ██╔══╝  ██╔══╝  ██║   ██║██╔══██╗██║   ██║██╔══╝
              ███████╗   ██║   ███████╗██║     ╚██████╔╝██║  ██║╚██████╔╝███████╗
              ╚══════╝   ╚═╝   ╚══════╝╚═╝      ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝
"""


def create_module_name(file_path: Path) -> str:
    safe_name = re.sub(r"[^a-zA-Z0-9_]", "_", file_path.stem)
    return f"lteforge_lab_{safe_name}_{abs(hash(file_path))}"


def import_lab(file_path: Path) -> LabInfo | None:
    try:
        spec = importlib.util.spec_from_file_location(
            create_module_name(file_path),
            file_path,
        )

        if spec is None or spec.loader is None:
            return None

        module = importlib.util.module_from_spec(spec)

        if str(PROJECT_ROOT) not in sys.path:
            sys.path.insert(0, str(PROJECT_ROOT))

        spec.loader.exec_module(module)

    except Exception as error:
        print(f"[LTEForge] Failed to import {file_path.name}: {error}")
        return None

    function: Callable[[], object] | None = None

    if hasattr(module, "run") and callable(module.run):
        function = module.run

    elif hasattr(module, "main") and callable(module.main):
        function = module.main

    else:
        functions = {
            name: func
            for name, func in inspect.getmembers(
                module,
                inspect.isfunction,
            )
            if not name.startswith("_")
            and func.__module__ == module.__name__
            and name
            not in {
                "find_gnuradio_companion",
                "run_python_flowgraph",
                "open_grc_file",
            }
        }

        if functions:
            function = next(iter(functions.values()))

    if function is None:
        return None

    name = getattr(
        module,
        "LAB_NAME",
        file_path.stem.replace("_", " ").title(),
    )

    desc = getattr(
        module,
        "LAB_DESC",
        "No description available.",
    )

    return LabInfo(
        name=str(name),
        desc=str(desc),
        file=file_path,
        function=function,
    )


def discover_labs() -> List[LabInfo]:
    labs: List[LabInfo] = []

    for file_path in sorted(LABS_DIR.glob("*.py")):
        if file_path.name.startswith("_"):
            continue

        if file_path.resolve() == THIS_FILE:
            continue

        lab = import_lab(file_path)

        if lab is not None:
            labs.append(lab)

    labs.sort(key=lambda lab: lab.name.lower())
    return labs


def render_logo_line(term: Terminal, line: str) -> str:
    return "".join(
        blue(term, "█") if character == "B" else character
        for character in line
    )


def print_logo(
    term: Terminal,
    top: int,
    center_left: int,
    center_width: int,
) -> int:
    lines = textwrap.dedent(ASCII_ART).strip("\n").splitlines()

    logo_width = max(
        len(line.replace("B", "█"))
        for line in lines
    )

    menu_center = center_left + center_width // 2
    logo_left = menu_center - logo_width // 2

    for row, line in enumerate(lines):
        screen_row = top + row

        if screen_row < 0:
            continue

        print(
            term.move(screen_row, logo_left)
            + render_logo_line(term, line)
        )

    by_row = top + len(lines)

    if by_row >= 0:
        print(
            term.move(by_row, logo_left)
            + blue(term, "By BHIS")
        )

    return by_row + 1


def draw_outer_box(
    term: Terminal,
    top: int,
    left: int,
    width: int,
    height: int,
) -> None:
    label = f"|{VERSION}|"

    print(
        term.move(top, left)
        + "┌"
        + label
        + "─" * max(width - len(label) - 2, 0)
        + "┐"
    )

    for row in range(height):
        print(
            term.move(top + row + 1, left)
            + "│"
            + " " * max(width - 2, 0)
            + "│"
        )

    print(
        term.move(top + height + 1, left)
        + "└"
        + "─" * max(width - 2, 0)
        + "┘"
    )


def draw_inner_box(
    term: Terminal,
    top: int,
    left: int,
    width: int,
    height: int,
    title: str,
) -> None:
    title_text = f" {title} "
    available = width - 2

    left_line = max(
        (available - len(title_text)) // 2,
        0,
    )

    right_line = max(
        available - left_line - len(title_text),
        0,
    )

    print(
        term.move(top, left)
        + "┌"
        + "─" * left_line
        + title_text
        + "─" * right_line
        + "┐"
    )

    for row in range(height):
        print(
            term.move(top + row + 1, left)
            + "│"
            + " " * max(width - 2, 0)
            + "│"
        )

    print(
        term.move(top + height + 1, left)
        + "└"
        + "─" * max(width - 2, 0)
        + "┘"
    )


def truncate(text: str, maximum: int) -> str:
    if len(text) <= maximum:
        return text

    if maximum <= 3:
        return text[:maximum]

    return text[: maximum - 3] + "..."


def calculate_layout(
    term: Terminal,
) -> tuple[int, int, int, int, int]:
    if term.width >= 105:
        lab_width = 35
        desc_width = 57
        gap = 4

    elif term.width >= 85:
        lab_width = 28
        desc_width = 45
        gap = 3

    else:
        available = max(term.width - 10, 54)
        gap = 2
        lab_width = max(20, available // 3)

        desc_width = max(
            28,
            available - lab_width - gap,
        )

    if term.height >= 49:
        box_height = 8
        logo_top = 0

    elif term.height >= 44:
        box_height = 6
        logo_top = -1

    elif term.height >= 39:
        box_height = 4
        logo_top = -3

    else:
        box_height = 3
        logo_top = -5

    return (
        lab_width,
        desc_width,
        gap,
        box_height,
        logo_top,
    )


def print_menu(
    term: Terminal,
    labs: List[LabInfo],
    selected_index: int,
) -> None:
    with term.hidden_cursor():
        print(term.clear)

        (
            lab_width,
            desc_width,
            gap,
            box_height,
            logo_top,
        ) = calculate_layout(term)

        inner_width = lab_width + gap + desc_width
        outer_width = inner_width + 6

        outer_left = max(
            (term.width - outer_width) // 2,
            0,
        )

        logo_bottom = print_logo(
            term,
            logo_top,
            outer_left,
            outer_width,
        )

        outer_top = max(logo_bottom, 0)
        outer_height = box_height + 3

        lab_left = outer_left + 2
        desc_left = lab_left + lab_width + gap
        inner_top = outer_top + 1

        draw_outer_box(
            term,
            outer_top,
            outer_left,
            outer_width,
            outer_height,
        )

        draw_inner_box(
            term,
            inner_top,
            lab_left,
            lab_width,
            box_height,
            "Labs",
        )

        draw_inner_box(
            term,
            inner_top,
            desc_left,
            desc_width,
            box_height,
            "Description",
        )

        current_lab = labs[selected_index]

        start_index = max(
            selected_index - box_height + 1,
            0,
        )

        visible_labs = labs[
            start_index:start_index + box_height
        ]

        for row, lab in enumerate(visible_labs):
            actual_index = start_index + row

            name = truncate(
                lab.name,
                max(lab_width - 5, 1),
            )

            rendered = (
                blue(term, name)
                if actual_index == selected_index
                else name
            )

            print(
                term.move(
                    inner_top + row + 1,
                    lab_left + 2,
                )
                + rendered
            )

        wrapped = textwrap.wrap(
            current_lab.desc,
            width=max(desc_width - 5, 10),
            break_long_words=False,
            break_on_hyphens=False,
        )

        for row, line in enumerate(wrapped[:box_height]):
            print(
                term.move(
                    inner_top + row + 1,
                    desc_left + 2,
                )
                + line
            )

        footer = (
            "[↑/↓] Navigate    "
            "[ENTER] Launch    "
            "[R] Refresh    "
            "[Q] Quit"
        )

        footer_left = outer_left + max(
            (outer_width - len(footer)) // 2,
            0,
        )

        footer_row = min(
            outer_top + outer_height + 2,
            max(term.height - 1, 0),
        )

        print(
            term.move(
                footer_row,
                max(footer_left, 0),
            )
            + blue(term, footer)
        )


def launch_lab(lab: LabInfo) -> None:
    clear_screen()

    try:
        result = lab.function()

        if result is not None:
            print(result)

    except KeyboardInterrupt:
        pass

    except Exception as error:
        clear_screen()
        print(f"\n[LTEForge] Error launching {lab.name}:\n")
        print(error)
        input("\nPress ENTER to return...")


def main() -> None:
    labs = discover_labs()

    if not labs:
        print("[LTEForge] No labs found.")
        print(f"[LTEForge] Lab directory: {LABS_DIR}")
        sys.exit(1)

    term = Terminal()
    selected_index = 0

    with term.cbreak(), term.fullscreen():
        while True:
            selected_index = min(
                selected_index,
                len(labs) - 1,
            )

            print_menu(
                term,
                labs,
                selected_index,
            )

            key = term.inkey()

            if key.code == term.KEY_UP:
                if selected_index > 0:
                    selected_index -= 1

            elif key.code == term.KEY_DOWN:
                if selected_index < len(labs) - 1:
                    selected_index += 1

            elif key.code in (
                term.KEY_ENTER,
                "\n",
                "\r",
            ):
                launch_lab(labs[selected_index])

            elif key.lower() == "r":
                selected_name = labs[selected_index].name
                refreshed = discover_labs()

                if not refreshed:
                    clear_screen()
                    print("[LTEForge] No labs found.")
                    input("\nPress ENTER to return...")
                    continue

                labs = refreshed

                selected_index = next(
                    (
                        index
                        for index, lab in enumerate(labs)
                        if lab.name == selected_name
                    ),
                    0,
                )

            elif key.lower() == "q":
                clear_screen()
                return


if __name__ == "__main__":
    main()