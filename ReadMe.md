# EurekaLoader

EurekaLoader เป็นโปรแกรมที่ช่วยจัดการการวางกล่องในพื้นที่จำกัด เช่น คอนเทนเนอร์หรือพาเลท โดยใช้ข้อมูลจากไฟล์ CSV และแสดงผลการวางกล่องในรูปแบบ 3D พร้อมทั้งสามารถ Export ผลลัพธ์ออกมาเป็นไฟล์ CSV ได้

---

## คุณสมบัติ
1. **โหลดข้อมูลกล่องจากไฟล์ CSV**:
   - โปรแกรมสามารถโหลดข้อมูลกล่องจากไฟล์ `forimport.csv` ที่อยู่ในโฟลเดอร์ `D:/EurekaLoader/Input`
   - ตรวจสอบความถูกต้องของคอลัมน์ในไฟล์ CSV เช่น `Priority`, `BoxTypes`, `Width`, `Length`, `Height`, `Conveyor`, และ `QTY`

2. **จัดเรียงกล่องตาม Priority**:
   - กล่องจะถูกจัดเรียงตามลำดับ Priority ก่อนเริ่มกระบวนการจัดวาง

3. **แสดงผลการวางกล่องในรูปแบบ 3D**:
   - ใช้ Matplotlib ในการแสดงผลการวางกล่องในคอนเทนเนอร์
   - มีการแสดงกรอบของพาเลทและคอนเทนเนอร์ รวมถึงกล่องที่ถูกวาง

4. **Export ผลลัพธ์**:
   - บันทึกผลลัพธ์การวางกล่องที่สำเร็จในไฟล์ `PlacedBox.csv` (โฟลเดอร์ `D:/EurekaLoader/Placed`)
   - บันทึกกล่องที่ไม่สามารถวางได้ในไฟล์ `Free_Roller_Boxes.csv` (โฟลเดอร์ `D:/EurekaLoader/Exception_Place`)

5. **แสดงสรุปผลการวางกล่อง**:
   - แสดงจำนวนกล่องที่วางสำเร็จและไม่สำเร็จ
   - แสดงเปอร์เซ็นต์การใช้พื้นที่ในคอนเทนเนอร์ (Utilization)

6. **เปิดโฟลเดอร์ Explore**:
   - มีปุ่ม Explore สำหรับเปิดโฟลเดอร์ `D:/EurekaLoader` ใน File Explorer

7. **สร้างไฟล์ Executable**:
   - รองรับการสร้างไฟล์ `.exe` ด้วย PyInstaller ผ่านสคริปต์ `build.py`

---

## ความต้องการของระบบ
- **ระบบปฏิบัติการ**: Windows 10 หรือสูงกว่า
- **Python**: Python 3.10 หรือสูงกว่า
- **ไลบรารีที่จำเป็น**: ดูในไฟล์ `requirements.txt`

---

## การติดตั้ง

### 1. ติดตั้ง Python
ดาวน์โหลดและติดตั้ง Python จาก [python.org](https://www.python.org/downloads/)

### 2. ดาวน์โหลดไฟล์โปรเจกต์
จัดโครงสร้างไฟล์ดังนี้:
:/EurekaLoader/ ├── Input/ │ └── forimport.csv ├── Placed/ # สร้างอัตโนมัติเมื่อรันโปรแกรม ├── Exception_Place/ # สร้างอัตโนมัติเมื่อรันโปรแกรม ├── config.ini ├── MainEurekaLoader_Prototype.py ├── build.py ├── requirements.txt └── favicon.ico

### 3. ติดตั้งไลบรารีที่จำเป็น
เปิด Command Prompt และรันคำสั่ง:
```bash
pip install -r [requirements.txt](http://_vscodecontentref_/6)