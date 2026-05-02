# 工作流: 测试指定层

## Foundation 层测试
```powershell
cd 2workbench ; python -c "
from foundation.event_bus import event_bus, Event
from foundation.config import settings
from foundation.logger import get_logger
from foundation.database import init_db
from foundation.cache import llm_cache
import tempfile, os

# EventBus
event_bus.emit(Event(type='test', data={}))

# Config
print(f'Model: {settings.default_model}')

# Database
tmp = tempfile.mktemp(suffix='.db')
init_db(db_path=tmp)
os.unlink(tmp)

# Cache
llm_cache.set('test_key', 'test_value', ttl=60)
assert llm_cache.get('test_key') == 'test_value'

print('OK: Foundation 层测试通过')
"
```

## Core 层测试
```powershell
cd 2workbench ; python -c "
import tempfile, os
from foundation.database import init_db
from core.models import WorldRepo, PlayerRepo, NPCRepo, ItemRepo
from core.state import create_initial_state
from core.calculators import roll_dice

tmp = tempfile.mktemp(suffix='.db')
init_db(db_path=tmp)

# Repository
repo = WorldRepo()
w = repo.create(name='测试世界', db_path=tmp)
assert w.id > 0

# State
state = create_initial_state(world_id=1)
assert 'messages' in state

# Calculator
result = roll_dice('2d6')
assert 2 <= result <= 12

os.unlink(tmp)
print('OK: Core 层测试通过')
"
```

## Feature 层测试
```powershell
cd 2workbench ; python -c "
from feature.registry import feature_registry
from feature.battle import BattleSystem
from feature.dialogue import DialogueSystem
from feature.ai import GMAgent

feature_registry.register(BattleSystem())
feature_registry.register(DialogueSystem())
feature_registry.enable_all()

assert 'battle' in feature_registry.list_features()
print('OK: Feature 层测试通过')
"
```

## Presentation 层测试
```powershell
cd 2workbench ; python -c "
import sys
from PyQt6.QtWidgets import QApplication
app = QApplication(sys.argv)

from presentation.theme.manager import theme_manager
theme_manager.apply('dark')

from presentation.project.manager import ProjectManager
pm = ProjectManager()
print('OK: Presentation 层测试通过')
"
```
