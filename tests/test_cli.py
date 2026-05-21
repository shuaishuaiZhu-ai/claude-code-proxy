import unittest

from ccproxy.cli import main


class CliTests(unittest.TestCase):
    def test_local_smoke_test(self) -> None:
        self.assertEqual(main(["test", "--profile", "minimax-cn"]), 0)


if __name__ == "__main__":
    unittest.main()
