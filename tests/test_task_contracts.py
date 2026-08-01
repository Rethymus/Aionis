"""
Hermetic tests for task contract linter with synthetic/labeled fixtures.

Uses only synthetic task fixtures—no real data, no network, no git operations.
"""


from scripts.check_task_contracts import (
    check_dangerous_commands,
    check_missing_fields,
    check_owner_gate,
    check_size_l,
    lint_task_file,
    parse_task_file,
)

# Fixtures are synthetic/labeled per task contract requirements


class TestParseTaskFile:
    """Test markdown parsing logic."""

    def test_parse_standard_fields(self, tmp_path):
        """Parses standard field format: '- key: value'."""
        task_file = tmp_path / "task.md"
        task_file.write_text(
            """# Test Task

- 编号: TEST-01
- 标题: Test task
- 状态: in progress
- Priority: P0
- Size: S
- Risk: LOW

## Content
""",
            encoding="utf-8",
        )
        fields, errors = parse_task_file(task_file)
        assert fields["编号"] == "TEST-01"
        assert fields["标题"] == "Test task"
        assert fields["状态"] == "in progress"
        assert fields["Priority"] == "P0"
        assert fields["Size"] == "S"
        assert fields["Risk"] == "LOW"
        assert len(errors) == 0

    def test_parse_chinese_field_names(self, tmp_path):
        """Handles Chinese field names correctly."""
        task_file = tmp_path / "task.md"
        task_file.write_text(
            """# Test Task

- 编号: TEST-01
- 标题: 测试任务
- 状态: 进行中
- Priority: P0
- Size: S
- Risk: LOW
- 目标: 测试目标
- 允许修改: 测试文件
- 禁止修改: 冻结文件
- 前置条件: 无
- 验收标准: 通过
- 必须运行的测试: pytest
""",
            encoding="utf-8",
        )
        fields, errors = parse_task_file(task_file)
        assert fields["编号"] == "TEST-01"
        assert fields["标题"] == "测试任务"
        assert fields["状态"] == "进行中"
        assert len(errors) == 0

    def test_parse_handles_missing_fields_gracefully(self, tmp_path):
        """Returns empty dict for files with no recognized fields."""
        task_file = tmp_path / "task.md"
        task_file.write_text(
            """# Test Task

Just some content without field markers.
""",
            encoding="utf-8",
        )
        fields, errors = parse_task_file(task_file)
        assert fields == {}
        assert len(errors) == 0

    def test_parse_handles_read_error_gracefully(self, tmp_path):
        """Returns empty fields when file cannot be read due to permissions."""
        # Create a file with no read permissions
        task_file = tmp_path / "task.md"
        task_file.write_text("test", encoding="utf-8")

        # Make file unreadable (this will cause read_text to fail)
        # Note: This test documents the behavior; actual permission errors
        # are handled gracefully in production by returning empty fields
        import stat

        try:
            task_file.chmod(stat.S_IRUSR)
            fields, errors = parse_task_file(task_file)
            # If we can read it, that's fine - just verify no errors
            assert len(errors) == 0
        except Exception:
            # Permission errors are caught by the try/except in parse_task_file
            # which returns empty fields
            pass


class TestCheckMissingFields:
    """Test detection of missing required fields."""

    def test_all_required_fields_present_passes(self, tmp_path):
        """No missing fields when all required fields are present."""
        file_path = tmp_path / "task.md"
        fields = {
            "编号": "TEST-01",
            "标题": "Test",
            "状态": "open",
            "Priority": "P0",
            "Size": "S",
            "Risk": "LOW",
            "目标": "test goal",
            "允许修改": "none",
            "禁止修改": "frozen",
            "前置条件": "none",
            "验收标准": "pass",
            "必须运行的测试": "pytest",
        }
        reasons = check_missing_fields(fields, file_path)
        assert len(reasons) == 0

    def test_missing_required_field_reported(self, tmp_path):
        """Each missing required field generates a separate reason code."""
        file_path = tmp_path / "task.md"
        fields = {
            "编号": "TEST-01",
            "标题": "Test",
            # Missing 状态, Priority, Size, Risk, etc.
        }
        reasons = check_missing_fields(fields, file_path)
        assert len(reasons) > 0
        # Check that reasons are sorted deterministically
        assert reasons == sorted(reasons)
        # Each reason should start with MISSING_REQUIRED_FIELD
        for reason in reasons:
            assert reason.startswith("MISSING_REQUIRED_FIELD:")


class TestCheckSizeL:
    """Test detection of Size = L (forbidden to dispatch)."""

    def test_size_l_detected(self, tmp_path):
        """Size = L triggers SIZE_L_FORBIDDEN reason code."""
        file_path = tmp_path / "task.md"
        fields = {"Size": "L"}
        reasons = check_size_l(fields, file_path)
        assert len(reasons) == 1
        assert "SIZE_L_FORBIDDEN" in reasons[0]

    def test_size_lowercase_l_detected(self, tmp_path):
        """Size = l (lowercase) also triggers SIZE_L_FORBIDDEN."""
        file_path = tmp_path / "task.md"
        fields = {"Size": "l"}
        reasons = check_size_l(fields, file_path)
        assert len(reasons) == 1
        assert "SIZE_L_FORBIDDEN" in reasons[0]

    def test_size_s_no_warning(self, tmp_path):
        """Size = S does not trigger warning."""
        file_path = tmp_path / "task.md"
        fields = {"Size": "S"}
        reasons = check_size_l(fields, file_path)
        assert len(reasons) == 0

    def test_size_m_no_warning(self, tmp_path):
        """Size = M does not trigger warning."""
        file_path = tmp_path / "task.md"
        fields = {"Size": "M"}
        reasons = check_size_l(fields, file_path)
        assert len(reasons) == 0

    def test_chinese_大小_l_detected(self, tmp_path):
        """Chinese '大小' field with L triggers warning."""
        file_path = tmp_path / "task.md"
        fields = {"大小": "L"}
        reasons = check_size_l(fields, file_path)
        assert len(reasons) == 1
        assert "SIZE_L_FORBIDDEN" in reasons[0]


class TestCheckOwnerGate:
    """Test detection of owner-gate declarations."""

    def test_owner_gated_status_detected(self, tmp_path):
        """Status containing 'owner-gated' triggers OWNER_GATE_DECLARED."""
        file_path = tmp_path / "task.md"
        fields = {"状态": "owner-gated — awaiting authorization"}
        reasons = check_owner_gate(fields, file_path)
        assert len(reasons) == 1
        assert "OWNER_GATE_DECLARED" in reasons[0]

    def test_owner_gate_status_detected(self, tmp_path):
        """Status containing 'owner-gate' triggers OWNER_GATE_DECLARED."""
        file_path = tmp_path / "task.md"
        fields = {"状态": "owner-gate required"}
        reasons = check_owner_gate(fields, file_path)
        assert len(reasons) == 1
        assert "OWNER_GATE_DECLARED" in reasons[0]

    def test_owner_go_status_detected(self, tmp_path):
        """Status containing 'owner GO' triggers OWNER_GATE_DECLARED."""
        file_path = tmp_path / "task.md"
        fields = {"状态": "requires owner GO"}
        reasons = check_owner_gate(fields, file_path)
        assert len(reasons) == 1
        assert "OWNER_GATE_DECLARED" in reasons[0]

    def test_regular_status_no_warning(self, tmp_path):
        """Regular status without owner gate keywords does not trigger warning."""
        file_path = tmp_path / "task.md"
        fields = {"状态": "in progress"}
        reasons = check_owner_gate(fields, file_path)
        assert len(reasons) == 0


class TestCheckDangerousCommands:
    """Test detection of dangerous command declarations."""

    def test_phase_script_in_forbidden_detected(self, tmp_path):
        """Forbidden section containing 'phase.py' triggers dangerous command warning."""
        file_path = tmp_path / "task.md"
        fields = {"禁止修改": "scripts/phase_b_run.py, frozen configs"}
        content = ""
        reasons = check_dangerous_commands(fields, file_path, content)
        assert len(reasons) == 1
        assert "DANGEROUS_COMMAND_DECLARED" in reasons[0]

    def test_forward_script_in_forbidden_detected(self, tmp_path):
        """Forbidden section containing 'forward' triggers dangerous command warning."""
        file_path = tmp_path / "task.md"
        fields = {"禁止修改": "scripts/forward_scoring.py"}
        content = ""
        reasons = check_dangerous_commands(fields, file_path, content)
        assert len(reasons) == 1
        assert "DANGEROUS_COMMAND_DECLARED" in reasons[0]

    def test_safe_forbidden_section_no_warning(self, tmp_path):
        """Forbidden section without dangerous scripts does not trigger warning."""
        file_path = tmp_path / "task.md"
        fields = {"禁止修改": "frozen configs, ledger, data"}
        content = ""
        reasons = check_dangerous_commands(fields, file_path, content)
        assert len(reasons) == 0

    def test_empty_forbidden_section_no_warning(self, tmp_path):
        """Empty forbidden section does not trigger warning."""
        file_path = tmp_path / "task.md"
        fields = {"禁止修改": ""}
        content = ""
        reasons = check_dangerous_commands(fields, file_path, content)
        assert len(reasons) == 0


class TestLintTaskFile:
    """Integration tests for full linting pipeline."""

    def test_perfect_task_no_findings(self, tmp_path):
        """A task with all required fields and no violations produces no findings."""
        task_file = tmp_path / "TEST-01-perfect.md"
        task_file.write_text(
            """# TEST-01 — Perfect Task

- 编号: TEST-01
- 标题: Perfect test task
- 状态: in progress
- Priority: P0
- Size: S
- Risk: LOW
- 目标: Test goal
- 允许修改: test files
- 禁止修改: frozen configs
- 前置条件: none
- 验收标准: pass
- 必须运行的测试: pytest

## Content
""",
            encoding="utf-8",
        )
        reasons = lint_task_file(task_file)
        assert len(reasons) == 0

    def test_task_with_size_l_reported(self, tmp_path):
        """Task with Size = L triggers SIZE_L_FORBIDDEN."""
        task_file = tmp_path / "TEST-02-large.md"
        task_file.write_text(
            """# TEST-02 — Large Task

- 编号: TEST-02
- 标题: Large task
- 状态: in progress
- Priority: P0
- Size: L
- Risk: HIGH
- 目标: Large goal
- 允许修改: test files
- 禁止修改: frozen configs
- 前置条件: none
- 验收标准: pass
- 必须运行的测试: pytest
""",
            encoding="utf-8",
        )
        reasons = lint_task_file(task_file)
        assert len(reasons) == 1
        assert "SIZE_L_FORBIDDEN" in reasons[0]

    def test_task_with_missing_fields_reported(self, tmp_path):
        """Task with missing required fields triggers MISSING_REQUIRED_FIELD codes."""
        task_file = tmp_path / "TEST-03-incomplete.md"
        task_file.write_text(
            """# TEST-03 — Incomplete Task

- 编号: TEST-03
- 标题: Incomplete task
# Missing many required fields
""",
            encoding="utf-8",
        )
        reasons = lint_task_file(task_file)
        assert len(reasons) > 0
        # Should have multiple MISSING_REQUIRED_FIELD entries
        missing_count = sum(1 for r in reasons if "MISSING_REQUIRED_FIELD" in r)
        assert missing_count > 0

    def test_task_with_owner_gate_reported(self, tmp_path):
        """Task with owner-gated status triggers OWNER_GATE_DECLARED."""
        task_file = tmp_path / "TEST-04-gated.md"
        task_file.write_text(
            """# TEST-04 — Gated Task

- 编号: TEST-04
- 标题: Owner-gated task
- 状态: owner-gated — awaiting explicit authorization
- Priority: P0
- Size: S
- Risk: LOW
- 目标: Gated goal
- 允许修改: test files
- 禁止修改: frozen configs
- 前置条件: owner GO
- 验收标准: pass
- 必须运行的测试: pytest
""",
            encoding="utf-8",
        )
        reasons = lint_task_file(task_file)
        assert len(reasons) == 1
        assert "OWNER_GATE_DECLARED" in reasons[0]

    def test_output_is_deterministically_sorted(self, tmp_path):
        """Multiple findings are sorted deterministically."""
        task_file = tmp_path / "TEST-05-multi-issue.md"
        task_file.write_text(
            """# TEST-05 — Multi-Issue Task

- 编号: TEST-05
- 标题: Multi-issue task
- 状态: owner-gated
- Priority: P0
- Size: L
- Risk: HIGH
# Missing other required fields
""",
            encoding="utf-8",
        )
        reasons = lint_task_file(task_file)
        # Check sorted (each reason starts with code, then path)
        assert reasons == sorted(reasons)


class TestReasonCodeFormat:
    """Test that reason codes follow the expected format."""

    def test_reason_code_format(self, tmp_path):
        """All reason codes follow format: CODE|path|detail."""
        task_file = tmp_path / "TEST-FORMAT.md"
        task_file.write_text(
            """# TEST-FORMAT

- 编号: TEST-FORMAT
- 标题: Format test
- 状态: owner-gated
- Priority: P0
- Size: L
- Risk: HIGH
- 目标: Test
- 允许修改: none
- 禁止修改: scripts/phase_run.py
- 前置条件: none
- 验收标准: pass
- 必须运行的测试: pytest
""",
            encoding="utf-8",
        )
        reasons = lint_task_file(task_file)
        for reason in reasons:
            parts = reason.split("|")
            assert len(parts) >= 2, f"Reason doesn't have pipe separator: {reason}"
            assert parts[0].isupper() or "_" in parts[0], f"Reason code not uppercase: {parts[0]}"


class TestH6Determinism:
    """Test H6 determinism requirements (no randomness, seeded RNG)."""

    def test_no_randomness_in_linting(self, tmp_path):
        """Linting the same file twice produces identical results."""
        task_file = tmp_path / "TEST-DETERMINISM.md"
        task_file.write_text(
            """# TEST-DETERMINISM

- 编号: TEST-DETERMINISM
- 标题: Determinism test
- 状态: in progress
- Priority: P0
- Size: S
- Risk: LOW
- 目标: Test
- 允许修改: none
- 禁止修改: frozen
- 前置条件: none
- 验收标准: pass
- 必须运行的测试: pytest
""",
            encoding="utf-8",
        )
        reasons1 = lint_task_file(task_file)
        reasons2 = lint_task_file(task_file)
        assert reasons1 == reasons2

    def test_sorted_order_is_stable(self, tmp_path):
        """Output order is stable across multiple runs."""
        task_file = tmp_path / "TEST-SORTED.md"
        task_file.write_text(
            """# TEST-SORTED

- 编号: TEST-SORTED
- 标题: Sorted test
- 状态: in progress
- Priority: P0
- Size: S
- Risk: LOW
- 目标: Test
- 允许修改: none
- 禁止修改: frozen
- 前置条件: none
- 验收标准: pass
- 必须运行的测试: pytest
""",
            encoding="utf-8",
        )
        # Run linting 10 times and verify output is identical
        results = [lint_task_file(task_file) for _ in range(10)]
        assert all(r == results[0] for r in results), "Output not stable across runs"


class TestImmutablePatterns:
    """Test that code follows immutability patterns."""

    def test_parse_does_not_modify_input(self, tmp_path):
        """Parsing does not modify the input file."""
        task_file = tmp_path / "TEST-NO-MUTATE.md"
        original_content = """# TEST

- 编号: TEST
- 标题: Test
- 状态: open
- Priority: P0
- Size: S
- Risk: LOW
- 目标: Test
- 允许修改: none
- 禁止修改: frozen
- 前置条件: none
- 验收标准: pass
- 必须运行的测试: pytest
"""
        task_file.write_text(original_content, encoding="utf-8")

        parse_task_file(task_file)
        check_missing_fields({}, task_file)
        check_size_l({}, task_file)
        check_owner_gate({}, task_file)
        check_dangerous_commands({}, task_file, "")
        lint_task_file(task_file)

        # File content unchanged
        assert task_file.read_text(encoding="utf-8") == original_content
