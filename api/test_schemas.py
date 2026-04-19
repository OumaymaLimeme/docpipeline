"""
Tests for api/schemas.py — covering JobOut and JobListOut Pydantic schemas.

PR context: the `from pydantic import BaseModel` import was removed from
schemas.py.  These tests act as a regression suite that will fail if that
import (or an equivalent provider) is missing.
"""

import sys
import os
import pytest
from datetime import datetime
from typing import List

# Make sure the api package directory is on sys.path when running tests
# directly from the repo root or from the api/ directory.
sys.path.insert(0, os.path.dirname(__file__))

# ---------------------------------------------------------------------------
# Smoke-test: importing schemas must not raise NameError / ImportError.
# This catches the regression introduced by removing `from pydantic import
# BaseModel` from schemas.py.
# ---------------------------------------------------------------------------
def test_schemas_module_importable():
    """schemas.py must be importable without NameError or ImportError."""
    import importlib
    import schemas  # noqa: F401 – existence check
    assert hasattr(schemas, "JobOut")
    assert hasattr(schemas, "JobListOut")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture()
def now():
    return datetime(2024, 6, 1, 12, 0, 0)


@pytest.fixture()
def valid_job_data(now):
    return {
        "id": "abc-123",
        "filename": "report.pdf",
        "file_type": "pdf",
        "status": "pending",
        "result": None,
        "error": None,
        "created_at": now,
        "updated_at": now,
    }


# ---------------------------------------------------------------------------
# JobOut — construction and field validation
# ---------------------------------------------------------------------------
from models import JobStatus  # noqa: E402
from schemas import JobOut, JobListOut  # noqa: E402


class TestJobOutConstruction:
    def test_all_required_fields_accepted(self, valid_job_data):
        job = JobOut(**valid_job_data)
        assert job.id == "abc-123"
        assert job.filename == "report.pdf"
        assert job.file_type == "pdf"
        assert job.status == JobStatus.PENDING
        assert job.result is None
        assert job.error is None

    def test_optional_result_defaults_to_none(self, now):
        job = JobOut(
            id="x",
            filename="f.txt",
            file_type="txt",
            status=JobStatus.PENDING,
            created_at=now,
            updated_at=now,
        )
        assert job.result is None

    def test_optional_error_defaults_to_none(self, now):
        job = JobOut(
            id="x",
            filename="f.txt",
            file_type="txt",
            status=JobStatus.PENDING,
            created_at=now,
            updated_at=now,
        )
        assert job.error is None

    def test_result_field_can_hold_string(self, valid_job_data):
        valid_job_data["result"] = "some extracted text"
        job = JobOut(**valid_job_data)
        assert job.result == "some extracted text"

    def test_error_field_can_hold_string(self, valid_job_data):
        valid_job_data["error"] = "timeout"
        job = JobOut(**valid_job_data)
        assert job.error == "timeout"

    def test_datetime_fields_preserved(self, valid_job_data, now):
        job = JobOut(**valid_job_data)
        assert job.created_at == now
        assert job.updated_at == now

    def test_all_job_statuses_accepted(self, now):
        for status in JobStatus:
            job = JobOut(
                id="id",
                filename="file.csv",
                file_type="csv",
                status=status,
                created_at=now,
                updated_at=now,
            )
            assert job.status == status

    def test_status_pending(self, valid_job_data):
        valid_job_data["status"] = JobStatus.PENDING
        job = JobOut(**valid_job_data)
        assert job.status == JobStatus.PENDING

    def test_status_processing(self, valid_job_data):
        valid_job_data["status"] = JobStatus.PROCESSING
        job = JobOut(**valid_job_data)
        assert job.status == JobStatus.PROCESSING

    def test_status_done(self, valid_job_data):
        valid_job_data["status"] = JobStatus.DONE
        job = JobOut(**valid_job_data)
        assert job.status == JobStatus.DONE

    def test_status_failed(self, valid_job_data):
        valid_job_data["status"] = JobStatus.FAILED
        job = JobOut(**valid_job_data)
        assert job.status == JobStatus.FAILED

    def test_string_status_value_coerced(self, valid_job_data):
        """JobStatus is a str-enum; raw string 'done' should be accepted."""
        valid_job_data["status"] = "done"
        job = JobOut(**valid_job_data)
        assert job.status == JobStatus.DONE

    def test_missing_required_id_raises(self, valid_job_data, now):
        from pydantic import ValidationError
        del valid_job_data["id"]
        with pytest.raises(ValidationError):
            JobOut(**valid_job_data)

    def test_missing_required_filename_raises(self, valid_job_data):
        from pydantic import ValidationError
        del valid_job_data["filename"]
        with pytest.raises(ValidationError):
            JobOut(**valid_job_data)

    def test_missing_required_file_type_raises(self, valid_job_data):
        from pydantic import ValidationError
        del valid_job_data["file_type"]
        with pytest.raises(ValidationError):
            JobOut(**valid_job_data)

    def test_missing_required_status_raises(self, valid_job_data):
        from pydantic import ValidationError
        del valid_job_data["status"]
        with pytest.raises(ValidationError):
            JobOut(**valid_job_data)

    def test_missing_created_at_raises(self, valid_job_data):
        from pydantic import ValidationError
        del valid_job_data["created_at"]
        with pytest.raises(ValidationError):
            JobOut(**valid_job_data)

    def test_missing_updated_at_raises(self, valid_job_data):
        from pydantic import ValidationError
        del valid_job_data["updated_at"]
        with pytest.raises(ValidationError):
            JobOut(**valid_job_data)

    def test_invalid_status_raises(self, valid_job_data):
        from pydantic import ValidationError
        valid_job_data["status"] = "unknown_status"
        with pytest.raises(ValidationError):
            JobOut(**valid_job_data)

    def test_invalid_created_at_type_raises(self, valid_job_data):
        from pydantic import ValidationError
        valid_job_data["created_at"] = "not-a-datetime"
        with pytest.raises(ValidationError):
            JobOut(**valid_job_data)


class TestJobOutFromAttributes:
    """Verify model_config = {"from_attributes": True} allows ORM-style init."""

    def test_from_orm_like_object(self, now):
        """JobOut must be constructable from an object with matching attributes."""

        class FakeOrmJob:
            id = "orm-1"
            filename = "data.xlsx"
            file_type = "xlsx"
            status = JobStatus.DONE
            result = "42 rows processed"
            error = None
            created_at = now
            updated_at = now

        job = JobOut.model_validate(FakeOrmJob(), from_attributes=True)
        assert job.id == "orm-1"
        assert job.filename == "data.xlsx"
        assert job.status == JobStatus.DONE
        assert job.result == "42 rows processed"
        assert job.error is None

    def test_from_attributes_config_is_set(self):
        assert JobOut.model_config.get("from_attributes") is True


class TestJobOutSerialization:
    def test_model_dump_returns_dict(self, valid_job_data):
        job = JobOut(**valid_job_data)
        data = job.model_dump()
        assert isinstance(data, dict)
        assert data["id"] == "abc-123"
        assert data["status"] == JobStatus.PENDING

    def test_model_dump_json_round_trip(self, valid_job_data):
        import json
        job = JobOut(**valid_job_data)
        json_str = job.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed["id"] == "abc-123"
        assert parsed["filename"] == "report.pdf"


# ---------------------------------------------------------------------------
# JobListOut — construction and field validation
# ---------------------------------------------------------------------------
class TestJobListOutConstruction:
    def _make_job(self, now, idx=0):
        return JobOut(
            id=f"id-{idx}",
            filename=f"file_{idx}.pdf",
            file_type="pdf",
            status=JobStatus.PENDING,
            created_at=now,
            updated_at=now,
        )

    def test_basic_construction(self, now):
        jobs = [self._make_job(now, i) for i in range(3)]
        listing = JobListOut(total=3, page=1, limit=10, jobs=jobs)
        assert listing.total == 3
        assert listing.page == 1
        assert listing.limit == 10
        assert len(listing.jobs) == 3

    def test_empty_jobs_list(self, now):
        listing = JobListOut(total=0, page=1, limit=10, jobs=[])
        assert listing.total == 0
        assert listing.jobs == []

    def test_jobs_field_type(self, now):
        jobs = [self._make_job(now)]
        listing = JobListOut(total=1, page=1, limit=5, jobs=jobs)
        assert isinstance(listing.jobs, list)
        assert isinstance(listing.jobs[0], JobOut)

    def test_missing_total_raises(self, now):
        from pydantic import ValidationError
        jobs = [self._make_job(now)]
        with pytest.raises(ValidationError):
            JobListOut(page=1, limit=10, jobs=jobs)

    def test_missing_page_raises(self, now):
        from pydantic import ValidationError
        jobs = [self._make_job(now)]
        with pytest.raises(ValidationError):
            JobListOut(total=1, limit=10, jobs=jobs)

    def test_missing_limit_raises(self, now):
        from pydantic import ValidationError
        jobs = [self._make_job(now)]
        with pytest.raises(ValidationError):
            JobListOut(total=1, page=1, jobs=jobs)

    def test_missing_jobs_raises(self, now):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            JobListOut(total=0, page=1, limit=10)

    def test_invalid_total_type_raises(self, now):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            JobListOut(total="many", page=1, limit=10, jobs=[])

    def test_page_zero_boundary(self, now):
        """page=0 is technically valid by type — schema does not restrict it."""
        listing = JobListOut(total=0, page=0, limit=10, jobs=[])
        assert listing.page == 0

    def test_large_page_and_limit(self, now):
        listing = JobListOut(total=1000, page=100, limit=100, jobs=[])
        assert listing.total == 1000
        assert listing.page == 100
        assert listing.limit == 100

    def test_model_dump_includes_jobs(self, now):
        jobs = [self._make_job(now)]
        listing = JobListOut(total=1, page=1, limit=10, jobs=jobs)
        data = listing.model_dump()
        assert "jobs" in data
        assert len(data["jobs"]) == 1
        assert data["jobs"][0]["id"] == "id-0"

    def test_jobs_preserve_all_statuses(self, now):
        """All four JobStatus variants must survive round-trip through JobListOut."""
        statuses = list(JobStatus)
        jobs = [
            JobOut(
                id=f"id-{i}",
                filename="f.txt",
                file_type="txt",
                status=s,
                created_at=now,
                updated_at=now,
            )
            for i, s in enumerate(statuses)
        ]
        listing = JobListOut(total=len(jobs), page=1, limit=10, jobs=jobs)
        result_statuses = [j.status for j in listing.jobs]
        assert result_statuses == statuses


# ---------------------------------------------------------------------------
# Regression: BaseModel import must exist in schemas module
# ---------------------------------------------------------------------------
class TestBaseModelImportRegression:
    """
    Regression test for the PR that removed `from pydantic import BaseModel`.
    JobOut and JobListOut must be proper Pydantic BaseModel subclasses.
    """

    def test_jobout_is_pydantic_basemodel(self):
        from pydantic import BaseModel
        assert issubclass(JobOut, BaseModel), (
            "JobOut must inherit from pydantic.BaseModel — "
            "check that 'from pydantic import BaseModel' is present in schemas.py"
        )

    def test_joblistout_is_pydantic_basemodel(self):
        from pydantic import BaseModel
        assert issubclass(JobListOut, BaseModel), (
            "JobListOut must inherit from pydantic.BaseModel — "
            "check that 'from pydantic import BaseModel' is present in schemas.py"
        )

    def test_jobout_has_model_fields(self):
        """Pydantic BaseModel subclasses expose model_fields."""
        assert hasattr(JobOut, "model_fields")
        fields = JobOut.model_fields
        assert "id" in fields
        assert "filename" in fields
        assert "file_type" in fields
        assert "status" in fields
        assert "result" in fields
        assert "error" in fields
        assert "created_at" in fields
        assert "updated_at" in fields

    def test_joblistout_has_model_fields(self):
        assert hasattr(JobListOut, "model_fields")
        fields = JobListOut.model_fields
        assert "total" in fields
        assert "page" in fields
        assert "limit" in fields
        assert "jobs" in fields