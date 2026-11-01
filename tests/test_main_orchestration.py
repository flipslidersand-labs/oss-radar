"""main.main(): ソース別の失敗継続・スキップ・dry-run・stats 例外の握りつぶし・サマリー JSON"""

import json
import sys
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

sys.path.insert(0, str(Path(__file__).parent.parent))

import main
from models import Repo


def _repo(name: str) -> Repo:
    return Repo(name, "", 1, None, [], None, "test", "t")


def _run(args=(), *, token="tok", gs=None, ght=None, bj=None, oi=None, ingest_count=3, snapshot=None):
    """gs/ght/bj/oi: 戻り値(list) か例外。未指定は 1 件返す。"""

    def mk(v, default):
        v = default if v is None else v
        return {"side_effect": v} if isinstance(v, Exception) else {"return_value": v}

    with ExitStack() as st:
        st.enter_context(patch.object(main, "GITHUB_TOKEN", token))
        st.enter_context(patch.object(main, "EMBED_API_KEY", "k"))
        st.enter_context(patch.object(main, "EMBED_URL", "https://e.example/embed"))
        st.enter_context(patch("collectors.github_search.collect", **mk(gs, [_repo("gs/a")])))
        st.enter_context(patch("collectors.gh_trending.collect", **mk(ght, [_repo("gt/a")])))
        st.enter_context(patch("collectors.bestofjs.collect", **mk(bj, [_repo("bj/a")])))
        st.enter_context(patch("collectors.ossinsight.collect", **mk(oi, [_repo("oi/a")])))
        ingest = st.enter_context(patch("ingest.ingest", return_value=ingest_count))
        snap_kw = {"side_effect": snapshot} if snapshot else {}
        snap = st.enter_context(patch("oss_radar.stats.record_snapshot", **snap_kw))
        result = CliRunner().invoke(main.main, list(args))
    summary = None
    for line in result.stderr.splitlines():
        if line.startswith("{"):
            summary = json.loads(line)
    return result, summary, ingest, snap


def test_all_sources_ok_ingests_deduped():
    result, summary, ingest, _ = _run()
    assert result.exit_code == 0
    # gh_trending は daily/weekly で 2 回呼ばれるが同名は dedup される
    assert summary["sources"] == {"github_search": 1, "gh_trending": 2, "bestofjs": 1, "ossinsight": 1}
    assert summary["total_raw"] == 5 and summary["deduped"] == 4
    assert summary["upserted"] == 3 and summary["errors"] == []
    ingest.assert_called_once()
    assert len(ingest.call_args.args[0]) == 4


def test_source_failure_is_recorded_and_others_continue():
    result, summary, ingest, _ = _run(gs=RuntimeError("gs boom"), oi=RuntimeError("oi boom"))
    assert result.exit_code == 0
    assert {e["source"] for e in summary["errors"]} == {"github_search", "ossinsight"}
    assert summary["sources"]["github_search"] == 0 and summary["sources"]["ossinsight"] == 0
    assert summary["sources"]["bestofjs"] == 1
    ingest.assert_called_once()


def test_gh_trending_failure_per_period():
    _, summary, _, _ = _run(ght=RuntimeError("503"))
    assert {e["source"] for e in summary["errors"]} == {"gh_trending/daily", "gh_trending/weekly"}


def test_missing_github_token_skips_github_search():
    result, summary, _, _ = _run(token="")
    assert "GITHUB_TOKEN 未設定" in result.stderr
    assert summary["sources"]["github_search"] == 0 and summary["errors"] == []


def test_skip_flags():
    _, summary, _, _ = _run(("--skip-bestofjs", "--skip-ossinsight"))
    assert summary["sources"]["bestofjs"] == 0 and summary["sources"]["ossinsight"] == 0


def test_dry_run_does_not_ingest_or_snapshot():
    result, summary, ingest, snap = _run(("--dry-run",))
    assert "dry-run" in result.output
    assert summary["upserted"] == 0
    ingest.assert_not_called()
    snap.assert_not_called()


def test_snapshot_failure_is_swallowed_and_continues():
    result, _, _, snap = _run(snapshot=RuntimeError("qdrant down"))
    assert result.exit_code == 0
    assert snap.call_count == 4  # 4 ソースとも試行する
    assert "stats upsert" in result.stderr


def test_sources_numbered_and_ordered():
    result, _, _, _ = _run(("--skip-bestofjs",))
    out = result.output
    assert out.index("[1/4] GitHub Search API") < out.index("[2/4] github.com/trending")
    assert "[3/4] bestofjs … スキップ" in out
    assert out.index("[3/4]") < out.index("[4/4] ossinsight.io")


def test_snapshot_recorded_only_for_sources_that_succeeded():
    # 全バリアントが失敗したソースは 0 件の snapshot を記録しない(github_search 等と揃える)
    _, summary, _, snap = _run(ght=RuntimeError("503"), gs=RuntimeError("boom"))
    recorded = {c.args[1] for c in snap.call_args_list}
    assert recorded == {"bestofjs", "ossinsight"}
    assert summary["sources"]["gh_trending"] == 0
