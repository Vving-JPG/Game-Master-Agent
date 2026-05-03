# P1-05: Constants 常量定义

> 模块: `core.constants`
> 文件: `2workbench/core/constants/npc_templates.py`, `story_templates.py`

---

## NPC 模板 (npc_templates.py)

### 五大人格模板

```python
PERSONALITY_TEMPLATES = {
    "hero": {
        "openness": 70,
        "conscientiousness": 80,
        "extraversion": 75,
        "agreeableness": 70,
        "neuroticism": 30,
    },
    "villain": {
        "openness": 60,
        "conscientiousness": 40,
        "extraversion": 80,
        "agreeableness": 20,
        "neuroticism": 70,
    },
    "mentor": {
        "openness": 75,
        "conscientiousness": 85,
        "extraversion": 50,
        "agreeableness": 80,
        "neuroticism": 25,
    },
    "merchant": {
        "openness": 60,
        "conscientiousness": 65,
        "extraversion": 85,
        "agreeableness": 60,
        "neuroticism": 40,
    },
    "mystic": {
        "openness": 90,
        "conscientiousness": 50,
        "extraversion": 30,
        "agreeableness": 65,
        "neuroticism": 60,
    },
    "guard": {
        "openness": 40,
        "conscientiousness": 90,
        "extraversion": 60,
        "agreeableness": 50,
        "neuroticism": 35,
    },
}
```

### 使用示例

```python
from core.constants import PERSONALITY_TEMPLATES

# 创建英雄 NPC
hero_personality = PERSONALITY_TEMPLATES["hero"]
npc = NPC(name="勇者", personality=Personality(**hero_personality))
```

---

## 剧情模板 (story_templates.py)

### 故事类型

```python
STORY_TEMPLATES = {
    "hero_journey": {
        "name": "英雄之旅",
        "stages": [
            "ordinary_world",      # 平凡世界
            "call_to_adventure",   # 冒险召唤
            "refusal",             # 拒绝召唤
            "meeting_mentor",      # 遇见导师
            "crossing_threshold",  # 跨越门槛
            "tests_allies",        # 考验与盟友
            "approach",            # 接近洞穴
            "ordeal",              # 磨难
            "reward",              # 奖励
            "road_back",           # 归途
            "resurrection",        # 复活
            "return",              # 携万能药归来
        ]
    },
    "revenge": {
        "name": "复仇",
        "stages": ["harm", "anger", "plan", "execution", "consequence"]
    },
    "redemption": {
        "name": "救赎",
        "stages": ["fall", "awareness", "struggle", "sacrifice", "redemption"]
    },
    "mystery": {
        "name": "悬疑",
        "stages": ["crime", "clues", "suspects", "revelation", "resolution"]
    },
    "romance": {
        "name": "浪漫",
        "stages": ["meet", "obstacle", "deepen", "crisis", "union"]
    },
}
```

### 使用示例

```python
from core.constants import STORY_TEMPLATES

# 获取英雄之旅模板
template = STORY_TEMPLATES["hero_journey"]
print(f"故事类型: {template['name']}")
print(f"阶段数: {len(template['stages'])}")
```

---

## 其他常量

### 游戏数值

```python
MAX_LEVEL = 100
BASE_EXP = 100
EXP_MULTIPLIER = 1.5

MAX_INVENTORY_SLOTS = 50
MAX_PARTY_SIZE = 4
MAX_QUEST_TRACKED = 5
```

### 文本模板

```python
DIALOGUE_TEMPLATES = {
    "greeting_friendly": ["你好！", "欢迎！", "很高兴见到你！"],
    "greeting_neutral": ["你好。", "有什么事吗？"],
    "greeting_hostile": ["哼。", "离我远点。"],
}
```
