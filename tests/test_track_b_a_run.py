"""track_b_a_run.py 运行时配置绑定测试（P1-7）。

修复前："config #41/#42" 绑定只存在于注释中——不计算配置指纹、不写入输出。
修复后：运行时对特征列集（两臂）+ 面板文件字节计算 sha256，打印到 stdout
（``[track_b] config_sha256=...``）并写入 differential 模式的 site_data JSON
（``config_sha256`` 字段）。不引入 ledger 写入（超出本修复范围）。

测试策略（hermetic，无网络）：
- 指纹函数路径：小 parquet 面板帧写入 tmp，验证 sha 存在、稳定、对输入敏感；
- main() 接线路径：stub 掉重型模型拟合（``_run_arm``），验证 stdout 与
  site_data JSON 都携带 ``config_sha256`` 且与 ``_config_sha256`` 一致。
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import track_b_a_run as runner  # noqa: E402

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


@pytest.fixture
def small_panel(tmp_path: Path) -> Path:
    """Hermetic 小面板帧（真实 parquet 文件，供指纹函数路径消费）。"""
    panel_path = tmp_path / "cache" / "track_b_panel.parquet"
    panel_path.parent.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(0)
    panel = pd.DataFrame({
        "date": pd.bdate_range("2020-01-01", periods=10).repeat(2),
        "ticker": ["A", "B"] * 10,
        "close": rng.uniform(90.0, 110.0, 20),
    })
    panel.to_parquet(panel_path)
    return panel_path


def _stub_arm_result(mean_ic: float) -> SimpleNamespace:
    """fit_track_b_baseline 结果的最小 stub（只含 main() 消费的字段）。"""
    months = pd.date_range("2020-01-31", periods=30, freq="ME")
    ic = pd.Series(np.linspace(mean_ic - 0.01, mean_ic + 0.01, 30), index=months)
    return SimpleNamespace(
        mean_ic=mean_ic,
        ci_95=(mean_ic - 0.02, mean_ic + 0.02),
        p_hac=0.5,
        dm_stat=1.0,
        dm_p=0.3,
        n_walk_folds=3,
        ic_series=ic,
        monthly_dates=[d.strftime("%Y-%m-%d") for d in months],
        monthly_model_returns=[0.01] * 30,
        monthly_ew_returns=[0.008] * 30,
        oos_scores=pd.DataFrame({
            "date": pd.to_datetime(["2020-01-02", "2020-01-02"]),
            "ticker": ["A", "B"],
            "score": [0.1, -0.1],
        }),
    )


class TestConfigSha256FunctionPath:
    """指纹函数路径：sha 字段存在且稳定，对特征列集与面板字节敏感。"""

    def test_sha_is_stable_and_wellformed(self, small_panel: Path) -> None:
        sha_1 = runner._config_sha256(small_panel)
        sha_2 = runner._config_sha256(small_panel)

        # 稳定：同输入两次调用比特级一致
        assert sha_1 == sha_2
        # 良构：64 位小写十六进制 sha256
        assert _SHA256_RE.match(sha_1)

    def test_sha_changes_when_panel_bytes_change(self, small_panel: Path) -> None:
        sha_before = runner._config_sha256(small_panel)

        # 面板文件字节变化（追加一行）
        panel = pd.read_parquet(small_panel)
        panel.loc[len(panel)] = {"date": panel["date"].iloc[-1], "ticker": "A", "close": 123.0}
        panel.to_parquet(small_panel)

        assert runner._config_sha256(small_panel) != sha_before

    def test_sha_changes_when_feature_sets_change(
        self, small_panel: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        sha_before = runner._config_sha256(small_panel)

        # 特征列集变化（treatment 臂加一列）→ 指纹必须变化
        changed_arms = {
            arm: (list(feats) + ["extra_feature"] if arm == "treatment" else list(feats))
            for arm, feats in runner.ARMS.items()
        }
        monkeypatch.setattr(runner, "ARMS", changed_arms)

        assert runner._config_sha256(small_panel) != sha_before

    def test_sha_ignores_arm_dict_ordering(
        self, small_panel: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """特征集合相同但 ARMS 构造顺序不同 → 指纹必须不变（确定性）。"""
        sha_before = runner._config_sha256(small_panel)
        reordered_arms = {arm: runner.ARMS[arm] for arm in sorted(runner.ARMS, reverse=True)}
        monkeypatch.setattr(runner, "ARMS", reordered_arms)

        assert runner._config_sha256(small_panel) == sha_before


class TestArmsMatchDocstringConfig:
    """钉住模块 docstring 的配置声明：#41 = 23 特征，#42 = 10 特征。"""

    def test_treatment_arm_has_23_features(self) -> None:
        assert len(runner.ARMS["treatment"]) == 23

    def test_price_only_arm_has_10_features(self) -> None:
        assert len(runner.ARMS["price_only"]) == 10


class TestMainWiring:
    """main() 接线路径：stdout 与 site_data JSON 都携带 config_sha256。"""

    def _run_main_differential(
        self,
        small_panel: Path,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> dict:
        monkeypatch.setattr(runner, "PANEL_PATH", small_panel)
        monkeypatch.setattr(
            runner, "settings", SimpleNamespace(data_dir=tmp_path / "data")
        )
        monkeypatch.setattr(
            runner,
            "_run_arm",
            lambda panel, arm: _stub_arm_result(0.02 if arm == "treatment" else 0.005),
        )
        monkeypatch.setattr(sys, "argv", ["track_b_a_run.py", "--mode", "differential"])

        runner.main()

        out = capsys.readouterr().out
        site_file = tmp_path / "site" / "track_b_data.json"
        assert site_file.exists()
        return {"stdout": out, "site_data": json.loads(site_file.read_text(encoding="utf-8"))}

    def test_site_data_carries_config_sha256(
        self,
        small_panel: Path,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        result = self._run_main_differential(small_panel, tmp_path, monkeypatch, capsys)

        # sha 字段存在于输出摘要，且与函数路径重算值一致
        assert result["site_data"]["config_sha256"] == runner._config_sha256(small_panel)

    def test_stdout_prints_config_sha256_line(
        self,
        small_panel: Path,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        result = self._run_main_differential(small_panel, tmp_path, monkeypatch, capsys)

        expected_line = f"[track_b] config_sha256={runner._config_sha256(small_panel)}"
        assert expected_line in result["stdout"]

    def test_site_data_sha_stable_across_reruns(
        self,
        small_panel: Path,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        sha_1 = self._run_main_differential(small_panel, tmp_path, monkeypatch, capsys)[
            "site_data"
        ]["config_sha256"]
        sha_2 = self._run_main_differential(small_panel, tmp_path, monkeypatch, capsys)[
            "site_data"
        ]["config_sha256"]

        assert sha_1 == sha_2
        assert _SHA256_RE.match(sha_1)

    def test_single_arm_mode_prints_config_sha256(
        self,
        small_panel: Path,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setattr(runner, "PANEL_PATH", small_panel)
        monkeypatch.setattr(
            runner, "settings", SimpleNamespace(data_dir=tmp_path / "data")
        )
        monkeypatch.setattr(runner, "_run_arm", lambda panel, arm: _stub_arm_result(0.01))
        monkeypatch.setattr(sys, "argv", ["track_b_a_run.py", "--mode", "treatment"])

        runner.main()

        out = capsys.readouterr().out
        assert f"[track_b] config_sha256={runner._config_sha256(small_panel)}" in out

    def test_missing_panel_fails_like_existing_pattern(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """面板文件缺失 → 照既有模式 fail（read_parquet 抛 FileNotFoundError）。"""
        missing = tmp_path / "nope" / "track_b_panel.parquet"
        monkeypatch.setattr(runner, "PANEL_PATH", missing)
        monkeypatch.setattr(sys, "argv", ["track_b_a_run.py", "--mode", "treatment"])

        with pytest.raises(FileNotFoundError):
            runner.main()


def test_fingerprint_matches_manual_reference(small_panel: Path) -> None:
    """指纹 = sha256(sorted arms 特征列集序列 + 面板字节)，手算参照核对。"""
    hasher = hashlib.sha256()
    for arm in sorted(runner.ARMS):
        hasher.update(f"arm={arm};features={','.join(runner.ARMS[arm])};".encode())
    hasher.update(small_panel.read_bytes())

    assert runner._config_sha256(small_panel) == hasher.hexdigest()
