import pytest

import tests.settings as test_settings


@pytest.fixture(name="settings")
def settings_fixture() -> test_settings.Settings:
    return test_settings.Settings()
