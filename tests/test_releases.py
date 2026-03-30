import datetime
import json
from typing import Any, List, cast
from unittest.mock import AsyncMock

import pytest

from ruyi_backend.app.releases import _get_latest_releases, _ide_plugin_url_generator
from ruyi_backend.components.github_stats import (
    ReleaseDownloadStats,
    query_release_downloads,
)
from ruyi_backend.schema.releases import LatestReleasesV1

from .fixtures import RuyiFileFixtureFactory


@pytest.fixture
def release_stats(ruyi_file: RuyiFileFixtureFactory) -> List[ReleaseDownloadStats]:
    with ruyi_file.path("github-release-stats-cache.json") as p:
        with open(p, "r") as f:
            return cast(List[ReleaseDownloadStats], json.load(f))


def test_get_latest_releases(release_stats: List[ReleaseDownloadStats]) -> None:
    stats: List[ReleaseDownloadStats] = release_stats

    def pm_url_generator(s: ReleaseDownloadStats) -> dict[str, list[str]]:
        from ruyi_backend.app.releases import _generate_download_urls

        return _generate_download_urls(s, "foo/bar")

    result: LatestReleasesV1 = _get_latest_releases(stats, pm_url_generator)
    channels = result.channels
    assert set(channels.keys()) == {"stable", "testing"}

    stable = channels["stable"]
    assert stable.version == "0.32.0"
    assert stable.channel == "stable"
    assert stable.release_date.isoformat() == "2025-04-21T23:35:47+00:00"
    assert stable.download_urls == {
        "linux/aarch64": [
            "https://github.com/foo/bar/releases/download/0.32.0/ruyi-0.32.0.arm64",
            "https://mirror.iscas.ac.cn/ruyisdk/ruyi/tags/0.32.0/ruyi-0.32.0.arm64",
        ],
        "linux/riscv64": [
            "https://github.com/foo/bar/releases/download/0.32.0/ruyi-0.32.0.riscv64",
            "https://mirror.iscas.ac.cn/ruyisdk/ruyi/tags/0.32.0/ruyi-0.32.0.riscv64",
        ],
        "linux/x86_64": [
            "https://github.com/foo/bar/releases/download/0.32.0/ruyi-0.32.0.amd64",
            "https://mirror.iscas.ac.cn/ruyisdk/ruyi/tags/0.32.0/ruyi-0.32.0.amd64",
        ],
    }

    testing = channels["testing"]
    assert testing.version == "0.32.0-beta.20250421"
    assert testing.channel == "testing"
    assert testing.release_date.isoformat() == "2025-04-21T14:33:33+00:00"
    assert testing.download_urls == {
        "linux/aarch64": [
            "https://github.com/foo/bar/releases/download/0.32.0-beta.20250421/ruyi-0.32.0-beta.20250421.arm64",
            "https://mirror.iscas.ac.cn/ruyisdk/ruyi/tags/0.32.0-beta.20250421/ruyi-0.32.0-beta.20250421.arm64",
        ],
        "linux/riscv64": [
            "https://github.com/foo/bar/releases/download/0.32.0-beta.20250421/ruyi-0.32.0-beta.20250421.riscv64",
            "https://mirror.iscas.ac.cn/ruyisdk/ruyi/tags/0.32.0-beta.20250421/ruyi-0.32.0-beta.20250421.riscv64",
        ],
        "linux/x86_64": [
            "https://github.com/foo/bar/releases/download/0.32.0-beta.20250421/ruyi-0.32.0-beta.20250421.amd64",
            "https://mirror.iscas.ac.cn/ruyisdk/ruyi/tags/0.32.0-beta.20250421/ruyi-0.32.0-beta.20250421.amd64",
        ],
    }


def test_ide_plugin_url_generator() -> None:
    # VSCode-style (tag matches version in filename)
    s_vscode: ReleaseDownloadStats = {
        "tag": "0.1.2",
        "date": datetime.datetime(2026, 3, 3, tzinfo=datetime.timezone.utc),
        "assets": [],
    }
    urls = _ide_plugin_url_generator(
        s_vscode,
        "ruyisdk/ruyisdk-vscode-extension",
        "ruyisdk-vscode-extension-0.1.2.vsix",
        "vscode",
    )
    assert urls == {
        "all/all": [
            "https://github.com/ruyisdk/ruyisdk-vscode-extension/releases/download/0.1.2/ruyisdk-vscode-extension-0.1.2.vsix",
            "https://mirrors.iscas.ac.cn/ruyisdk/ide/plugins/vscode/ruyisdk-vscode-extension-0.1.2.vsix",
        ],
    }

    # Eclipse-style (v-prefixed tag, but filename has no v)
    s_eclipse: ReleaseDownloadStats = {
        "tag": "v0.1.2",
        "date": datetime.datetime(2026, 3, 28, tzinfo=datetime.timezone.utc),
        "assets": [],
    }
    ver = s_eclipse["tag"].removeprefix("v")
    filename = f"ruyisdk-eclipse-plugins-{ver}.zip"
    urls = _ide_plugin_url_generator(
        s_eclipse,
        "ruyisdk/ruyisdk-eclipse-plugins",
        filename,
        "eclipse",
    )
    assert urls == {
        "all/all": [
            "https://github.com/ruyisdk/ruyisdk-eclipse-plugins/releases/download/v0.1.2/ruyisdk-eclipse-plugins-0.1.2.zip",
            "https://mirrors.iscas.ac.cn/ruyisdk/ide/plugins/eclipse/ruyisdk-eclipse-plugins-0.1.2.zip",
        ],
    }


@pytest.fixture
def mock_github_client(ruyi_file: RuyiFileFixtureFactory) -> AsyncMock:
    """Create a mock GitHub client that returns fixture data."""
    mock_client = AsyncMock()

    # Load the fixture data for paginated responses
    responses: dict[str | None, Any] = {}
    for cursor in (None, "NTA"):
        with ruyi_file.path(f"github-release-query-graphql.{cursor or '0'}.json") as p:
            with open(p, "r") as f:
                responses[cursor] = json.load(f)

    # Configure the mock to return appropriate responses based on cursor
    async def mock_graphql(query: str, variables: dict[str, Any]) -> Any:
        cursor = variables.get("cursor")
        return responses[cursor]

    mock_client.async_graphql = AsyncMock(side_effect=mock_graphql)
    return mock_client


@pytest.mark.asyncio
async def test_query_release_downloads(mock_github_client: AsyncMock) -> None:
    """Test that query_release_downloads correctly processes paginated GitHub API responses."""

    # Call the function with mock client
    result = await query_release_downloads(mock_github_client, "ruyisdk/ruyi")

    # Verify the function made the expected GraphQL calls
    mock_github_client.async_graphql.assert_called()
    assert mock_github_client.async_graphql.call_count == 2

    # First call should use no cursor
    first_call = mock_github_client.async_graphql.call_args_list[0]
    assert first_call.kwargs["variables"]["owner"] == "ruyisdk"
    assert first_call.kwargs["variables"]["name"] == "ruyi"
    assert first_call.kwargs["variables"]["cursor"] is None

    # Second call should use the cursor from first page
    second_call = mock_github_client.async_graphql.call_args_list[1]
    assert second_call.kwargs["variables"]["cursor"] == "NTA"

    # Verify the result structure
    assert isinstance(result, list)
    assert len(result) == 77

    # Check a few specific entries to ensure data is correctly transformed
    # First release from the first fixture
    first_release = result[0]
    assert first_release["tag"] == "0.32.0"
    assert first_release["assets"][0]["name"] == "ruyi-0.32.0.tar.gz"
    assert first_release["assets"][0]["download_count"] == 5

    # Last release from the second fixture (found near the end of the combined list)
    last_release = next(r for r in result if r["tag"] == "0.2.0-beta.20231204")
    assert last_release["tag"] == "0.2.0-beta.20231204"
    assert "assets" in last_release
    assert len(last_release["assets"]) == 3  # This specific release has 3 assets
