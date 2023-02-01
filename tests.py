# builtin modules
import os
import os.path
from pathlib import Path
import shutil
import subprocess
import tempfile
import uuid

# third-party modules
import pytest

# This is run by .github/workflows/ci.yml :)

EXECUTABLE_UNDER_TEST = "click-up-timereport.py"
ARTIFACTS_DIRECTORY="artifacts" # no trailing slash

@pytest.mark.parametrize("output_format", ["json", "pdf", "html"])
@pytest.mark.parametrize("output_title", ["Some title", False])
@pytest.mark.parametrize("company_logo", ["templates/company-logo.png", False])
@pytest.mark.parametrize("customer_name", ["Mr Customer", False])
@pytest.mark.parametrize("consultant_name", ["Ms Consultant", False])
@pytest.mark.parametrize("language", ["french", "english", False])
def test_output_from_static_json(output_format, output_title, company_logo, customer_name, consultant_name, language):
    os.makedirs(ARTIFACTS_DIRECTORY, exist_ok=True)

    output_test_file_path = "{}/{}_test_{}.{}".format(ARTIFACTS_DIRECTORY, output_format, uuid.uuid4(), output_format)
    command_line_list = [
            "python",
            EXECUTABLE_UNDER_TEST,
            "--from-json",
            "--json-input-path",
            "examples/example1.json",
            "--as-{}".format(output_format),
            "--{}-output-path".format(output_format),
            output_test_file_path,
        ]

    if output_title:
        command_line_list += ["--output-title", output_title]

    if company_logo:
        command_line_list += ["--company-logo-img-path", company_logo]

    if customer_name:
        command_line_list += ["--customer-name", customer_name] 

    if consultant_name:
        command_line_list += ["--consultant-name", consultant_name] 

    if language:
        command_line_list += ["--language", language] 

    result = subprocess.run(command_line_list)
    assert result.returncode == 0
    assert Path(output_test_file_path).resolve().is_file()
    assert os.path.getsize(output_test_file_path) > 1000
    if not os.environ.get("KEEP_FILES_FOR_ARTIFACTS"):
        shutil.rmtree(ARTIFACTS_DIRECTORY, ignore_errors=True)
