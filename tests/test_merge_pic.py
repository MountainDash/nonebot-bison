import pytest
import typing

if typing.TYPE_CHECKING:
    import sys
    sys.path.append('./src/plugins')
    import nonebot_hk_reporter

merge_source_9 = [
        'https://wx1.sinaimg.cn/large/0071VPLMgy1gq0vib7zooj30dx0dxmz5.jpg',
        "https://wx4.sinaimg.cn/large/0071VPLMgy1gq0vib5oqjj30dw0dxjt2.jpg",
        "https://wx2.sinaimg.cn/large/0071VPLMgy1gq0vib8bjmj30dv0dxgn7.jpg",
        "https://wx1.sinaimg.cn/large/0071VPLMgy1gq0vib6pn1j30dx0dw75v.jpg",
        "https://wx4.sinaimg.cn/large/0071VPLMgy1gq0vib925mj30dw0dwabb.jpg",
        "https://wx2.sinaimg.cn/large/0071VPLMgy1gq0vib7ujuj30dv0dwtap.jpg",
        "https://wx1.sinaimg.cn/large/0071VPLMgy1gq0vibaexnj30dx0dvq49.jpg",
        "https://wx1.sinaimg.cn/large/0071VPLMgy1gq0vibehw4j30dw0dv74u.jpg",
        "https://wx1.sinaimg.cn/large/0071VPLMgy1gq0vibfb5fj30dv0dvtac.jpg",
        "https://wx3.sinaimg.cn/large/0071VPLMgy1gq0viexkjxj30rs3pcx6p.jpg",
        "https://wx2.sinaimg.cn/large/0071VPLMgy1gq0vif6qrpj30rs4mou10.jpg",
        "https://wx4.sinaimg.cn/large/0071VPLMgy1gq0vifc826j30rs4a64qs.jpg",
        "https://wx1.sinaimg.cn/large/0071VPLMgy1gq0vify21lj30rsbj71ld.jpg",
    ]

@pytest.mark.asyncio
async def test_9_merge(plugin_module: 'nonebot_hk_reporter'):
    post = plugin_module.post.Post('', '', '', pics=merge_source_9)
    await post._pic_merge() 
    assert len(post.pics) == 5
    await post.generate_messages()

@pytest.mark.asyncio
async def test_6_merge(plugin_module):
    post = plugin_module.post.Post('', '', '', pics=merge_source_9[0:6]+merge_source_9[9:])
    await post._pic_merge() 
    assert len(post.pics) == 5

@pytest.mark.asyncio
async def test_3_merge(plugin_module):
    post = plugin_module.post.Post('', '', '', pics=merge_source_9[0:3]+merge_source_9[9:])
    await post._pic_merge() 
    assert len(post.pics) == 5

@pytest.mark.asyncio
async def test_6_merge_only(plugin_module):
    post = plugin_module.post.Post('', '', '', pics=merge_source_9[0:6])
    await post._pic_merge() 
    assert len(post.pics) == 1

@pytest.mark.asyncio
async def test_3_merge_only(plugin_module):
    post = plugin_module.post.Post('', '', '', pics=merge_source_9[0:3])
    await post._pic_merge() 
    assert len(post.pics) == 1
