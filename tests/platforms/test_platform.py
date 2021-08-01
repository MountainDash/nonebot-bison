import sys
import typing
from typing import Any, Optional

import pytest

if typing.TYPE_CHECKING:
    import sys
    sys.path.append('./src/plugins')
    import nonebot_hk_reporter
    from nonebot_hk_reporter.types import *
    from nonebot_hk_reporter.post import Post

from time import time
now = time()
passed = now - 3 * 60 * 60

raw_post_list_1 = [
        {'id': 1, 'text': 'p1', 'date': now, 'tags': ['tag1'], 'category': 1}
        ]

raw_post_list_2 = raw_post_list_1 + [
        {'id': 2, 'text': 'p2', 'date': now, 'tags': ['tag1'], 'category': 1},
        {'id': 3, 'text': 'p3', 'date': now, 'tags': ['tag2'], 'category': 2},
        {'id': 4, 'text': 'p4', 'date': now, 'tags': ['tag2'], 'category': 3}
        ]

@pytest.fixture
def dummy_user(plugin_module: 'nonebot_hk_reporter'):
    user = plugin_module.types.User('123', 'group')
    return user

@pytest.fixture
def user_info_factory(plugin_module: 'nonebot_hk_reporter', dummy_user):
    def _user_info(category_getter, tag_getter):
        return plugin_module.types.UserSubInfo(dummy_user, category_getter, tag_getter)
    return _user_info

@pytest.fixture
def mock_platform_without_cats_tags(plugin_module: 'nonebot_hk_reporter'):
    class MockPlatform(plugin_module.platform.platform.NewMessage,
            plugin_module.platform.platform.TargetMixin):

        platform_name = 'mock_platform'
        name = 'Mock Platform'
        enabled = True
        is_common = True
        schedule_interval = 10
        enable_tag = False
        categories = {}

        def __init__(self):
            self.sub_index = 0
            super().__init__()
        
        @staticmethod
        async def get_target_name(_: 'Target'):
            return 'MockPlatform'

        def get_id(self, post: 'RawPost') -> Any:
            return post['id']

        def get_date(self, raw_post: 'RawPost') -> float:
            return raw_post['date']

        async def parse(self, raw_post: 'RawPost') -> 'Post':
            return plugin_module.post.Post('mock_platform', raw_post['text'], 'http://t.tt/' + str(self.get_id(raw_post)), target_name='Mock')

        async def get_sub_list(self, _: 'Target'):
            if self.sub_index == 0:
                self.sub_index += 1
                return raw_post_list_1
            else:
                return raw_post_list_2

    return MockPlatform()

@pytest.fixture
def mock_platform(plugin_module: 'nonebot_hk_reporter'):
    class MockPlatform(plugin_module.platform.platform.NewMessage,
            plugin_module.platform.platform.TargetMixin):

        platform_name = 'mock_platform'
        name = 'Mock Platform'
        enabled = True
        is_common = True
        schedule_interval = 10
        enable_tag = True
        categories = {
                1: '转发',
                2: '视频',
            }
        def __init__(self):
            self.sub_index = 0
            super().__init__()
        
        @staticmethod
        async def get_target_name(_: 'Target'):
            return 'MockPlatform'

        def get_id(self, post: 'RawPost') -> Any:
            return post['id']

        def get_date(self, raw_post: 'RawPost') -> float:
            return raw_post['date']

        def get_tags(self, raw_post: 'RawPost') -> list['Tag']:
            return raw_post['tags']

        def get_category(self, raw_post: 'RawPost') -> 'Category':
            return raw_post['category']

        async def parse(self, raw_post: 'RawPost') -> 'Post':
            return plugin_module.post.Post('mock_platform', raw_post['text'], 'http://t.tt/' + str(self.get_id(raw_post)), target_name='Mock')

        async def get_sub_list(self, _: 'Target'):
            if self.sub_index == 0:
                self.sub_index += 1
                return raw_post_list_1
            else:
                return raw_post_list_2

    return MockPlatform()

@pytest.fixture
def mock_platform_no_target(plugin_module: 'nonebot_hk_reporter'):
    class MockPlatform(plugin_module.platform.platform.NewMessage,
            plugin_module.platform.platform.NoTargetMixin):

        platform_name = 'mock_platform'
        name = 'Mock Platform'
        enabled = True
        is_common = True
        schedule_type = 'interval'
        schedule_kw = {'seconds': 30}
        enable_tag = True
        categories = {
                1: '转发',
                2: '视频',
                3: '不支持'
            }
        def __init__(self):
            self.sub_index = 0
            super().__init__()
        
        @staticmethod
        async def get_target_name(_: 'Target'):
            return 'MockPlatform'

        def get_id(self, post: 'RawPost') -> Any:
            return post['id']

        def get_date(self, raw_post: 'RawPost') -> float:
            return raw_post['date']

        def get_tags(self, raw_post: 'RawPost') -> list['Tag']:
            return raw_post['tags']

        def get_category(self, raw_post: 'RawPost') -> 'Category':
            if raw_post['category'] == 3:
                raise plugin_module.platform.platform.CategoryNotSupport()
            return raw_post['category']

        async def parse(self, raw_post: 'RawPost') -> 'Post':
            return plugin_module.post.Post('mock_platform', raw_post['text'], 'http://t.tt/' + str(self.get_id(raw_post)), target_name='Mock')

        async def get_sub_list(self, _: 'Target'):
            if self.sub_index == 0:
                self.sub_index += 1
                return raw_post_list_1
            else:
                return raw_post_list_2

    return MockPlatform()

@pytest.fixture
def mock_platform_no_target_2(plugin_module: 'nonebot_hk_reporter'):
    class MockPlatform(plugin_module.platform.platform.NewMessage,
            plugin_module.platform.platform.NoTargetMixin):

        platform_name = 'mock_platform'
        name = 'Mock Platform'
        enabled = True
        schedule_type = 'interval'
        schedule_kw = {'seconds': 30}
        is_common = True
        enable_tag = True
        categories = {
                4: 'leixing4',
                5: 'leixing5',
            }
        def __init__(self):
            self.sub_index = 0
            super().__init__()
        
        @staticmethod
        async def get_target_name(_: 'Target'):
            return 'MockPlatform'

        def get_id(self, post: 'RawPost') -> Any:
            return post['id']

        def get_date(self, raw_post: 'RawPost') -> float:
            return raw_post['date']

        def get_tags(self, raw_post: 'RawPost') -> list['Tag']:
            return raw_post['tags']

        def get_category(self, raw_post: 'RawPost') -> 'Category':
            return raw_post['category']

        async def parse(self, raw_post: 'RawPost') -> 'Post':
            return plugin_module.post.Post('mock_platform_2', raw_post['text'], 'http://t.tt/' + str(self.get_id(raw_post)), target_name='Mock')

        async def get_sub_list(self, _: 'Target'):
            list_1 = [
                    {'id': 5, 'text': 'p5', 'date': now, 'tags': ['tag1'], 'category': 4}
                    ]

            list_2 = list_1 + [
                    {'id': 6, 'text': 'p6', 'date': now, 'tags': ['tag1'], 'category': 4},
                    {'id': 7, 'text': 'p7', 'date': now, 'tags': ['tag2'], 'category': 5},
                    ]
            if self.sub_index == 0:
                self.sub_index += 1
                return list_1
            else:
                return list_2

    return MockPlatform()

@pytest.fixture
def mock_status_change(plugin_module: 'nonebot_hk_reporter'):
    class MockPlatform(plugin_module.platform.platform.StatusChange,
            plugin_module.platform.platform.NoTargetMixin):

        platform_name = 'mock_platform'
        name = 'Mock Platform'
        enabled = True
        is_common = True
        enable_tag = False
        schedule_type = 'interval'
        schedule_kw = {'seconds': 10}
        categories = {
                1: '转发',
                2: '视频',
            }
        def __init__(self):
            self.sub_index = 0
            super().__init__()

        async def get_status(self, _: 'Target'):
            if self.sub_index == 0:
                self.sub_index += 1
                return {'s': False}
            elif self.sub_index == 1:
                self.sub_index += 1
                return {'s': True}
            else:
                return {'s': False}

        def compare_status(self, target, old_status, new_status) -> list['RawPost']:
            if old_status['s'] == False and new_status['s'] == True:
                return [{'text': 'on', 'cat': 1}]
            elif old_status['s'] == True and new_status['s'] == False:
                return [{'text': 'off', 'cat': 2}]
            return []

        async def parse(self, raw_post) -> 'Post':
            return plugin_module.post.Post('mock_status', raw_post['text'], '')

        def get_category(self, raw_post):
            return raw_post['cat']

    return MockPlatform()


@pytest.mark.asyncio
async def test_new_message_target_without_cats_tags(mock_platform_without_cats_tags, user_info_factory):
    res1 = await mock_platform_without_cats_tags.fetch_new_post('dummy', [user_info_factory(lambda _: [1,2], lambda _: [])])
    assert(len(res1) == 0)
    res2 = await mock_platform_without_cats_tags.fetch_new_post('dummy', [
        user_info_factory(lambda _: [], lambda _: []),
        ])
    assert(len(res2) == 1)
    posts_1 = res2[0][1]
    assert(len(posts_1) == 3)
    id_set_1 = set(map(lambda x: x.text, posts_1))
    assert('p2' in id_set_1 and 'p3' in id_set_1 and 'p4' in id_set_1)

@pytest.mark.asyncio
async def test_new_message_target(mock_platform, user_info_factory):
    res1 = await mock_platform.fetch_new_post('dummy', [user_info_factory(lambda _: [1,2], lambda _: [])])
    assert(len(res1) == 0)
    res2 = await mock_platform.fetch_new_post('dummy', [
        user_info_factory(lambda _: [1,2], lambda _: []),
        user_info_factory(lambda _: [1], lambda _: []),
        user_info_factory(lambda _: [1,2], lambda _: ['tag1'])
        ])
    assert(len(res2) == 3)
    posts_1 = res2[0][1]
    posts_2 = res2[1][1]
    posts_3 = res2[2][1]
    assert(len(posts_1) == 2)
    assert(len(posts_2) == 1)
    assert(len(posts_3) == 1)
    id_set_1 = set(map(lambda x: x.text, posts_1))
    id_set_2 = set(map(lambda x: x.text, posts_2))
    id_set_3 = set(map(lambda x: x.text, posts_3))
    assert('p2' in id_set_1 and 'p3' in id_set_1)
    assert('p2' in id_set_2)
    assert('p2' in id_set_3)

@pytest.mark.asyncio
async def test_new_message_no_target(mock_platform_no_target, user_info_factory):
    res1 = await mock_platform_no_target.fetch_new_post('dummy', [user_info_factory(lambda _: [1,2], lambda _: [])])
    assert(len(res1) == 0)
    res2 = await mock_platform_no_target.fetch_new_post('dummy', [
        user_info_factory(lambda _: [1,2], lambda _: []),
        user_info_factory(lambda _: [1], lambda _: []),
        user_info_factory(lambda _: [1,2], lambda _: ['tag1'])
        ])
    assert(len(res2) == 3)
    posts_1 = res2[0][1]
    posts_2 = res2[1][1]
    posts_3 = res2[2][1]
    assert(len(posts_1) == 2)
    assert(len(posts_2) == 1)
    assert(len(posts_3) == 1)
    id_set_1 = set(map(lambda x: x.text, posts_1))
    id_set_2 = set(map(lambda x: x.text, posts_2))
    id_set_3 = set(map(lambda x: x.text, posts_3))
    assert('p2' in id_set_1 and 'p3' in id_set_1)
    assert('p2' in id_set_2)
    assert('p2' in id_set_3)
    res3 = await mock_platform_no_target.fetch_new_post('dummy', [user_info_factory(lambda _: [1,2], lambda _: [])])
    assert(len(res3) == 0)

@pytest.mark.asyncio
async def test_status_change(mock_status_change, user_info_factory):
    res1 = await mock_status_change.fetch_new_post('dummy', [user_info_factory(lambda _: [1,2], lambda _: [])])
    assert(len(res1) == 0)
    res2 = await mock_status_change.fetch_new_post('dummy', [
        user_info_factory(lambda _: [1,2], lambda _:[])
        ])
    assert(len(res2) == 1)
    posts = res2[0][1]
    assert(len(posts) == 1)
    assert(posts[0].text == 'on')
    res3 = await mock_status_change.fetch_new_post('dummy', [
        user_info_factory(lambda _: [1,2], lambda _: []),
        user_info_factory(lambda _: [1], lambda _: []),
        ])
    assert(len(res3) == 2)
    assert(len(res3[0][1]) == 1)
    assert(res3[0][1][0].text == 'off')
    assert(len(res3[1][1]) == 0)
    res4 = await mock_status_change.fetch_new_post('dummy', [user_info_factory(lambda _: [1,2], lambda _: [])])
    assert(len(res4) == 0)

@pytest.mark.asyncio
async def test_group(plugin_module: 'nonebot_hk_reporter', mock_platform_no_target, mock_platform_no_target_2, user_info_factory):
    group_platform = plugin_module.platform.platform.NoTargetGroup([mock_platform_no_target, mock_platform_no_target_2])
    res1 = await group_platform.fetch_new_post('dummy', [user_info_factory(lambda _: [1,4], lambda _: [])])
    assert(len(res1) == 0)
    res2 = await group_platform.fetch_new_post('dummy', [user_info_factory(lambda _: [1,4], lambda _: [])])
    assert(len(res2) == 1)
    posts = res2[0][1]
    assert(len(posts) == 2)
    id_set_2 = set(map(lambda x: x.text, posts))
    assert('p2' in id_set_2 and 'p6' in id_set_2)
    res3 = await group_platform.fetch_new_post('dummy', [user_info_factory(lambda _: [1,4], lambda _: [])])
    assert(len(res3) == 0)
