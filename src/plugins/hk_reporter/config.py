from .utils import Singleton, supported_target_type
from . import plugin_config
from os import path
import nonebot
from tinydb import TinyDB, Query
from collections import defaultdict
import os


def get_config_path() -> str:
    if plugin_config.hk_reporter_config_path:
        data_dir = plugin_config.hk_reporter_config_path
    else:
        working_dir = os.getcwd()
        data_dir = path.join(working_dir, 'data')
    if not path.isdir(data_dir):
        os.makedirs(data_dir)
    return path.join(data_dir, 'hk_reporter.json')

class NoSuchUserException(Exception):
    pass

class NoSuchSubscribeException(Exception):
    pass

class Config(metaclass=Singleton):

    migrate_version = 1
    
    def __init__(self):
        self.db = TinyDB(get_config_path(), encoding='utf-8') 
        self.kv_config = self.db.table('kv')
        self.user_target = self.db.table('user_target')
        self.target_user_cache = {}
        self.target_list = {}
        self.next_index = defaultdict(lambda: 0)
         
    def add_subscribe(self, user, user_type, target, target_name, target_type):
        user_query = Query()
        query = (user_query.user == user) & (user_query.user_type == user_type)
        if (user_data := self.user_target.get(query)):
            # update
            subs: list = user_data.get('subs', [])
            subs.append({"target": target, "target_type": target_type, 'target_name': target_name})
            self.user_target.update({"subs": subs}, query)
        else:
            # insert
            self.user_target.insert({'user': user, 'user_type': user_type, 'subs': [{'target': target, 'target_type': target_type, 'target_name': target_name}]})
        self.update_send_cache()

    def list_subscribe(self, user, user_type): 
        query = Query()
        return self.user_target.get((query.user == user) & (query.user_type ==user_type))['subs']
    
    def del_subscribe(self, user, user_type, target, target_type):
        user_query = Query()
        query = (user_query.user == user) & (user_query.user_type == user_type)
        if not (query_res := self.user_target.get(query)):
            raise NoSuchUserException()
        subs = query_res.get('subs', [])
        for idx, sub in enumerate(subs):
            if sub.get('target') == target and sub.get('target_type') == target_type:
                subs.pop(idx)
                self.user_target.update({'subs': subs}, query)
                self.update_send_cache()
                return
        raise NoSuchSubscribeException()

    def update_send_cache(self):
        res = {target_type: defaultdict(list) for target_type in supported_target_type}
        # res = {target_type: defaultdict(lambda: defaultdict(list)) for target_type in supported_target_type}
        for user in self.user_target.all():
            for sub in user.get('subs', []):
                if not sub.get('target_type') in supported_target_type:
                    continue
                res[sub['target_type']][sub['target']].append({"user": user['user'], "user_type": user['user_type']})
        self.target_user_cache = res
        for target_type in self.target_user_cache:
            self.target_list[target_type] = list(self.target_user_cache[target_type].keys())

    def get_next_target(self, target_type):
        # FIXME 插入或删除target后对队列的影响（但是并不是大问题
        if not self.target_list[target_type]:
            return None
        self.next_index[target_type] %= len(self.target_list[target_type])
        res = self.target_list[target_type][self.next_index[target_type]]
        self.next_index[target_type] += 1
        return res

def start_up():
    config = Config()
    if not (search_res := config.kv_config.search(Query().name=="version")):
        config.kv_config.insert({"name": "version", "value": config.migrate_version})
    elif search_res[0].get("value") < config.migrate_version:
        pass
        # do migration
    config.update_send_cache()

nonebot.get_driver().on_startup(start_up)
