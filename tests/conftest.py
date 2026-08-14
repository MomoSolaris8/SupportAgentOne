from pathlib import Path

import pytest


TEST_ROOT = Path(__file__).parent.resolve()
PROJECT_ROOT = TEST_ROOT.parent


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Return the repository root for tests that load project data files."""
    return PROJECT_ROOT


DIRECTORY_MARKERS = {
    "unit": "unit",
    "component": "component",
    "integration": "integration",
    "evals": "eval",
    "e2e": "e2e",
}


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register explicit opt-ins for tests that can touch external systems."""

    group = parser.getgroup("supportagent test layers")
    group.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Run tests against real infrastructure such as databases or storage.",
    )
    group.addoption(
        "--run-live",
        action="store_true",
        default=False,
        help="Run tests that call real AI or external service providers.",
    )
    group.addoption(
        "--run-e2e",
        action="store_true",
        default=False,
        help="Run end-to-end tests against a deployed application.",
    )


def pytest_collection_modifyitems(
    config: pytest.Config,
    items: list[pytest.Item],
) -> None:
    """Apply test-layer markers based on the directory structure."""

    for item in items:
        test_path = Path(str(item.path)).resolve()

        try:
            relative_path = test_path.relative_to(TEST_ROOT)
        except ValueError:
            continue

        if not relative_path.parts:
            continue

        test_layer = relative_path.parts[0]
        marker_name = DIRECTORY_MARKERS.get(test_layer)

        if marker_name:
            item.add_marker(getattr(pytest.mark, marker_name))

        if relative_path.parts[:2] == ("evals", "live"):
            item.add_marker(pytest.mark.live)

        opt_in_layers = {
            "integration": (
                "run_integration",
                "requires --run-integration because it uses real infrastructure",
            ),
            "live": (
                "run_live",
                "requires --run-live because it calls real external providers",
            ),
            "e2e": (
                "run_e2e",
                "requires --run-e2e because it targets a deployed application",
            ),
        }

        for test_marker, (option, reason) in opt_in_layers.items():
            if item.get_closest_marker(test_marker) and not config.getoption(option):
                item.add_marker(pytest.mark.skip(reason=reason))
