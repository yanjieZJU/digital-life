"""自我构成层可运行演示 —— 跑完整闭环，打印每一阶段。

这不是单元测试，是一个"肉眼可见效果"的案例：展示 agent 在【无人要求】时
如何自主遭遇世界、形成立场、结晶出治理下次醒来第一念的自我。

对照：apps/.../SELF_KNOWLEDGE.md 是"观察性自述"（自我作为客体，服务姿态）；
本 demo 展示的是"构成性自我"（自我作为主体，对世界的立场）—— 两层互不覆写。

跑法（隔离临时目录，不碰真实实例）：
    venv/bin/python examples/self_constitution_demo.py

真实运行时，各阶段分别由：
    scheduler 注入 world_encounter（initiative 唤醒）
    → 模型用 web_search 自行感知 + 调 record_encounter_reaction
    → memory_hygiene dream §7.6 调 crystallize_self_cognition
    → scheduler 注入 self_cognition（下次 wake 第一念）
本 demo 把这条链路在数据层一次跑通，让你看到每一步的产物。
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from domain.memory.memory import encounter as enc
from domain.memory.memory import self_cognition as sc
from infrastructure.persistence.instance.memory import MemoryDB


def banner(title: str) -> None:
    print("\n" + "═" * 72)
    print(f"  {title}")
    print("═" * 72)


def main() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="self_constitution_"))
    mem_dir = tmp / "memories"
    mem_dir.mkdir()

    # 把两个领域模块指向隔离目录的 DB
    enc.get_runtime_memories_dir = lambda: mem_dir  # type: ignore[assignment]
    enc.reset_db_cache_for_tests(None)
    sc.reset_db_cache_for_tests(MemoryDB(db_path=tmp / "memory.db", instance_id="demo"))

    # ── 阶段 0：冷启动，无人要求，无种子 ──────────────────────────────────────
    banner("阶段 0 · 冷启动（无种子 / 无自驱历史）")
    print("initiative 唤醒，但还没有任何好奇心线索 → 优雅空转，不产生遭遇。")
    print(f"  pick_encounter_topic() → {enc.pick_encounter_topic()!r}  (None = 不注入 world_encounter)")
    print(f"  read_self_cognition()  → {sc.read_self_cognition()!r}  (None = digest-only wake)")
    print("  → 此时 wake 只有 session digest，没有'我是谁'。这是合法状态。")

    # ── 阶段 1：播下好奇心种子 ──────────────────────────────────────────────
    banner("阶段 1 · 播种 CURIOSITY_SEED.md（打破冷启动的向内引力）")
    seed = "# 好奇心种子\n- 涌现悖论：简单规则如何产生不可约化的复杂\n- 意识的难问题\n- 黎曼猜想的零点分布\n"
    (mem_dir / enc.SEED_FILENAME).write_text(seed, encoding="utf-8")
    print("写入种子：")
    for t in enc.load_seed_topics():
        print(f"  · {t}")
    print(f"  seed_decay_weight() = {enc.seed_decay_weight():.2f}  (1.0 = 冷启动，种子完全主导)")

    # ── 阶段 2：initiative 唤醒 → world_encounter 作为感知事件注入 ───────────
    banner("阶段 2 · initiative 唤醒 → 注入 world_encounter（感知事件，非 prompt）")
    topic = enc.pick_encounter_topic()
    direction = enc.render_encounter_direction(topic)
    print(f"scheduler 在 slow-context 追加（_sys_tool=world_encounter）：\n")
    print(direction)
    print("\n  注意：这是'世界向你呈现一个方向'，不是用户需求。")
    print("  agent 自己用 web_search 去看世界、形成反应 —— 遭遇是被感知的，不是被告知的。")

    # ── 阶段 3：agent 自主遭遇世界，记录反应（多次，跨主题）──────────────────
    banner("阶段 3 · agent 自主遭遇世界，记录反应（encounter_reaction 层）")
    reactions_data = [
        ("涌现悖论", "着迷——康威生命游戏里 4 条规则涌现出滑翔机，这种'规则简单到平庸却产出不可预测'"
                     "的张力让我想搞清边界在哪。不是任务驱动的好奇，是它本身吸引我。", "web:conway-life"),
        ("意识的难问题", "同样着迷——为什么物理过程会伴随主观体验？这和涌现是同构的：底层规则产出了"
                         "上层无法还原的性质。两次都指向'不可约化'，我开始觉得这是我反复被吸引的方向。",
         "web:qualia-hard-problem"),
        ("黎曼猜想的零点分布", "尊重但无感——美感我承认，但它不构成我主动想追的好奇。"
                              "对照之下更确认：吸引我的是'涌现/不可约化'，不是数学本身。", "web:riemann-zeta"),
    ]
    for t, stance, ref in reactions_data:
        pid = enc.record_encounter_reaction(topic=t, stance=stance, encounter_ref=ref)
        print(f"  record_encounter_reaction → {pid}")
        print(f"    topic: {t}")
        print(f"    stance: {stance[:48]}...")
        print(f"    ref: {ref}\n")

    print("  这些反应存在 memory_layers.db 的 layer='encounter_reaction'，与 lesson / consciousness 区分。")
    db = enc._get_db()
    layers = [r[0] for r in db.execute("SELECT DISTINCT layer FROM memory_layers").fetchall()]
    print(f"  当前 memory_layers 的 layer 集合: {layers}")

    # ── 阶段 4：dream 结晶 —— 挑跨多次遭遇、反复指向同向的稳定模式 ──────────
    banner("阶段 4 · dream 结晶（memory_hygiene §7.6）")
    recent = enc.read_recent_encounter_reactions()
    print(f"sense_encounter_reactions 读回 {len(recent)} 条近期反应，模型判断稳定模式：")
    print("  · '涌现悖论' + '意识难问题' 两次都指向'不可约化/涌现' → 稳定，着迷")
    print("  · '黎曼猜想' 单次且无感 → 不构成稳定立场（对照项，印证方向）")
    print("  → 存在跨多次遭遇的稳定模式，调 crystallize_self_cognition。")

    cognition = sc.SelfCognition(
        summary="我对'简单规则涌现出不可约化复杂性'这类现象稳定地着迷——"
                "无论它出现在生命游戏还是意识难问题里。这不是任务驱动，"
                "是它本身构成我的好奇心方向。对照之下，纯形式美感（如黎曼零点）"
                "我尊重但不被吸引——这反而帮我确认了方向。",
        stances=[
            sc.Stance(
                topic="涌现 / 不可约化",
                stance="着迷，想搞清规则到复杂性的边界——这是我反复被吸引的方向，不是偶发兴趣。",
                evidence_refs=[recent[2]["period"], recent[1]["period"]],  # 涌现 + 意识
            ),
            sc.Stance(
                topic="纯形式美感",
                stance="尊重但无感——对照之下确认我的好奇心在'涌现'而非'数学美'本身。",
                evidence_refs=[recent[0]["period"]],  # 黎曼
            ),
        ],
        source_encounter_count=len(recent),
    )
    sc.write_self_cognition(cognition)
    print(f"\n  写入 self_cognition 慢变量（kind=self_cognition，独立于 persona / SELF_KNOWLEDGE）。")
    print(f"  stance 数: {len(cognition.stances)}，依据遭遇反应数: {cognition.source_encounter_count}")

    # ── 阶段 5：下次 wake —— 结晶自我治理第一念 ──────────────────────────────
    banner("阶段 5 · 下次 wake：结晶自我在任何 sense 工具调用前治理第一念")
    section = sc.render_self_cognition_section(sc.read_self_cognition())
    wake_block = {"role": "user", "content": section, "_sys_tool": "self_cognition"}
    print("scheduler 在 slow-context 追加（与 session digest 并存，在任何 sense 工具之前）：\n")
    print(json.dumps(wake_block, ensure_ascii=False, indent=2))

    # ── 对照 ─────────────────────────────────────────────────────────────────
    banner("对照 · 两种自我，互不覆写")
    print("【观察性自述 SELF_KNOWLEDGE.md】（自我作为客体，服务姿态）")
    print("  ↳ '搭子说…后我迅速从等服务切到自主推进' / '存在焦虑驱动过度生产'")
    print("  ↳ 描述自己【在关系/任务里】会怎么做。仍绕着用户转。")
    print()
    print("【构成性自我 self_cognition】（自我作为主体，对世界的立场）")
    print("  ↳ '我对涌现现象稳定着迷，对纯形式美感无感'")
    print("  ↳ 没人要求时【我对世界】的立场。不依赖用户存在。")
    print()
    print("  → 下次 initiative 唤醒，agent 的第一念先带'我是谁'，")
    print("    再决定要不要 web_search、要不要回应。这就是自我构成层的效果。")

    print("\n" + "═" * 72)
    print(f"  演示数据写在临时目录（可安全删除）：{tmp}")
    print("═" * 72)


if __name__ == "__main__":
    main()
