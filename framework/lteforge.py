#!/usr/bin/env python3
from __future__ import annotations

import inspect
import importlib.util
import os
import re
import sys
import textwrap

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List

from blessed import Terminal


THIS_FILE = Path(__file__).resolve()
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

# Blessed 256-color blue.
BLUE = 33

VERSION = "Version 0.1.0"
PROJECT_NAME = "LTEForge"


def blue(term: Terminal, text: str) -> str:
    return term.color(BLUE) + text + term.normal


def clean_len(text: str) -> int:
    return len(ANSI_RE.sub("", text))


def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def find_project_root(start: Path) -> Path:
    """
    Search upward until a project containing framework/labs is found.
    """

    for path in [start, *start.parents]:
        labs_dir = path / "framework" / "labs"

        if labs_dir.exists() and labs_dir.is_dir():
            return path

    print(f"[{PROJECT_NAME}] Could not find project root.")
    print(
        f"[{PROJECT_NAME}] Expected a directory at: "
        "framework/labs"
    )
    sys.exit(1)


PROJECT_ROOT = find_project_root(THIS_FILE.parent)
LABS_DIR = PROJECT_ROOT / "framework" / "labs"


@dataclass(frozen=True)
class LabInfo:
    name: str
    desc: str
    file: Path
    function: Callable[[], object]


ascii_art = r"""
                                      ▪  ▪  ▪
                                        ▪█▪
                                         █
                                   ▄▄    █    ▄▄
                                     ▀▄  █  ▄▀
                                       ▀██▀
                                        ██▄
                                        █  ▀▄
                                        █    ▀▄
                                        █    ▄▀
                                        █  ▄▀
                                       ▄██▄
                                     ▄▀  █  ▀▄
                                   ▀▀    █    ▀▀
                                         █
                                        ▄█▄

              ██╗     ████████╗███████╗███████╗ ██████╗ ██████╗  ██████╗ ███████╗
              ██║     ╚══██╔══╝██╔════╝██╔════╝██╔═══██╗██╔══██╗██╔════╝ ██╔════╝
              ██║        ██║   █████╗  █████╗  ██║   ██║██████╔╝██║  ███╗█████╗
              ██║        ██║   ██╔══╝  ██╔══╝  ██║   ██║██╔══██╗██║   ██║██╔══╝
              ███████╗   ██║   ███████╗██║     ╚██████╔╝██║  ██║╚██████╔╝███████╗
              ╚══════╝   ╚═╝   ╚══════╝╚═╝      ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝
"""


def create_module_name(file_path: Path) -> str:
    """
    Create a unique import name so labs with similar filenames do not
    overwrite one another in Python's module system.
    """

    safe_stem = re.sub(r"[^a-zA-Z0-9_]", "_", file_path.stem)

    return f"lteforge_lab_{safe_stem}_{abs(hash(file_path))}"


def import_module_and_get_function(
    file_path: Path,
    module_name: str,
) -> LabInfo | None:
    """
    Import one lab module and locate its launch function.

    Function priority:
        1. run()
        2. main()
        3. First public function defined by that module
    """

    try:
        spec = importlib.util.spec_from_file_location(
            module_name,
            file_path,
        )

        if spec is None or spec.loader is None:
            return None

        module = importlib.util.module_from_spec(spec)

        # Makes imports relative to the project easier for lab modules.
        if str(PROJECT_ROOT) not in sys.path:
            sys.path.insert(0, str(PROJECT_ROOT))

        spec.loader.exec_module(module)

    except Exception as error:
        print(
            f"[{PROJECT_NAME}] Could not import "
            f"{file_path.name}: {error}"
        )
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
                "find_project_root",
                "find_gnuradio_companion",
                "run_python_flowgraph",
                "open_grc_file",
            }
        }

        if functions:
            _, function = next(iter(functions.items()))

    if function is None:
        return None

    default_name = file_path.stem.replace("_", " ").title()

    name = getattr(module, "LAB_NAME", default_name)
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
    """
    Discover all valid Python lab modules inside framework/labs.
    """

    labs: List[LabInfo] = []

    if not LABS_DIR.exists():
        return labs

    for file_path in sorted(LABS_DIR.glob("*.py")):
        if file_path.name.startswith("_"):
            continue

        if file_path.resolve() == THIS_FILE:
            continue

        module_name = create_module_name(file_path)

        lab = import_module_and_get_function(
            file_path,
            module_name,
        )

        if lab is not None:
            labs.append(lab)

    labs.sort(key=lambda item: item.name.lower())

    return labs


def draw_box(
    term: Terminal,
    top: int,
    left: int,
    width: int,
    height: int,
    title: str,
) -> None:
    title_text = f" {title} "
    available_width = width - 2
    side = max(
        (available_width - len(title_text)) // 2,
        0,
    )

    remaining = max(
        available_width - side - len(title_text),
        0,
    )

    print(
        term.move(top, left)
        + "┌"
        + "─" * side
        + title_text
        + "─" * remaining
        + "┐"
    )

    for row in range(height):
        print(
            term.move(top + 1 + row, left)
            + "│"
            + " " * (width - 2)
            + "│"
        )

    print(
        term.move(top + height + 1, left)
        + "└"
        + "─" * (width - 2)
        + "┘"
    )


def draw_outer_box(
    term: Terminal,
    top: int,
    left: int,
    width: int,
    height: int,
    version: str = VERSION,
) -> None:
    label = f"|{version}|"

    line_length = max(
        width - len(label) - 2,
        0,
    )

    top_line = (
        "┌"
        + label
        + "─" * line_length
        + "┐"
    )

    print(term.move(top, left) + top_line)

    for row in range(height):
        print(
            term.move(top + 1 + row, left)
            + "│"
            + " " * (width - 2)
            + "│"
        )

    print(
        term.move(top + height + 1, left)
        + "└"
        + "─" * (width - 2)
        + "┘"
    )


def print_logo(
    term: Terminal,
    top: int,
    art: str,
    center_left: int,
    center_width: int,
) -> int:
    lines = textwrap.dedent(art).strip("\n").splitlines()

    logo_width = max(
        clean_len(line)
        for line in lines
    )

    logo_left = center_left + max(
        (center_width - logo_width) // 2,
        0,
    )

    for row, line in enumerate(lines):
        # The ▪ characters become the blue accent details.
        rendered_line = line.replace(
            "▪",
            blue(term, "▪"),
        )

        print(
            term.move(top + row, logo_left)
            + rendered_line
        )

    by_text = "By BHIS"
    by_row = top + len(lines)

    print(
        term.move(by_row, logo_left)
        + blue(term, by_text)
    )

    return by_row + 1


def calculate_dimensions(term: Terminal) -> tuple[int, int, int]:
    """
    Scale the menu down slightly on smaller terminals.
    """

    available_width = max(term.width - 6, 60)

    preferred_lab_width = 33
    preferred_desc_width = 55
    gap = 4

    preferred_inner_width = (
        preferred_lab_width
        + gap
        + preferred_desc_width
    )

    if available_width >= preferred_inner_width + 4:
        return (
            preferred_lab_width,
            preferred_desc_width,
            gap,
        )

    gap = 2
    lab_width = max(
        min(29, available_width // 3),
        20,
    )

    desc_width = max(
        available_width - lab_width - gap - 4,
        30,
    )

    return lab_width, desc_width, gap


def print_menu(
    term: Terminal,
    labs: List[LabInfo],
    selected_index: int,
) -> None:
    with term.hidden_cursor():
        print(term.clear)

        lab_width, desc_width, gap = calculate_dimensions(term)

        available_height = max(term.height - 30, 6)
        box_height = min(12, available_height)

        inner_width = lab_width + gap + desc_width
        outer_width = inner_width + 4

        outer_left = max(
            (term.width - outer_width) // 2,
            0,
        )

        inner_left = outer_left + 2

        logo_bottom = print_logo(
            term=term,
            top=1,
            art=ascii_art,
            center_left=outer_left,
            center_width=outer_width,
        )

        outer_top = logo_bottom + 1
        outer_height = box_height + 2

        draw_outer_box(
            term=term,
            top=outer_top,
            left=outer_left,
            width=outer_width,
            height=outer_height,
        )

        lab_left = inner_left
        desc_left = lab_left + lab_width + gap
        box_top = outer_top + 1

        draw_box(
            term,
            box_top,
            lab_left,
            lab_width,
            box_height,
            "Labs",
        )

        draw_box(
            term,
            box_top,
            desc_left,
            desc_width,
            box_height,
            "Description",
        )

        current_lab = labs[selected_index]

        start = max(
            selected_index - box_height + 1,
            0,
        )

        visible_labs = labs[
            start:start + box_height
        ]

        for row, lab in enumerate(visible_labs):
            real_index = start + row

            max_name_length = max(
                lab_width - 4,
                1,
            )

            name = lab.name[:max_name_length]

            if real_index == selected_index:
                rendered = blue(term, name)
            else:
                rendered = name

            print(
                term.move(
                    box_top + 1 + row,
                    lab_left + 2,
                )
                + rendered
            )

        description_width = max(
            desc_width - 5,
            10,
        )

        wrapped_description = textwrap.wrap(
            current_lab.desc,
            width=description_width,
        )

        for row, line in enumerate(
            wrapped_description[:box_height]
        ):
            print(
                term.move(
                    box_top + 1 + row,
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

        footer_row = outer_top + outer_height + 3

        print(
            term.move(footer_row, footer_left)
            + blue(term, footer)
        )


def launch_lab(lab: LabInfo) -> None:
    clear_screen()

    try:
        result = lab.function()

        # Prevent an immediate flash back to the menu when a lab
        # finishes without handling its own pause.
        if result is not None:
            print(result)

    except KeyboardInterrupt:
        pass

    except Exception as error:
        clear_screen()

        print(f"\n[{PROJECT_NAME}] Error launching lab:\n")
        print(error)

        input("\nPress ENTER to return...")


def main() -> None:
    labs = discover_labs()

    if not labs:
        print(f"[{PROJECT_NAME}] No labs found.")
        print(f"[{PROJECT_NAME}] Lab directory: {LABS_DIR}")
        print(
            f"[{PROJECT_NAME}] Each lab must define run(), "
            "main(), or another public function."
        )
        sys.exit(1)

    term = Terminal()
    current_row = 0

    with term.cbreak(), term.fullscreen():
        while True:
            # Rediscover on every redraw after refresh, but preserve
            # the currently selected position when possible.
            current_row = min(
                current_row,
                len(labs) - 1,
            )

            print_menu(
                term,
                labs,
                current_row,
            )

            key = term.inkey()

            if key.code == term.KEY_UP:
                if current_row > 0:
                    current_row -= 1

            elif key.code == term.KEY_DOWN:
                if current_row < len(labs) - 1:
                    current_row += 1

            elif key.code in (
                term.KEY_ENTER,
                "\n",
                "\r",
            ):
                launch_lab(labs[current_row])

            elif key.lower() == "r":
                labs = discover_labs()

                if not labs:
                    clear_screen()
                    print(f"[{PROJECT_NAME}] No labs found.")
                    input("\nPress ENTER to return...")
                    labs = discover_labs()

                    if not labs:
                        return

            elif key.lower() == "q":
                clear_screen()
                return


if __name__ == "__main__":
    main()