"""Checks for the public dependency and configuration contract."""

import tomllib
import unittest
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


class PublicConfigurationTests(unittest.TestCase):
    """Keep public setup instructions aligned with the recommended API."""

    def test_public_runtime_contract_matches_supported_environment(self):
        """Keep the API, Python, and data-source setup internally consistent."""
        runtime_requirements = (REPOSITORY_ROOT / "requirements" / "base.in").read_text(
            encoding="utf-8"
        )
        project_config = tomllib.loads(
            (REPOSITORY_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        )
        public_content = "\n".join(
            [
                (REPOSITORY_ROOT / "README.md").read_text(encoding="utf-8"),
                (REPOSITORY_ROOT / ".env.example").read_text(encoding="utf-8"),
                (
                    REPOSITORY_ROOT
                    / "dagster_pipelines"
                    / "assets"
                    / "portfolio_asset.py"
                ).read_text(encoding="utf-8"),
            ]
        )

        self.assertIn("vbase-api==0.1.3", runtime_requirements)
        self.assertNotIn("\nvbase==", "\n" + runtime_requirements)
        self.assertEqual(project_config["project"]["requires-python"], ">=3.12")
        self.assertEqual(project_config["tool"]["black"]["target-version"], ["py312"])
        self.assertIn("Python 3.12 or later", public_content)
        self.assertIn("most recent 60 days", public_content)
        for legacy_marker in (
            "VBASE_COMMITMENT_SERVICE_PRIVATE_KEY",
            "VBASE_FORWARDER_URL",
            "ForwarderCommitmentService",
            "VBaseDataset",
        ):
            with self.subTest(marker=legacy_marker):
                self.assertNotIn(legacy_marker, public_content)


if __name__ == "__main__":
    unittest.main()
