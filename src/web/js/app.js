// MUD 前端主逻辑 - P4' 真实 WebSocket 连接
const narrativeContent = document.getElementById('narrative-content');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');

// ===== 真实 WebSocket 连接 =====
let ws = null;
let worldId = 1;

class RealGameClient {
    constructor(worldId) {
        this.worldId = worldId;
        this.ws = null;
        this.reconnectTimer = null;
    }

    connect() {
        const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
        const url = `${protocol}//${location.host}/ws/worlds/${this.worldId}`;
        this.ws = new WebSocket(url);

        this.ws.onopen = () => {
            addMessage('已连接到游戏服务器', 'system-text');
        };

        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'narrative') {
                appendToLastGMMessage(data.content);
            } else if (data.type === 'system') {
                addMessage(data.content, 'system-text');
            } else if (data.type === 'combat') {
                handleCombatUpdate(data.data);
            } else if (data.type === 'choice') {
                showChoices(data.choices);
            }
        };

        this.ws.onclose = () => {
            addMessage('连接断开，5秒后重连...', 'system-text');
            this.reconnectTimer = setTimeout(() => this.connect(), 5000);
        };

        this.ws.onerror = () => {
            addMessage('连接错误', 'system-text');
        };
    }

    send(userInput) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ type: 'action', content: userInput }));
        } else {
            addMessage('未连接到服务器', 'system-text');
        }
    }

    disconnect() {
        if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
        if (this.ws) this.ws.close();
    }
}

// 替换 Mock 客户端
const client = new RealGameClient(worldId);
client.connect();

// 添加消息到叙事区
function addMessage(text, className) {
    const div = document.createElement('div');
    div.className = `message ${className}`;
    div.textContent = text;
    narrativeContent.appendChild(div);
    narrativeContent.scrollTop = narrativeContent.scrollHeight;
}

// 修改 appendToLastGMMessage 函数
function appendToLastGMMessage(char) {
    let container = document.querySelector('#narrative-content .gm-text:last-child');
    if (!container || !container.dataset.streaming) {
        container = document.createElement('div');
        container.className = 'message gm-text';
        container.dataset.streaming = 'true';
        narrativeContent.appendChild(container);
    }
    container.textContent += char;
    narrativeContent.scrollTop = narrativeContent.scrollHeight;

    // 流结束后标记完成
    clearTimeout(container._endTimer);
    container._endTimer = setTimeout(() => {
        delete container.dataset.streaming;
    }, 2000);
}

// 发送消息
async function sendMessage() {
    const text = userInput.value.trim();
    if (!text) return;
    addMessage(`你> ${text}`, 'user-text');
    userInput.value = '';
    client.send(text);
}

// 事件绑定
sendBtn.addEventListener('click', sendMessage);
userInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') sendMessage();
});

// Tab切换
document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
        tab.classList.add('active');
        document.getElementById(`tab-${tab.dataset.tab}`).classList.add('active');
    });
});

// ===== NPC 面板功能 =====
const npcsTab = document.getElementById('tab-npcs');

async function loadNPCs(locationId) {
    // TODO: P4' 替换为 WebSocket 调用
    // 当前使用 Mock 数据
    const mockNPCs = [
        { id: 1, name: "村长", mood: "neutral" },
        { id: 2, name: "铁匠", mood: "happy" },
        { id: 3, name: "神秘旅者", mood: "contemplative" },
    ];
    npcsTab.innerHTML = mockNPCs.map(npc =>
        `<div class="npc-item" onclick="talkToNPC(${npc.id}, '${npc.name}')">
            <span class="npc-name">${npc.name}</span>
            <span class="npc-mood">${npc.mood}</span>
        </div>`
    ).join('');
}

function talkToNPC(npcId, npcName) {
    userInput.placeholder = `对 ${npcName} 说...`;
    userInput.dataset.npcId = npcId;
    userInput.dataset.npcName = npcName;
    userInput.focus();
}

// 初始化时加载NPC
loadNPCs(1);

// ===== 任务面板功能 =====
const questsTab = document.getElementById('tab-quests');

async function loadQuests() {
    // TODO: P4' 替换为 WebSocket 调用
    const mockQuests = [
        { id: 1, title: "哥布林的威胁", status: "active", progress: "50%" },
        { id: 2, title: "铁匠的请求", status: "completed", progress: "100%" },
    ];
    questsTab.innerHTML = mockQuests.map(q =>
        `<div class="quest-item ${q.status}">
            <span class="quest-title">${q.title}</span>
            <span class="quest-progress">${q.progress}</span>
        </div>`
    ).join('');
}

// 初始化时加载任务
loadQuests();

// ===== 战斗界面功能 =====
function handleCombatUpdate(data) {
    const panel = document.getElementById('combat-panel');
    panel.style.display = 'block';

    // 更新战斗参与者
    const combatants = document.getElementById('combatants');
    combatants.innerHTML = data.participants.map(p => {
        const hpPercent = Math.max(0, (p.hp / p.max_hp) * 100);
        const hpClass = hpPercent < 25 ? 'low' : hpPercent < 50 ? 'medium' : '';
        return `<div class="combatant">
            <span class="combatant-name">${p.is_player ? '🧙' : '👹'} ${p.name}</span>
            <div style="display:flex;align-items:center;">
                <div class="hp-bar-container">
                    <div class="hp-bar ${hpClass}" style="width:${hpPercent}%"></div>
                </div>
                <span class="hp-text">${p.hp}/${p.max_hp}</span>
            </div>
        </div>`;
    }).join('');

    // 更新战斗日志
    if (data.log) {
        const logEl = document.getElementById('combat-log');
        logEl.innerHTML += data.log.map(l => `<div>${l}</div>`).join('');
        logEl.scrollTop = logEl.scrollHeight;
    }

    // 战斗结束
    if (data.finished) {
        document.getElementById('combat-actions').style.display = 'none';
        if (data.victory) {
            addMessage(`🎉 胜利！获得 ${data.rewards.exp} 经验和 ${data.rewards.gold} 金币。`, 'system-text');
        } else {
            addMessage('💀 你被击败了...', 'combat-text');
        }
        setTimeout(() => {
            panel.style.display = 'none';
            document.getElementById('combat-actions').style.display = 'flex';
        }, 3000);
    }
}

function combatAction(action) {
    client.send(JSON.stringify({ type: 'combat_action', action: action }));
}

// ===== 分支选择 UI =====
function showChoices(choices) {
    const panel = document.getElementById('choice-panel');
    const options = document.getElementById('choice-options');
    panel.style.display = 'block';
    options.innerHTML = choices.map((c, i) =>
        `<button class="choice-btn" onclick="selectChoice('${c.id}')">${c.text}</button>`
    ).join('');
    userInput.disabled = true;
}

function selectChoice(choiceId) {
    client.send(JSON.stringify({ type: 'choice', choice_id: choiceId }));
    document.getElementById('choice-panel').style.display = 'none';
    userInput.disabled = false;
    addMessage(`你做出了选择。`, 'system-text');
}
