"""Terminal output and logging setup."""

from __future__ import annotations

import logging
import sys
import sysconfig
from abc import ABC, abstractmethod
from contextlib import (
    contextmanager,
    redirect_stderr,
    redirect_stdout,
    suppress,
)
from dataclasses import dataclass, field
from enum import IntEnum
from functools import cached_property
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, TextIO, cast

from rich.console import Console as RichConsole
from rich.console import ConsoleRenderable
from rich.live import Live
from rich.logging import RichHandler
from rich.spinner import Spinner
from rich.table import Table
from rich.text import Text

if TYPE_CHECKING:
    from collections.abc import Iterator
    from types import TracebackType

    from rich.traceback import Traceback


STDLIB_PATH = sysconfig.get_paths()["stdlib"]


class LogLevel(IntEnum):
    TRACE = 5
    STDOUT = 21
    STDERR = 22


for _log_level in LogLevel:
    logging.addLevelName(_log_level, _log_level.name)


class Logger(logging.LoggerAdapter):
    def trace(self, msg: object, *args: object, **kwargs: Any) -> None:
        self.log(LogLevel.TRACE, msg, *args, **kwargs)

    def stdout(self, msg: object, *args: object, **kwargs: Any) -> None:
        self.log(LogLevel.STDOUT, msg, *args, **kwargs)

    def stderr(self, msg: object, *args: object, **kwargs: Any) -> None:
        self.log(LogLevel.STDERR, msg, *args, **kwargs)


class LogHandler(RichHandler):
    LOG_LEVEL_STYLES = MappingProxyType(
        {
            LogLevel.TRACE: "dim",
            LogLevel.STDERR: "yellow",
            logging.DEBUG: "dim",
            logging.INFO: "bold",
            logging.WARNING: "yellow",
            logging.ERROR: "bold red",
            logging.CRITICAL: "bold red",
        }
    )

    COMPACT_LEVEL_PREFIXES = MappingProxyType(
        {
            logging.WARNING: "[WARN] ",
            logging.ERROR: "[ERROR] ",
            logging.CRITICAL: "[CRIT] ",
        }
    )

    def __init__(
        self, *args: Any, level: int, compact: bool = False, **kwargs: Any
    ) -> None:
        kwargs.setdefault("log_time_format", "[%X]")
        kwargs.setdefault("rich_tracebacks", True)
        super().__init__(*args, **kwargs)
        self.show_path = kwargs.get("show_path", True)
        self.compact = compact
        self.setLevel(level)

    def get_level_text(self, record: logging.LogRecord) -> Text:
        if record.levelno == LogLevel.TRACE:
            return Text.styled("TRACE   ", "dim")
        if record.levelno == LogLevel.STDOUT:
            return Text.styled("STDOUT  ", "dim")
        if record.levelno == LogLevel.STDERR:
            return Text.styled("STDERR  ", "yellow")
        return super().get_level_text(record)

    def render(
        self,
        *,
        record: logging.LogRecord,
        traceback: Traceback | None,
        message_renderable: ConsoleRenderable,
    ) -> ConsoleRenderable:
        output = super().render(
            record=record,
            traceback=traceback,
            message_renderable=message_renderable,
        )
        if not self.show_path and isinstance(output, Table):
            output.expand = False
        return output

    def render_message(
        self, record: logging.LogRecord, message: str
    ) -> ConsoleRenderable:
        msg_text = cast("Text", super().render_message(record, message))
        level_style = self.LOG_LEVEL_STYLES.get(record.levelno)
        if level_style:
            msg_text.stylize_before(level_style)
        if self.compact and (
            prefix := self.COMPACT_LEVEL_PREFIXES.get(record.levelno)
        ):
            msg_text = Text.assemble(
                Text(prefix, style=level_style or ""),
                msg_text,
                no_wrap=True,
                overflow="ignore",
            )
        return msg_text


@dataclass
class LoggingStream:
    log: logging.Logger
    level: int
    buf: str = field(default="", init=False, repr=False)

    def write(self, text: str) -> int:
        self.buf += text
        while "\n" in self.buf:
            line, self.buf = self.buf.split("\n", 1)
            if line:
                self.log.log(self.level, line)
        return len(text)

    def flush(self) -> None:
        if self.buf.strip():
            self.log.log(self.level, self.buf)
            self.buf = ""

    def isatty(self) -> bool:
        return False


@dataclass
class ConsoleOutput(ABC):
    level: int = field(default=logging.CRITICAL, kw_only=True)

    class StderrWrapper:
        def __getattr__(self, key: str) -> Any:
            return getattr(sys.__stderr__, key)

    @property
    @abstractmethod
    def console(self) -> RichConsole: ...

    @property
    @abstractmethod
    def handler(self) -> RichHandler: ...


@dataclass
class WebConsoleOutput(ConsoleOutput):
    level: int = field(default=logging.INFO, kw_only=True)
    stream: TextIO
    width: int = 80

    def set_width(self, value: int) -> None:
        self.width = value
        self.console.width = self.width

    @cached_property
    def console(self) -> RichConsole:
        return RichConsole(
            file=self.stream,
            force_terminal=True,
            markup=True,
            width=self.width,
        )

    @cached_property
    def handler(self) -> RichHandler:
        import bdbox  # noqa: PLC0415

        return LogHandler(
            level=self.level,
            console=self.console,
            show_time=False,
            show_level=False,
            show_path=False,
            compact=True,
            tracebacks_suppress=[bdbox, STDLIB_PATH],
            tracebacks_width=100,
        )


@dataclass
class TerminalConsoleOutput(ConsoleOutput):
    @cached_property
    def console(self) -> RichConsole:
        return RichConsole(
            file=cast("TextIO", self.StderrWrapper()), markup=True
        )

    @cached_property
    def handler(self) -> RichHandler:
        import bdbox  # noqa: PLC0415

        return LogHandler(
            level=self.level,
            console=self.console,
            show_time=bool(self.level <= LogLevel.TRACE),
            show_level=bool(self.level <= logging.DEBUG),
            show_path=bool(self.level <= LogLevel.TRACE),
            tracebacks_suppress=(
                [bdbox, STDLIB_PATH] if self.level > logging.DEBUG else []
            ),
        )


@dataclass
class Console:
    verbose: int = 0

    terminal_output: TerminalConsoleOutput | None = field(
        default=None, init=False
    )
    web_outputs: dict[int, ConsoleOutput] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.reset()

        def excepthook(
            exc_type: type[BaseException],
            exc_value: BaseException,
            exc_traceback: TracebackType | None,
        ) -> None:
            if issubclass(exc_type, KeyboardInterrupt):
                sys.__excepthook__(exc_type, exc_value, exc_traceback)
                return
            self.logger().error(
                "Uncaught exception",
                exc_info=(exc_type, exc_value, exc_traceback),
            )

        sys.excepthook = excepthook

    def logger(self) -> Logger:
        return Logger(logging.getLogger("bdbox"))

    @contextmanager
    def log_stdout_stderr(self) -> Iterator[None]:
        """Redirect model stdout/stderr through the bdbox logger."""
        log = logging.getLogger("bdbox")
        stdout_stream = LoggingStream(log, LogLevel.STDOUT)
        stderr_stream = LoggingStream(log, LogLevel.STDERR)
        try:
            with (
                redirect_stdout(stdout_stream),
                redirect_stderr(stderr_stream),
            ):
                yield
        finally:
            stdout_stream.flush()
            stderr_stream.flush()

    @contextmanager
    def activity_indicator(self) -> Iterator[None]:
        term = console.terminal_output
        if term and sys.__stderr__ and sys.__stderr__.isatty():
            with Live(
                Spinner("dots", text="[bold]Running model...[/bold]"),
                console=term.console,
                refresh_per_second=8,
                transient=True,
                redirect_stdout=False,
                redirect_stderr=False,
            ):
                yield
        else:
            yield

    def configure(self, *, verbose: int = 0) -> None:
        if verbose != self.verbose:
            self.verbose = verbose
            self.reset()

    def reset(self) -> None:
        log = logging.getLogger()
        if self.terminal_output and self.terminal_output.handler:
            for handler in log.handlers:
                if handler == self.terminal_output.handler:
                    log.removeHandler(handler)

        for web_output in self.web_outputs.values():
            web_output.level = logging.INFO
        bdbox_level = (
            LogLevel.TRACE
            if self.verbose >= 2
            else logging.DEBUG
            if self.verbose
            else logging.INFO
        )
        self.terminal_output = TerminalConsoleOutput(level=bdbox_level)
        log.addHandler(self.terminal_output.handler)
        logging.getLogger().setLevel(
            logging.DEBUG if self.verbose >= 3 else logging.WARNING
        )
        logging.getLogger("websockets").setLevel(
            logging.DEBUG if self.verbose >= 4 else logging.WARNING
        )
        bdbox_log = logging.getLogger("bdbox")
        bdbox_log.setLevel(bdbox_level)
        self.log_level = bdbox_log.getEffectiveLevel()

    def add_web_output(self, ws_id: int, stream: TextIO, width: int) -> None:
        if ws_id in self.web_outputs:
            self.web_outputs[ws_id].console.width = width
            return
        web_console = WebConsoleOutput(stream=stream, width=width)
        self.web_outputs[ws_id] = web_console
        logging.getLogger().addHandler(web_console.handler)
        return

    def remove_web_output(self, ws_id: int) -> None:
        if ws_id not in self.web_outputs:
            return
        with suppress(ValueError):
            web_console = self.web_outputs.pop(ws_id)
            logging.getLogger().removeHandler(web_console.handler)


console = Console()
log = console.logger()
