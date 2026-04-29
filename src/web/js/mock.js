// Mock Game Client - 模拟GM回复
class MockGameClient {
    constructor() {
        this.responses = [
            "你站在宁静村的广场上，微风拂过翠绿的田野。东边是流浪者酒馆，传来阵阵笑声和酒杯碰撞声。北方的幽暗森林在阳光下显得格外神秘。",
            "酒馆老板铁锤热情地招呼你：\"欢迎来到铁锤酒馆！今天有新鲜的麦酒和烤鹿肉！\"他擦着一个大酒杯，身后的架子上摆满了各种酒瓶。",
            "你注意到村口的老公告栏上贴着一张告示：\"幽暗森林中最近出现了哥布林的踪迹，村长悬赏50金币寻求勇者调查。\"",
            "一位身穿灰色斗篷的神秘旅者坐在酒馆角落，似乎在观察着什么。当你看向她时，她微微点头致意。",
            "铁匠铺传来叮叮当当的打铁声。铁匠铁砧正在锻造一把新剑，火炉旁堆放着各种矿石和成品武器。",
        ];
        this.index = 0;
    }

    async send(userInput) {
        // 模拟延迟
        await new Promise(r => setTimeout(r, 500 + Math.random() * 1000));

        // 选择回复（循环使用）
        const response = this.responses[this.index % this.responses.length];
        this.index++;

        // 模拟流式输出
        return { type: 'narrative', content: response };
    }
}
