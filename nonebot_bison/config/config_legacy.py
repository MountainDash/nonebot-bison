import json
import os
from collections import defaultdict
from datetime import datetime
from os import path
from pathlib import Path
from typing import DefaultDict, Literal, Mapping, TypedDict

import nonebot
from nonebot.log import logger
from tinydb import Query, TinyDB

from ..platform import platform_manager
from ..plugin_config import plugin_config
from ..types import Target, User
from ..utils import Singleton
from .utils import NoSuchSubscribeException, NoSuchUserException

supported_target_type = platform_manager.keys()


def get_config_path() -> tuple[str, str]:
    if plugin_config.bison_config_path:
        data_dir = plugin_config.bison_config_path
    else:
        working_dir = os.getcwd()
        data_dir = path.join(working_dir, "data")
    if not path.isdir(data_dir):
        os.makedirs(data_dir)
    old_path = path.join(data_dir, "hk_reporter.json")
    new_path = path.join(data_dir, "bison.json")
    deprecated_maker_path = path.join(data_dir, "bison.json.deprecated")
    if os.path.exists(old_path) and not os.path.exists(new_path):
        os.rename(old_path, new_path)
    return new_path, deprecated_maker_path


def drop():
    if plugin_config.bison_config_path:
        data_dir = plugin_config.bison_config_path
    else:
        working_dir = os.getcwd()
        data_dir = path.join(working_dir, "data")
    old_path = path.join(data_dir, "bison.json")
    deprecated_marker_path = path.join(data_dir, "bison.json.deprecated")
    if os.path.exists(old_path):
        config.db.close()
        config.available = False
        with open(deprecated_marker_path, "w") as file:
            content = {
                "migration_time": datetime.now().isoformat(),
            }
            file.write(json.dumps(content))
        return True
    return False


class SubscribeContent(TypedDict):
    target: str
    target_type: str
    target_name: str
    cats: list[int]
    tags: list[str]


class ConfigContent(TypedDict):
    user: int
    user_type: Literal["group", "private"]
    subs: list[SubscribeContent]


class Config(metaclass=Singleton):
    "Dropping it!"

    migrate_version = 2

    def __init__(self):
        self._do_init()

    def _do_init(self):
        path, deprecated_marker_path = get_config_path()
        if Path(deprecated_marker_path).exists():
            self.available = False
        elif Path(path).exists():
            self.available = True
            self.db = TinyDB(path, encoding="utf-8")
            self.kv_config = self.db.table("kv")
            self.user_target = self.db.table("user_target")
            self.target_user_cache: dict[str, defaultdict[Target, list[User]]] = {}
            self.target_user_cat_cache = {}
            self.target_user_tag_cache = {}
            self.target_list = {}
            self.next_index: DefaultDict[str, int] = defaultdict(lambda: 0)
        else:
            self.available = False

    def add_subscribe(
        self, user, user_type, target, target_name, target_type, cats, tags
    ):
        user_query = Query()
        query = (user_query.user == user) & (user_query.user_type == user_type)
        if user_data := self.user_target.get(query):
            # update
            subs: list = user_data.get("subs", [])
            subs.append(
                {
                    "target": target,
                    "target_type": target_type,
                    "target_name": target_name,
                    "cats": cats,
                    "tags": tags,
                }
            )
            self.user_target.update({"subs": subs}, query)
        else:
            # insert
            self.user_target.insert(
                {
                    "user": user,
                    "user_type": user_type,
                    "subs": [
                        {
                            "target": target,
                            "target_type": target_type,
                            "target_name": target_name,
                            "cats": cats,
                            "tags": tags,
                        }
                    ],
                }
            )
        self.update_send_cache()

    def list_subscribe(self, user, user_type) -> list[SubscribeContent]:
        query = Query()
        if user_sub := self.user_target.get(
            (query.user == user) & (query.user_type == user_type)
        ):
            return user_sub["subs"]
        return []

    def get_all_subscribe(self):
        return self.user_target

    def del_subscribe(self, user, user_type, target, target_type):
        user_query = Query()
        query = (user_query.user == user) & (user_query.user_type == user_type)
        if not (query_res := self.user_target.get(query)):
            raise NoSuchUserException()
        subs = query_res.get("subs", [])
        for idx, sub in enumerate(subs):
            if sub.get("target") == target and sub.get("target_type") == target_type:
                subs.pop(idx)
                self.user_target.update({"subs": subs}, query)
                self.update_send_cache()
                return
        raise NoSuchSubscribeException()

    def update_subscribe(
        self, user, user_type, target, target_name, target_type, cats, tags
    ):
        user_query = Query()
        query = (user_query.user == user) & (user_query.user_type == user_type)
        if user_data := self.user_target.get(query):
            # update
            subs: list = user_data.get("subs", [])
            find_flag = False
            for item in subs:
                if item["target"] == target and item["target_type"] == target_type:
                    item["target_name"], item["cats"], item["tags"] = (
                        target_name,
                        cats,
                        tags,
                    )
                    find_flag = True
                    break
            if not find_flag:
                raise NoSuchSubscribeException()
            self.user_target.update({"subs": subs}, query)
        else:
            raise NoSuchUserException()
        self.update_send_cache()

    def update_send_cache(self):
        res = {target_type: defaultdict(list) for target_type in supported_target_type}
        cat_res = {
            target_type: defaultdict(lambda: defaultdict(list))
            for target_type in supported_target_type
        }
        tag_res = {
            target_type: defaultdict(lambda: defaultdict(list))
            for target_type in supported_target_type
        }
        # res = {target_type: defaultdict(lambda: defaultdict(list)) for target_type in supported_target_type}
        to_del = []
        for user in self.user_target.all():
            for sub in user.get("subs", []):
                if not sub.get("target_type") in supported_target_type:
                    to_del.append(
                        {
                            "user": user["user"],
                            "user_type": user["user_type"],
                            "target": sub["target"],
                            "target_type": sub["target_type"],
                        }
                    )
                    continue
                res[sub["target_type"]][sub["target"]].append(
                    User(user["user"], user["user_type"])
                )
                cat_res[sub["target_type"]][sub["target"]][
                    "{}-{}".format(user["user_type"], user["user"])
                ] = sub["cats"]
                tag_res[sub["target_type"]][sub["target"]][
                    "{}-{}".format(user["user_type"], user["user"])
                ] = sub["tags"]
        self.target_user_cache = res
        self.target_user_cat_cache = cat_res
        self.target_user_tag_cache = tag_res
        for target_type in self.target_user_cache:
            self.target_list[target_type] = list(
                self.target_user_cache[target_type].keys()
            )

        logger.info(f"Deleting {to_del}")
        for d in to_del:
            self.del_subscribe(**d)

    def get_sub_category(self, target_type, target, user_type, user):
        return self.target_user_cat_cache[target_type][target][
            "{}-{}".format(user_type, user)
        ]

    def get_sub_tags(self, target_type, target, user_type, user):
        return self.target_user_tag_cache[target_type][target][
            "{}-{}".format(user_type, user)
        ]

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
    if not config.available:
        return
    if not (search_res := config.kv_config.search(Query().name == "version")):
        config.kv_config.insert({"name": "version", "value": config.migrate_version})
    elif search_res[0].get("value") < config.migrate_version:
        query = Query()
        version_query = query.name == "version"
        cur_version = search_res[0].get("value")
        if cur_version == 1:
            cur_version = 2
            for user_conf in config.user_target.all():
                conf_id = user_conf.doc_id
                subs = user_conf["subs"]
                for sub in subs:
                    sub["cats"] = []
                    sub["tags"] = []
                config.user_target.update({"subs": subs}, doc_ids=[conf_id])
        config.kv_config.update({"value": config.migrate_version}, version_query)
        # do migration
    config.update_send_cache()


config = Config()
