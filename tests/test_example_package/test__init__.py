"""Provide testcases for the entry points.."""

import unittest
from unittest.mock import patch
from io import StringIO
from src.main import entry_point


class TestEntryPoint(unittest.TestCase):
    """Testcases for the entry point."""

    @patch("sys.stdout", new_callable=StringIO)  # Mock stdout to capture prints
    @patch("sys.argv", ["entry_point", "2", "3"])  # Mock command-line arguments
    def test_entry_point(self, mock_stdout):
        """An exemplary testcase for the entry point."""
        entry_point()

        # Check if the output is correct
        output = mock_stdout.getvalue().strip()  # Capture printed output
        self.assertEqual(output, "5.0")  # Expecting the sum of 2 and 3 (5.0)


if __name__ == "__main__":
    unittest.main()
