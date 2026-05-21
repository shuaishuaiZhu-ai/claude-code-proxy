from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def read_script(name: str) -> str:
    return (SCRIPTS / name).read_text(encoding="utf-8")


class InstallScriptTests(unittest.TestCase):
    def test_install_scripts_exist_for_powershell_and_posix_shell(self) -> None:
        self.assertTrue((SCRIPTS / "install.ps1").exists())
        self.assertTrue((SCRIPTS / "install.sh").exists())

    def test_install_scripts_check_runtime_and_install_project(self) -> None:
        for name in ("install.ps1", "install.sh"):
            text = read_script(name)
            self.assertTrue("Python" in text or "python" in text)
            self.assertIn("pip", text)
            self.assertTrue("Claude" in text or "claude" in text)
            self.assertTrue("pip install" in text or 'pip" install' in text or "pip', 'install" in text)
            self.assertIn("-e", text)

    def test_uninstall_scripts_exist_for_powershell_and_posix_shell(self) -> None:
        self.assertTrue((SCRIPTS / "uninstall.ps1").exists())
        self.assertTrue((SCRIPTS / "uninstall.sh").exists())

    def test_uninstall_scripts_remove_package_and_state_without_system_dependencies(self) -> None:
        for name in ("uninstall.ps1", "uninstall.sh"):
            text = read_script(name)
            self.assertIn("claude-code-proxy", text)
            self.assertIn(".ccproxy", text)
            self.assertTrue("pip uninstall" in text or 'pip" uninstall' in text or "pip', 'uninstall" in text)
            self.assertIn("does not uninstall Python, pip, or Claude", text)


if __name__ == "__main__":
    unittest.main()
