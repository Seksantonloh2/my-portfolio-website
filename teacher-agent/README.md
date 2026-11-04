# Teacher Agent 🧑‍🏫

AI "ครู" ที่สั่งงาน AI "นักเรียน" ให้ไปค้นคว้าข้อมูลอ้างอิงจากอินเทอร์เน็ต ตรวจงาน และส่งกลับไปแก้จนกว่าจะผ่าน
แล้วสรุปเป็นรายงานฉบับเดียวพร้อมแหล่งอ้างอิง

```
คุณ ─► ครู ──assign_lesson(บทเรียน + เกณฑ์ผ่าน + feedback)──► นักเรียน ─► web_search / web_fetch
        ▲                                                        │
        └──────────── รายงาน + แหล่งอ้างอิง ◄───────────────────┘
      ตรวจตามเกณฑ์ → ผ่าน / ส่งกลับไปแก้ (สูงสุด 2 รอบต่อบท) → เขียนรายงานสุดท้าย
```

- ครูแตกหัวข้อเป็นบทเรียนย่อย 2–5 บท
- นักเรียนหลายตัวทำงาน **พร้อมกัน** และแต่ละตัวมี context แยกกัน (หน้าเว็บที่อ่านจะไม่ทำให้ context ของครูเต็ม)
- รายงานจะถูกบันทึกเป็นไฟล์ Markdown ในโฟลเดอร์ `reports/`

## วิธีใช้ (3 ขั้นตอน)

1. ติดตั้ง Python 3.10 ขึ้นไป และสร้าง API key ที่ <https://platform.claude.com/>
   (ต้องเปิดใช้ web search ใน Console ด้วย)
2. ติดตั้งแพ็กเกจ:

```bash
cd teacher-agent
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY="sk-ant-..."                # Windows: set ANTHROPIC_API_KEY=sk-ant-...
```

3. รัน:

```bash
python teacher_agent.py "เปรียบเทียบเทคนิค RAG แบบต่าง ๆ ในปี 2026"
```

## ปรับแต่งด้วย environment variables

| ตัวแปร | ค่าเริ่มต้น | ความหมาย |
|---|---|---|
| `TEACHER_MODEL` | `claude-opus-5-5` | โมเดลของครู |
| `STUDENT_MODEL` | `claude-opus-5-5` | โมเดลของนักเรียน (อยากประหยัดให้ใช้ `claude-sonnet-5-5` หรือ `claude-haiku-5-5`) |
| `TEACHER_EFFORT` / `STUDENT_EFFORT` | `high` / `medium` | ความลึกในการคิด: `low`, `medium`, `high`, `xhigh`, `max` |
| `MAX_ASSIGNMENTS` | `12` | จำนวนครั้งที่ครูสั่งงานได้ทั้งหมด (รวมรอบแก้) ใช้คุมค่าใช้จ่าย |
| `MAX_SEARCHES_PER_LESSON` | `6` | จำนวนครั้งที่นักเรียนค้นหาหรือเปิดเว็บได้ต่อบทเรียน |
| `MAX_PARALLEL_STUDENTS` | `4` | จำนวนนักเรียนที่ทำงานพร้อมกัน |
| `OUTPUT_DIR` | `reports` | โฟลเดอร์สำหรับบันทึกรายงาน |

ตัวอย่างแบบประหยัด:

```bash
STUDENT_MODEL=claude-haiku-5-5 MAX_ASSIGNMENTS=6 python teacher_agent.py "ประวัติของ Transformer"
```

## เรียกใช้จากโค้ด Python อื่น

```python
from teacher_agent import run_teacher

report = run_teacher("แนวโน้มพลังงานแสงอาทิตย์ในไทย")
print(report)
```

## ปรับพฤติกรรม

- เปลี่ยนวิธีสอนหรือวิธีตรวจของครู: แก้ `TEACHER_SYSTEM`
- เปลี่ยนวิธีค้นคว้าหรือรูปแบบรายงานของนักเรียน: แก้ `STUDENT_SYSTEM`
- ให้ค้นเฉพาะเว็บที่เชื่อถือได้: เพิ่ม `"allowed_domains": ["wikipedia.org", "arxiv.org"]` ใน `WEB_TOOLS`

## หมายเหตุ

- มีค่าใช้จ่ายตามการใช้ API (token และจำนวนครั้งที่ค้นเว็บ) ลองเริ่มจากหัวข้อเล็ก ๆ ก่อน
- ถ้าโมเดลปฏิเสธคำขอ ระบบจะสลับไปใช้โมเดลสำรองให้อัตโนมัติ (server-side fallback)
