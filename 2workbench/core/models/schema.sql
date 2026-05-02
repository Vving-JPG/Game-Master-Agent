-- ============================================================
-- Game Master Agent V3 — 数据库 Schema
-- 基于 V2 的 14 张表 + 新增 memories 表（统一记忆系统）
-- ============================================================

PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
PRAGMA busy_timeout=5000;

-- ===== 世界 =====
CREATE TABLE IF NOT EXISTS worlds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    setting TEXT DEFAULT 'fantasy',
    description TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- ===== 地点 =====
CREATE TABLE IF NOT EXISTS locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    world_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    connections TEXT DEFAULT '{}',  -- JSON: {"north": 2, "south": 3}
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (world_id) REFERENCES worlds(id) ON DELETE CASCADE
);

-- ===== 玩家 =====
CREATE TABLE IF NOT EXISTS players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    world_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    hp INTEGER DEFAULT 100,
    max_hp INTEGER DEFAULT 100,
    mp INTEGER DEFAULT 50,
    max_mp INTEGER DEFAULT 50,
    level INTEGER DEFAULT 1,
    exp INTEGER DEFAULT 0,
    gold INTEGER DEFAULT 0,
    location_id INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (world_id) REFERENCES worlds(id) ON DELETE CASCADE,
    FOREIGN KEY (location_id) REFERENCES locations(id)
);

-- ===== NPC =====
CREATE TABLE IF NOT EXISTS npcs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    world_id INTEGER NOT NULL,
    location_id INTEGER DEFAULT 0,
    name TEXT NOT NULL,
    personality TEXT DEFAULT '{}',      -- JSON: Personality
    backstory TEXT DEFAULT '',
    mood TEXT DEFAULT 'neutral',
    goals TEXT DEFAULT '[]',           -- JSON: [string]
    relationships TEXT DEFAULT '{}',   -- JSON: {"player": 0.5}
    speech_style TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (world_id) REFERENCES worlds(id) ON DELETE CASCADE,
    FOREIGN KEY (location_id) REFERENCES locations(id)
);

-- ===== 道具模板 =====
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    item_type TEXT DEFAULT 'misc',
    rarity TEXT DEFAULT 'common',
    slot TEXT DEFAULT '',
    stats TEXT DEFAULT '{}',           -- JSON: ItemStats
    description TEXT DEFAULT '',
    level_req INTEGER DEFAULT 1,
    stackable INTEGER DEFAULT 0,
    usable INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

-- ===== 玩家物品栏 =====
CREATE TABLE IF NOT EXISTS player_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id INTEGER NOT NULL,
    item_id INTEGER NOT NULL,
    quantity INTEGER DEFAULT 1,
    equipped INTEGER DEFAULT 0,
    FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE,
    FOREIGN KEY (item_id) REFERENCES items(id)
);

-- ===== 任务 =====
CREATE TABLE IF NOT EXISTS quests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    world_id INTEGER NOT NULL,
    player_id INTEGER DEFAULT NULL,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    quest_type TEXT DEFAULT 'side',
    status TEXT DEFAULT 'not_started',
    rewards TEXT DEFAULT '{}',         -- JSON
    prerequisites TEXT DEFAULT '{}',   -- JSON
    branches TEXT DEFAULT '{}',        -- JSON
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (world_id) REFERENCES worlds(id) ON DELETE CASCADE,
    FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE SET NULL
);

-- ===== 任务步骤 =====
CREATE TABLE IF NOT EXISTS quest_steps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    quest_id INTEGER NOT NULL,
    step_order INTEGER DEFAULT 0,
    description TEXT DEFAULT '',
    step_type TEXT DEFAULT '',         -- goto / kill / talk / collect
    target TEXT DEFAULT '',
    required_count INTEGER DEFAULT 1,
    current_count INTEGER DEFAULT 0,
    completed INTEGER DEFAULT 0,
    FOREIGN KEY (quest_id) REFERENCES quests(id) ON DELETE CASCADE
);

-- ===== 游戏日志 =====
CREATE TABLE IF NOT EXISTS game_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    world_id INTEGER NOT NULL,
    event_type TEXT DEFAULT 'system',
    content TEXT DEFAULT '',
    timestamp TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (world_id) REFERENCES worlds(id) ON DELETE CASCADE
);

-- ===== 对话消息 =====
CREATE TABLE IF NOT EXISTS game_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    world_id INTEGER NOT NULL,
    role TEXT DEFAULT 'user',
    name TEXT DEFAULT '',
    content TEXT DEFAULT '',
    timestamp TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (world_id) REFERENCES worlds(id) ON DELETE CASCADE
);

-- ===== Prompt 版本 =====
CREATE TABLE IF NOT EXISTS prompt_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt_key TEXT NOT NULL,
    content TEXT DEFAULT '',
    version INTEGER DEFAULT 1,
    is_active INTEGER DEFAULT 1,
    description TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now'))
);

-- ===== LLM 调用记录 =====
CREATE TABLE IF NOT EXISTS llm_calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    world_id INTEGER DEFAULT 0,
    call_type TEXT DEFAULT '',
    prompt_tokens INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    latency_ms INTEGER DEFAULT 0,
    model TEXT DEFAULT '',
    tool_calls_count INTEGER DEFAULT 0,
    tool_names TEXT DEFAULT '[]',      -- JSON
    error TEXT DEFAULT '',
    timestamp TEXT DEFAULT (datetime('now'))
);

-- ============================================================
-- 新增: 统一记忆表（替代 Markdown 文件记忆）
-- ============================================================
CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    world_id INTEGER NOT NULL,
    category TEXT DEFAULT 'session',   -- npc / location / player / quest / world / session
    source TEXT DEFAULT '',            -- 来源标识: "npc:张三" / "location:酒馆"
    title TEXT DEFAULT '',
    content TEXT DEFAULT '',           -- Markdown 格式内容
    importance REAL DEFAULT 0.5,       -- 重要性 0.0 - 1.0
    tags TEXT DEFAULT '[]',            -- JSON: ["战斗", "重要"]
    metadata TEXT DEFAULT '{}',        -- JSON: 扩展元数据
    turn_created INTEGER DEFAULT 0,    -- 创建时的回合数
    turn_last_referenced INTEGER DEFAULT 0,
    reference_count INTEGER DEFAULT 0, -- 被引用次数
    compressed INTEGER DEFAULT 0,      -- 是否已压缩
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (world_id) REFERENCES worlds(id) ON DELETE CASCADE
);

-- ============================================================
-- 索引
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_locations_world ON locations(world_id);
CREATE INDEX IF NOT EXISTS idx_players_world ON players(world_id);
CREATE INDEX IF NOT EXISTS idx_npcs_world ON npcs(world_id);
CREATE INDEX IF NOT EXISTS idx_npcs_location ON npcs(location_id);
CREATE INDEX IF NOT EXISTS idx_player_items_player ON player_items(player_id);
CREATE INDEX IF NOT EXISTS idx_quests_world ON quests(world_id);
CREATE INDEX IF NOT EXISTS idx_quests_player ON quests(player_id);
CREATE INDEX IF NOT EXISTS idx_quests_status ON quests(status);
CREATE INDEX IF NOT EXISTS idx_quest_steps_quest ON quest_steps(quest_id);
CREATE INDEX IF NOT EXISTS idx_game_logs_world ON game_logs(world_id);
CREATE INDEX IF NOT EXISTS idx_game_logs_timestamp ON game_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_game_messages_world ON game_messages(world_id);
CREATE INDEX IF NOT EXISTS idx_prompt_versions_key ON prompt_versions(prompt_key);
CREATE INDEX IF NOT EXISTS idx_llm_calls_world ON llm_calls(world_id);
CREATE INDEX IF NOT EXISTS idx_llm_calls_timestamp ON llm_calls(timestamp);

-- 记忆表索引
CREATE INDEX IF NOT EXISTS idx_memories_world ON memories(world_id);
CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(world_id, category);
CREATE INDEX IF NOT EXISTS idx_memories_source ON memories(world_id, source);
CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(world_id, importance DESC);
CREATE INDEX IF NOT EXISTS idx_memories_turn ON memories(world_id, turn_created);
CREATE INDEX IF NOT EXISTS idx_memories_tags ON memories(world_id, tags);