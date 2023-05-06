"""A simple spinner module"""
import asyncio
import itertools
import select
import sys
import termios
import threading
import time
import tty


class SpinnerInterrupted(Exception):
    pass


class RaisingThread(threading.Thread):
    def run(self):
        self._exc = None
        try:
            super().run()
        except Exception as e:
            self._exc = e

    def join(self, timeout=None):
        super().join(timeout=timeout)
        if self._exc:
            raise self._exc


class Spinner:
    """A simple spinner class"""

    def __init__(
        self,
        message: str = "Loading...",
        delay: float = 0.1,
        plain_output: bool = False,
        interruptable: bool = False,
        interrupt_action=None,
    ) -> None:
        """Initialize the spinner class

        Args:
            message (str): The message to display.
            delay (float): The delay between each spinner update.
            plain_output (bool): Whether to display the spinner or not.
        """
        self.plain_output = plain_output
        self.spinner = itertools.cycle(["-", "/", "|", "\\"])
        self.delay = delay
        self.message = message
        self.running = False
        self.spinner_thread = None
        self.interruptable = interruptable
        self.interrupt_action = interrupt_action
        self.ended = threading.Event()

    def spin(self) -> None:
        """Spin the spinner"""
        if self.plain_output:
            self.print_message()
            return
        while self.running:
            self.print_message()
            # Add non-blocking reading of char to stop spinner
            if (
                self.interruptable
                and sys.stdin in select.select([sys.stdin], [], [], 0.0)[0]
            ):
                key = sys.stdin.read(1)
                if key == " ":
                    if self.interrupt_action is not None:
                        self.interrupt_action()

                elif key == "q":
                    self.ended.set()
                    raise SpinnerInterrupted("Spinner interrupted")

            time.sleep(self.delay)

    def print_message(self):
        sys.stdout.write(f"\r{' ' * (len(self.message) + 2)}\r")
        sys.stdout.write(f"{next(self.spinner)} {self.message}\r")
        sys.stdout.flush()

    def __enter__(self):
        """Start the spinner"""
        self.running = True
        self.oldtty = termios.tcgetattr(sys.stdin)
        self.stdin_no = sys.stdin.fileno()
        tty.setcbreak(self.stdin_no)

        self.spinner_thread = RaisingThread(target=self.spin)
        self.spinner_thread.start()

        return self

    def __exit__(self, exc_type, exc_value, exc_traceback) -> None:
        """Stop the spinner

        Args:
            exc_type (Exception): The exception type.
            exc_value (Exception): The exception value.
            exc_traceback (Exception): The exception traceback.
        """
        self.running = False
        try:
            if self.spinner_thread is not None:
                self.spinner_thread.join()
        finally:
            while sys.stdin in select.select([sys.stdin], [], [], 0.0)[0]:
                sys.stdin.read(1)
            termios.tcsetattr(self.stdin_no, termios.TCSADRAIN, self.oldtty)

        sys.stdout.write(f"\r{' ' * (len(self.message) + 2)}\r")
        sys.stdout.flush()

    def update_message(self, new_message, delay=0.1):
        """Update the spinner message
        Args:
            new_message (str): New message to display.
            delay (float): The delay in seconds between each spinner update.
        """
        self.delay = delay
        self.message = new_message
        if self.plain_output:
            self.print_message()
