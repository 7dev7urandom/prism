import tkinter as tk
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Generic

from examples.overlay.output.overlay.utils import (
    Cell,
    CellValue,
    ColumnKey,
    OverlayRowData,
)

if TYPE_CHECKING:  # pragma: nocover
    from examples.overlay.output.overlay.stats_overlay import StatsOverlay

StatsCells = dict[ColumnKey, Cell]

OverlayRow = tuple[tk.Button, StatsCells[ColumnKey]]


class MainContent(Generic[ColumnKey]):  # pragma: nocover
    """Main content for the overlay"""

    def __init__(
        self,
        parent: tk.Misc,
        overlay: "StatsOverlay[ColumnKey]",
        column_order: Sequence[ColumnKey],
        column_names: dict[ColumnKey, str],
        left_justified_columns: set[int],
    ) -> None:
        # Column config
        """Set up a frame containing the main content for the overlay"""
        self.overlay = overlay
        self.column_order = column_order
        self.column_names = column_names
        self.left_justified_columns = left_justified_columns

        self.frame = tk.Frame(parent, background="black")

        # Start with zero rows
        self.rows: list[OverlayRow[ColumnKey]] = []

        # Frame at the top to display info to the user
        self.info_frame = tk.Frame(self.frame, background="black")
        self.info_frame.pack(side=tk.TOP, expand=True, fill=tk.X)

        self.info_labels: dict[CellValue, tk.Label] = {}

        def shrink_info_when_empty(event: "tk.Event[tk.Frame]") -> None:
            """Manually shrink the info frame when it becomes empty"""
            if not self.info_frame.children:
                self.info_frame.configure(height=1)

        self.info_frame.bind("<Expose>", shrink_info_when_empty)

        # A frame for the stats table
        self.table_frame = tk.Frame(self.frame, background="black")
        self.table_frame.pack(side=tk.TOP)

        # Set up header labels
        for column_index, column_name in enumerate(self.column_order):
            header_label = tk.Label(
                self.table_frame,
                text=(
                    str.ljust
                    if column_index in self.left_justified_columns
                    else str.rjust
                )(self.column_names[column_name], 7),
                font=("Consolas", "14"),
                fg="snow",
                bg="black",
            )
            header_label.grid(
                row=1,
                column=column_index + 1,
                sticky="w" if column_index in self.left_justified_columns else "e",
            )

    def append_row(self) -> None:
        """Add a row of labels and stringvars to the table"""
        row_index = len(self.rows) + 2

        stats_cells: StatsCells[ColumnKey] = {}
        for column_index, column_name in enumerate(self.column_order):
            string_var = tk.StringVar()
            label = tk.Label(
                self.table_frame,
                font=("Consolas", "14"),
                fg="gray60",  # Color set on each update
                bg="black",
                textvariable=string_var,
            )
            label.grid(
                row=row_index,
                column=column_index + 1,
                sticky="w" if column_index in self.left_justified_columns else "e",
            )
            stats_cells[column_name] = Cell(label, string_var)

        edit_button = tk.Button(
            self.table_frame,
            text="✎",
            font=("Consolas", "14"),
            foreground="white",
            disabledforeground="black",
            background="black",
            highlightthickness=0,
            state="disabled",
            command=lambda: None,
            relief="flat",
        )
        edit_button.grid(row=row_index, column=0)

        self.rows.append((edit_button, stats_cells))

    def pop_row(self) -> None:
        """Remove a row of labels and stringvars from the table"""
        edit_button, stats_cells = self.rows.pop()
        for column_name in self.column_order:
            stats_cells[column_name].label.destroy()

        edit_button.destroy()

    def set_length(self, length: int) -> None:
        """Add or remove table rows to give the desired length"""
        current_length = len(self.rows)
        if length > current_length:
            for i in range(length - current_length):
                self.append_row()
        elif length < current_length:
            for i in range(current_length - length):
                self.pop_row()

    def update_info(self, info_cells: list[CellValue]) -> None:
        """Update the list of info cells at the top of the overlay"""
        to_remove = set(self.info_labels.keys()) - set(info_cells)
        to_add = set(info_cells) - set(self.info_labels.keys())

        # Remove old labels
        for cell in to_remove:
            label = self.info_labels.pop(cell)
            label.destroy()

        # Add new labels
        for cell in to_add:
            label = tk.Label(
                self.info_frame,
                text=cell.text,
                font=("Consolas", "14"),
                fg=cell.color,  # Color set on each update
                bg="black",
            )
            label.pack(side=tk.TOP)
            self.info_labels[cell] = label

    def update_content(
        self,
        info_cells: list[CellValue],
        new_rows: list[OverlayRowData[ColumnKey]] | None,
    ) -> None:
        """Display the new data"""
        # Update the info at the top of the overlay
        self.update_info(info_cells)

        # Set the contents of the table if new data was provided
        if new_rows is not None:
            self.set_length(len(new_rows))

            for i, (nickname, rated_stats) in enumerate(new_rows):
                edit_button, stats_cells = self.rows[i]
                for column_name in self.column_order:
                    stats_cells[column_name].variable.set(rated_stats[column_name].text)
                    stats_cells[column_name].label.configure(
                        fg=rated_stats[column_name].color
                    )

                if nickname is None:
                    edit_button.configure(state="disabled", command=lambda: None)
                else:
                    edit_button.configure(
                        state="normal", command=self.make_set_nick_callback(nickname)
                    )

    def make_set_nick_callback(self, nickname: str) -> Callable[[], None]:
        """Create a callback to pass as a command to open the set nick page"""

        def command(self: "MainContent[ColumnKey]" = self) -> None:
            self.overlay.set_nickname_page.set_content(nickname)
            self.overlay.switch_page("set_nickname")

        return command
