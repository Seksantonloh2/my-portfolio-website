# Web Design Agent 🎨

AI Agent สำหรับออกแบบเว็บไซต์ไว้ขายงานลูกค้า คุณแค่ส่งลิงก์อ้างอิงให้ (เว็บที่ชอบ บทความสอนทำ animation หรือแกลเลอรีอย่าง Awwwards)
แล้ว Agent จะ:

1. **อ่านทุกลิงก์อย่างละเอียด** เปิดด้วยเบราว์เซอร์จริง เลื่อนจนสุดหน้า (animation ที่ทำงานตอน scroll และรูปที่โหลดทีหลังจะได้แสดงครบ) ถ่ายภาพหน้าจอ อ่านข้อความทั้งหมด
   และวัดค่าดีไซน์จริงจากหน้าเว็บ เช่น สี ฟอนต์ ไลบรารี animation (GSAP, Lenis, Three.js, Lottie ฯลฯ), `@keyframes`, transition และ hover effect
2. **ตามลิงก์ต่อไปยังเว็บอื่น** Claude จะเลือกเองว่าลิงก์ไหนในหน้านั้นน่าอ่านต่อ (เช่น case study, tutorial หรือเว็บที่ถูกยกเป็นตัวอย่าง) แล้วตามไปอ่านเป็นทอด ๆ ตาม `--depth`
3. **สรุปความรู้** เป็น `research.md` ว่าแต่ละเว็บใช้ดีไซน์ animation และ interaction อะไร และแต่ละอย่างทำยังไง
4. **ออกแบบเว็บใหม่** สร้าง `design.md` (เอกสาร design ไว้ present ลูกค้า) และ `index.html` (เว็บที่ใช้งานได้จริง มี animation และรองรับมือถือ)
5. **ตรวจงานตัวเอง** เปิดเว็บที่สร้างขึ้นบน desktop และมือถือ ดูภาพหน้าจอ เช็ก JavaScript error และ layout ที่ล้นจอ แล้วแก้ให้

```
ลิงก์ของคุณ ─► [อ่าน + ถ่ายภาพ + วัดค่าดีไซน์] ─► [Claude วิเคราะห์ + เลือกลิงก์ต่อ] ─┐
                         ▲                                                     │
                         └─────────────── ลิงก์ที่ควรอ่านต่อ (ตาม --depth) ─────────┘
                                         ▼
             research.md ─► [Claude ออกแบบ] ─► design.md + index.html ─► [render → ตรวจ → แก้]
```

## ติดตั้ง (ทำครั้งเดียว)

ต้องมี Python 3.10 ขึ้นไป และ API key จาก <https://platform.claude.com/>

```bash
cd web-design-agent
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
export ANTHROPIC_API_KEY="sk-ant-..."                # Windows: set ANTHROPIC_API_KEY=sk-ant-...
```

## วิธีใช้

**แบบง่าย:** เขียน brief สั้น ๆ แล้วตามด้วยลิงก์

```bash
python design_agent.py --brief "Landing page ร้านกาแฟ specialty ที่เชียงใหม่ โทนอบอุ่น มินิมอล" \
  https://www.awwwards.com/websites/ https://tympanus.net/codrops/
```

**แบบเต็ม:** ใช้ไฟล์ brief และไฟล์ลิงก์ (ดูตัวอย่างได้ใน `brief.example.txt` และ `urls.example.txt`)

```bash
python design_agent.py --brief-file brief.example.txt --urls-file urls.example.txt --depth 2 --max-pages 20
```

**ปรับดีไซน์ใหม่โดยไม่ต้องอ่านลิงก์ซ้ำ:** ใช้ผลค้นคว้าเดิม แล้วแก้แค่ brief

```bash
python design_agent.py --brief "เวอร์ชันโทนสีเข้ม หรูหรากว่าเดิม" --research projects/<โฟลเดอร์เดิม>/research.json
```

## ผลลัพธ์ (อยู่ใน `projects/<วันเวลา>-<ชื่อ brief>/`)

| ไฟล์ | คืออะไร |
|---|---|
| `index.html` | เว็บไซต์ใหม่ เปิดในเบราว์เซอร์ได้ทันที |
| `design.md` | เอกสาร design: concept, สี, ฟอนต์, layout, motion spec และเว็บอ้างอิง (ใช้ present ลูกค้า) |
| `research.md` | สรุปสิ่งที่เรียนรู้จากทุกหน้า: animation และวิธีทำ, interaction, UX |
| `research.json` | ข้อมูลดิบของผลค้นคว้า (ใช้กับ `--research`) |
| `screenshots/` | ภาพหน้าจอของทุกหน้าที่อ่าน |
| `index.v1.html` | เวอร์ชันก่อนรอบตรวจแก้ (เก็บไว้เทียบ) |

## ตัวเลือก

| ตัวเลือก | ค่าเริ่มต้น | ความหมาย |
|---|---|---|
| `--depth` | `1` | จำนวนทอดที่ตามลิงก์ต่อ (`0` = อ่านแค่ลิงก์ที่ให้ไป) |
| `--max-pages` | `12` | จำนวนหน้าสูงสุดที่จะอ่าน (ใช้คุมค่าใช้จ่าย) |
| `--max-links-per-page` | `4` | จำนวนลิงก์ที่ตามต่อได้จากแต่ละหน้า |
| `--review-rounds` | `1` | จำนวนรอบตรวจแก้เว็บ (`0` = ไม่ตรวจ) |
| `--out` | อัตโนมัติ | โฟลเดอร์สำหรับเก็บผลลัพธ์ |

Environment variables:

| ตัวแปร | ค่าเริ่มต้น | ความหมาย |
|---|---|---|
| `ANALYST_MODEL` | `claude-opus-5-5` | โมเดลที่ใช้วิเคราะห์แต่ละหน้า (อยากประหยัดให้ใช้ `claude-sonnet-5-5` หรือ `claude-haiku-5-5`) |
| `DESIGNER_MODEL` | `claude-opus-5-5` | โมเดลที่ใช้ออกแบบและตรวจงาน |
| `ANALYST_EFFORT` / `DESIGNER_EFFORT` | `medium` / `high` | ความลึกในการคิด (`low` ถึง `max`) |
| `PARALLEL_ANALYSTS` | `4` | จำนวนหน้าที่วิเคราะห์พร้อมกัน |
| `CHROMIUM_PATH` | – | ระบุตำแหน่ง Chromium เอง (ไม่ต้องตั้งถ้ารัน `playwright install chromium` แล้ว) |

## เคล็ดลับ

- **brief ยิ่งละเอียด งานยิ่งตรงใจลูกค้า** ควรระบุธุรกิจ กลุ่มเป้าหมาย เป้าหมายของเว็บ อารมณ์และโทน ส่วนที่ต้องมี และภาษา
- **ผสมลิงก์หลายประเภท** เช่น เว็บที่ชอบ 2–3 เว็บ บทความหรือ tutorial เรื่อง animation และเว็บของคู่แข่งลูกค้า
- เว็บที่ต้อง login หรือมีระบบกันบอทอาจอ่านไม่ได้ ถ้าเจอแบบนี้ Agent จะข้ามไปและจดไว้ใน `research.md`
- Agent ถูกสั่งให้ **ใช้เว็บอ้างอิงเป็นแรงบันดาลใจเท่านั้น** ไม่คัดลอกข้อความ โลโก้ หรือรูปภาพ ส่วนรูปในเว็บใหม่จะเป็นกรอบ placeholder ให้คุณใส่รูปจริงของลูกค้าเอง
- ค่าใช้จ่ายขึ้นกับจำนวนหน้าที่อ่าน (แต่ละหน้าส่งภาพหน้าจอไปให้ Claude วิเคราะห์) ลองเริ่มจาก `--max-pages 5` ก่อน
