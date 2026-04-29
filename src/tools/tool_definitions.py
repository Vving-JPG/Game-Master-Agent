"""GM 工具定义 - OpenAI function calling 格式的工具 Schema"""


# ========== 骰子工具 ==========
ROLL_DICE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "roll_dice",
        "description": "掷骰子。支持标准RPG骰子表达式，如 '2d6+3'（掷2个6面骰加3）、'1d20'（掷1个20面骰）、'd100'（掷1个100面骰）。",
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "骰子表达式，如 '2d6+3', '1d20', '3d8-1'"
                }
            },
            "required": ["expression"]
        }
    }
}

# ========== 世界状态工具 ==========
QUERY_WORLD_STATE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "query_world_state",
        "description": "查询当前游戏世界的状态信息。可以查询整体概览，也可以指定查询某个方面（如玩家位置、时间、天气等）。",
        "parameters": {
            "type": "object",
            "properties": {
                "aspect": {
                    "type": "string",
                    "description": "要查询的方面，可选值: 'overview'(概览), 'player_location'(玩家位置), 'active_quests'(活跃任务)。不指定则返回概览。"
                }
            },
            "required": []
        }
    }
}

UPDATE_WORLD_STATE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "update_world_state",
        "description": "更新游戏世界状态。用于改变玩家位置、时间流逝、天气变化等。",
        "parameters": {
            "type": "object",
            "properties": {
                "aspect": {
                    "type": "string",
                    "description": "要更新的方面，如 'player_location', 'time', 'weather'"
                },
                "value": {
                    "type": "string",
                    "description": "新的值"
                }
            },
            "required": ["aspect", "value"]
        }
    }
}

# ========== 地点工具 ==========
GET_LOCATION_INFO_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_location_info",
        "description": "获取某个地点的详细信息，包括描述和可前往的出口方向。",
        "parameters": {
            "type": "object",
            "properties": {
                "location_id": {
                    "type": "integer",
                    "description": "地点ID"
                }
            },
            "required": ["location_id"]
        }
    }
}

LIST_NPCS_AT_LOCATION_SCHEMA = {
    "type": "function",
    "function": {
        "name": "list_npcs_at_location",
        "description": "列出某个地点中的所有NPC。",
        "parameters": {
            "type": "object",
            "properties": {
                "location_id": {
                    "type": "integer",
                    "description": "地点ID"
                }
            },
            "required": ["location_id"]
        }
    }
}

# ========== 玩家工具 ==========
GET_PLAYER_INFO_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_player_info",
        "description": "获取玩家的完整信息，包括HP、MP、等级、经验值、金币、当前位置等。",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
}

UPDATE_PLAYER_INFO_SCHEMA = {
    "type": "function",
    "function": {
        "name": "update_player_info",
        "description": "更新玩家属性，如HP、MP、金币、等级、位置等。",
        "parameters": {
            "type": "object",
            "properties": {
                "hp": {"type": "integer", "description": "设置HP值"},
                "mp": {"type": "integer", "description": "设置MP值"},
                "gold": {"type": "integer", "description": "设置金币数量"},
                "level": {"type": "integer", "description": "设置等级"},
                "exp": {"type": "integer", "description": "设置经验值"},
                "location_id": {"type": "integer", "description": "设置当前位置ID"}
            },
            "required": []
        }
    }
}

# ========== NPC工具 ==========
GET_NPC_INFO_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_npc_info",
        "description": "获取NPC的详细信息，包括名字、性格、背景故事、心情等。",
        "parameters": {
            "type": "object",
            "properties": {
                "npc_id": {
                    "type": "integer",
                    "description": "NPC的ID"
                }
            },
            "required": ["npc_id"]
        }
    }
}

SEARCH_NPC_SCHEMA = {
    "type": "function",
    "function": {
        "name": "search_npc",
        "description": "按名字模糊搜索NPC。",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "NPC名字（支持模糊匹配）"
                }
            },
            "required": ["name"]
        }
    }
}

CREATE_NPC_SCHEMA = {
    "type": "function",
    "function": {
        "name": "create_npc",
        "description": "创建一个新的NPC。可以用预设性格模板快速创建，也可以自定义性格参数。",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "NPC名字"},
                "location_id": {"type": "integer", "description": "NPC所在地点ID"},
                "personality_type": {
                    "type": "string",
                    "description": "性格模板名: brave_warrior/mysterious_mage/friendly_merchant/sinister_villain/wise_elder/naive_villager"
                },
                "mood": {"type": "string", "description": "当前心情（可选，覆盖模板默认值）"},
                "speech_style": {"type": "string", "description": "说话风格（可选，覆盖模板默认值）"},
                "backstory": {"type": "string", "description": "背景故事（可选）"}
            },
            "required": ["name", "location_id"]
        }
    }
}

NPC_DIALOG_SCHEMA = {
    "type": "function",
    "function": {
        "name": "npc_dialog",
        "description": "让NPC与玩家对话。会根据NPC的性格、心情、目标和记忆生成符合人设的回复。",
        "parameters": {
            "type": "object",
            "properties": {
                "npc_id": {"type": "integer", "description": "NPC的ID"},
                "player_message": {"type": "string", "description": "玩家对NPC说的话"}
            },
            "required": ["npc_id", "player_message"]
        }
    }
}

UPDATE_RELATIONSHIP_SCHEMA = {
    "type": "function",
    "function": {
        "name": "update_relationship",
        "description": "更新NPC与目标之间的关系值。关系值范围-100到+100。正值表示友好，负值表示敌对。",
        "parameters": {
            "type": "object",
            "properties": {
                "npc_id": {"type": "integer", "description": "NPC的ID"},
                "target_id": {"type": "integer", "description": "目标ID（玩家或其他NPC的ID）"},
                "change": {"type": "integer", "description": "关系变化值（正数=变好，负数=变差）"}
            },
            "required": ["npc_id", "target_id", "change"]
        }
    }
}

GET_RELATIONSHIP_GRAPH_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_relationship_graph",
        "description": "获取NPC的关系网络图。",
        "parameters": {
            "type": "object",
            "properties": {
                "npc_id": {"type": "integer", "description": "NPC的ID（可选，不指定则返回所有关系）"}
            },
            "required": []
        }
    }
}

CREATE_QUEST_SCHEMA = {
    "type": "function",
    "function": {
        "name": "create_quest",
        "description": "创建一个新任务。可以用剧情模板快速生成，也可以自定义。",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "任务标题"},
                "description": {"type": "string", "description": "任务描述"},
                "quest_type": {"type": "string", "description": "类型: main/side/random"},
                "template_name": {"type": "string", "description": "剧情模板名(可选): rescue/escort/collect/investigate/exterminate"},
                "template_vars": {"type": "string", "description": "模板变量JSON(可选)，如 '{\"victim\":\"公主\"}'"}
            },
            "required": ["title", "description"]
        }
    }
}

UPDATE_QUEST_PROGRESS_SCHEMA = {
    "type": "function",
    "function": {
        "name": "update_quest_progress",
        "description": "更新任务步骤的进度。",
        "parameters": {
            "type": "object",
            "properties": {
                "quest_id": {"type": "integer", "description": "任务ID"},
                "step_index": {"type": "integer", "description": "步骤序号（从0开始）"},
                "progress": {"type": "integer", "description": "当前进度值"}
            },
            "required": ["quest_id", "step_index", "progress"]
        }
    }
}

HANDLE_CHOICE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "handle_choice",
        "description": "处理玩家的分支选择。",
        "parameters": {
            "type": "object",
            "properties": {
                "quest_id": {"type": "integer", "description": "任务ID"},
                "choice_id": {"type": "string", "description": "选择的分支ID"}
            },
            "required": ["quest_id", "choice_id"]
        }
    }
}

CREATE_ITEM_SCHEMA = {
    "type": "function",
    "function": {
        "name": "create_item",
        "description": "创建一个新的道具模板。",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "道具名称"},
                "item_type": {"type": "string", "description": "类型: weapon/armor/potion/misc"},
                "rarity": {"type": "string", "description": "稀有度: common/uncommon/rare/epic/legendary"},
                "stats": {"type": "string", "description": "属性JSON，如 '{\"attack\":10}'"},
                "description": {"type": "string", "description": "道具描述"},
                "level_req": {"type": "integer", "description": "等级要求"},
                "stackable": {"type": "boolean", "description": "是否可堆叠"},
                "usable": {"type": "boolean", "description": "是否可使用"},
                "slot": {"type": "string", "description": "装备槽位: weapon/head/body/shield/accessory"}
            },
            "required": ["name"]
        }
    }
}

EQUIP_ITEM_SCHEMA = {
    "type": "function",
    "function": {
        "name": "equip_item",
        "description": "装备道具。",
        "parameters": {
            "type": "object",
            "properties": {
                "item_id": {"type": "integer", "description": "道具ID"}
            },
            "required": ["item_id"]
        }
    }
}

USE_ITEM_SCHEMA = {
    "type": "function",
    "function": {
        "name": "use_item",
        "description": "使用道具。",
        "parameters": {
            "type": "object",
            "properties": {
                "item_id": {"type": "integer", "description": "道具ID"}
            },
            "required": ["item_id"]
        }
    }
}

GET_INVENTORY_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_inventory",
        "description": "查看背包。",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
}

# ========== 日志工具 ==========
LOG_EVENT_SCHEMA = {
    "type": "function",
    "function": {
        "name": "log_event",
        "description": "记录游戏事件到日志。用于记录重要事件，如战斗结果、任务完成、重要发现等。",
        "parameters": {
            "type": "object",
            "properties": {
                "event_type": {
                    "type": "string",
                    "description": "事件类型: dialog(对话), combat(战斗), quest(任务), discovery(发现), system(系统), death(死亡), trade(交易)"
                },
                "content": {
                    "type": "string",
                    "description": "事件内容描述"
                }
            },
            "required": ["event_type", "content"]
        }
    }
}

# ========== 所有工具Schema列表 ==========
ALL_TOOL_SCHEMAS = [
    ROLL_DICE_SCHEMA,
    QUERY_WORLD_STATE_SCHEMA,
    UPDATE_WORLD_STATE_SCHEMA,
    GET_LOCATION_INFO_SCHEMA,
    LIST_NPCS_AT_LOCATION_SCHEMA,
    GET_PLAYER_INFO_SCHEMA,
    UPDATE_PLAYER_INFO_SCHEMA,
    GET_NPC_INFO_SCHEMA,
    SEARCH_NPC_SCHEMA,
    CREATE_NPC_SCHEMA,
    NPC_DIALOG_SCHEMA,
    UPDATE_RELATIONSHIP_SCHEMA,
    GET_RELATIONSHIP_GRAPH_SCHEMA,
    CREATE_QUEST_SCHEMA,
    UPDATE_QUEST_PROGRESS_SCHEMA,
    HANDLE_CHOICE_SCHEMA,
    CREATE_ITEM_SCHEMA,
    EQUIP_ITEM_SCHEMA,
    USE_ITEM_SCHEMA,
    GET_INVENTORY_SCHEMA,
    LOG_EVENT_SCHEMA,
]
