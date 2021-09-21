from ..platform import platform_manager

async def test():
    return {"status": 200, "text": "test"}

async def get_global_conf():
    res = []
    for platform_name, platform in platform_manager.items():
        res.append({
            'platformName': platform_name,
            'categories': platform.categories,
            'enabledTag': platform.enable_tag,
            'name': platform.name,
            'hasTarget': getattr(platform, 'has_target')
            })
    return { 'platformConf': res }

