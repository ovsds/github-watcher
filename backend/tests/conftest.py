import pytest

import lib.plugin_registration as plugin_registration
import tests.settings as test_settings


@pytest.fixture(name="register_default_plugins", autouse=True, scope="session")
def register_default_plugins_fixture() -> None:
    plugin_registration.register_default_plugins()


@pytest.fixture(name="settings")
def settings_fixture() -> test_settings.Settings:
    return test_settings.Settings()
