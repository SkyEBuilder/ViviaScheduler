import datetime as DT
from pathlib import Path
from vivia_v4.templates import ExactDateTask


def make_exact_date_task():
    anchor = DT.datetime(2024, 1, 1, tzinfo=DT.timezone.utc)
    end = anchor + DT.timedelta(hours=3)
    return ExactDateTask(
        name="exact_demo",
        mandatory=True,
        priority=1,
        repeatition=2,
        start_interval=(anchor, anchor),
        end_interval=(end, end),
        duration_interval=(DT.timedelta(hours=3), DT.timedelta(hours=3)),
    )


def test_exact_date_round_trip_json_and_dict():
    t = make_exact_date_task()
    artifacts = Path("tests/artifacts")
    artifacts.mkdir(parents=True, exist_ok=True)

    dumped_json = t.model_dump_json(indent=2)
    (artifacts / "exact_date_original.json").write_text(dumped_json, encoding="utf-8")
    reloaded_json = ExactDateTask.model_validate_json(dumped_json)
    re_dumped_json = reloaded_json.model_dump_json(indent=2)
    (artifacts / "exact_date_reloaded.json").write_text(re_dumped_json, encoding="utf-8")
    assert t.model_dump() == reloaded_json.model_dump(), "ExactDateTask JSON round-trip mismatch"

    dumped_dict = t.model_dump()
    reloaded_dict = ExactDateTask.model_validate(dumped_dict)
    assert t.model_dump() == reloaded_dict.model_dump(), "ExactDateTask dict round-trip mismatch"

