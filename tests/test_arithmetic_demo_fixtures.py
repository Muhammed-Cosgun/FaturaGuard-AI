from scripts.generate_arithmetic_demo_fixtures import CASES, generate


def test_demo_fixture_generator_creates_only_validator_checked_cases(tmp_path) -> None:
    fixtures = generate(tmp_path)

    assert [path.name for path in fixtures] == [case.filename for case in CASES]
    assert all(path.is_file() and path.stat().st_size > 0 for path in fixtures)
