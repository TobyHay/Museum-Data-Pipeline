from live_pipeline import validate_info, extract_ids, convert_to_dict, format_time
import pytest
import logging


def define_logger() -> logging.Logger:
    logger = logging.getLogger('test')
    logger.setLevel(logging.ERROR)
    logger.addHandler(logging.NullHandler())
    return logger


logger = define_logger()


@pytest.mark.parametrize(
    "event, expected_validity",
    [
        ({'at': '2025-03-11T17:00:00.000000+00:00', 'site': '6', 'val': 1}, False),
        ({'at': '2025-03-11T17:00:00.000000+00:00', 'site': 'abcd', 'val': 1}, False),
        ({'at': '2025-03-11T17:00:00.000000+00:00', 'site': '-1', 'val': 1}, False),
        ({'at': '2025-03-11T17:00:00.000000+00:00', 'site': '1', 'val': -1}, False),
        ({'at': '2025-03-11T17:00:00.000000+00:00', 'site': '1', 'val': -1, 'type': None},
         False),
        ({'site': '1', 'val': 1}, False),
        ({'at': '2025-03-11T17:00:00.000000+00:00', 'site': '1', 'val': 5}, False),

        ({'at': '2025-03-11T17:00:00.000000+00:00', 'site': '0', 'val': 0}, True),
        ({'at': '2025-03-11T17:00:00.000000+00:00', 'site': '1', 'val': -1, 'type': 0},
         True),
        ({'at': '2025-03-11T17:00:00.000000+00:00', 'site': '5', 'val': 4}, True)
    ])
def test_validate_info(caplog, event, expected_validity):
    is_valid = validate_info(event, logger)

    if expected_validity == False:
        assert "Invalid" in caplog.text
    assert is_valid == expected_validity
