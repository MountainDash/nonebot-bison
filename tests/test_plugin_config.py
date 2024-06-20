from nonebug.app import App


def test_parse_alias(app: App):
    from nonebot.compat import PYDANTIC_V2

    from nonebot_bison.plugin_config import PlugConfig

    if PYDANTIC_V2:
        cfg = PlugConfig.model_validate({"bison_theme_use_browser": True})
        assert cfg.bison_use_browser

        cfg = PlugConfig.model_validate({"bison_use_browser": True})
        assert cfg.bison_use_browser
    else:
        cfg = PlugConfig.parse_obj({"bison_theme_use_browser": True})
        assert cfg.bison_use_browser

        cfg = PlugConfig.parse_obj({"bison_use_browser": True})
        assert cfg.bison_use_browser
