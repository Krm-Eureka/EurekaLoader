import configparser
import os
from typing import List, Tuple
from Models.Box import Box
from Models.Container import Container
from Service.shared_state import last_success_positions

config = configparser.ConfigParser()
config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.ini")
config.read(config_path, encoding="utf-8")
prefer_rotation_first = config.getboolean("PlaceMent", "PREFER_ROTATION_FIRST", fallback=True)
min_support_ratio = float(config.get("Container", "required_support_ratio", fallback="0.8"))

def has_vertical_clearance(box: Box, placed_boxes: List[Box], container_height: int) -> bool:
    """
    ตรวจสอบว่า:
    - ด้านบนของกล่องมีพื้นที่ว่าง 100%.
    - ด้านล่างของกล่องมีพื้นที่รองรับอย่างน้อย 75%.
    """
    # ตรวจสอบพื้นที่ด้านบน
    box_top = box.z + box.height
    for other in placed_boxes:
        if (
            other.z >= box_top and  # กล่องอื่นอยู่ด้านบน
            not (
                box.x + box.length <= other.x or
                box.x >= other.x + other.length or
                box.y + box.width <= other.y or
                box.y >= other.y + other.width
            )
        ):
            return False  # มีการบังด้านบน

    # ตรวจสอบพื้นที่ด้านล่าง
    if not box.is_supported(placed_boxes, container_height):
        return False  # พื้นที่ด้านล่างไม่เพียงพอ

    return True

def place_box_in_container(container: Container, box: Box, optional_check: str = "op2"):
    
    def calculate_support_ratio(box: Box, placed_boxes: List[Box], pallet_height: int) -> float:
        if box.z <= pallet_height:
            return 1.0
        support_area = 0
        total_area = box.length * box.width
        for b in placed_boxes:
            if abs(b.z + b.height - box.z) < 1e-6:
                overlap_x = max(0, min(box.x + box.length, b.x + b.length) - max(box.x, b.x))
                overlap_y = max(0, min(box.y + box.width, b.y + b.width) - max(box.y, b.y))
                support_area += overlap_x * overlap_y
        return support_area / total_area if total_area > 0 else 0.0

    candidate_positions = sorted(
        container.generate_candidate_positions(),
        key=lambda pos: pos[2]  # เรียงจาก Z ต่ำสุดขึ้นไป
    )
    print(len(candidate_positions))
    best_position = None
    best_support = -1
    best_rotation = False
    exceeds_container_height = False

    for x, y, z in candidate_positions:
        for rotation in [False, True]:
            # จำขนาดเดิมไว้ก่อน rotation
            original_length, original_width = box.length, box.width
            if rotation:
                box.length, box.width = original_width, original_length

            # ทดสอบตำแหน่งชั่วคราว
            old_pos = (box.x, box.y, box.z)
            box.set_position(x, y, z)
            can_place, reason = container.can_place(box, x, y, z, optional_check)
            
            print(f"Can place: {can_place}, reason: {reason}")
            if not can_place:
                box.set_position(*old_pos)
                box.length, box.width = original_length, original_width
                continue

            support_ratio = calculate_support_ratio(box, container.boxes, container.pallet_height)
            clearance_ok = has_vertical_clearance(box, container.boxes, container.height)
            
            if support_ratio >= min_support_ratio and clearance_ok:
                if best_position is None or (support_ratio >= best_support and z < best_position[2]):
                    best_position = (x, y, z)
                    best_support = support_ratio
                    best_rotation = rotation
                box.length, box.width = original_length, original_width  # รีเซตหลังเทียบเสร็จ
                print(f"Trying pos=({x},{y},{z}) rot={rotation} | support={support_ratio:.2f} | clearance={clearance_ok}")
                if support_ratio >= min_support_ratio and clearance_ok:
                    print(f"✅ Accepting this candidate (better or first)")
    if best_position:
        x, y, z = best_position
        if best_rotation:
            box.length, box.width = box.width, box.length
        box.set_position(x, y, z)
        exceeds = box.z + box.height > container.end_z  # ตรวจสอบว่าล้นความสูงหรือไม่
        container.place_box(box)  # วางกล่องใน container
        height_note = " (⚠ exceeds container height)" if exceeds else ""
        print(f"Chosen position: {best_position} | R: {best_rotation} | exceeds: {exceeds}")
        if not exceeds:
            return {
                "status": "Confirmed",
                "rotation": 0 if best_rotation else 1,  # 0 = หมุน, 1 = ไม่หมุน
                "support": best_support,
                "exceeds_end_z": False,
                "message": f"Support: {best_support:.2f}" ,
            }
        # วางสำเร็จ แต่สูงเกิน container → ใน op1 ถือว่าวางได้แต่ส่ง failed (จะใช้ในขั้นตอนต่อไป)
        if optional_check == "op1":
            return {
                "status": "OutOfContainer",
                "rotation": 0 if best_rotation else 1,  # 0 = หมุน, 1 = ไม่หมุน
                "support": best_support,
                "exceeds_end_z": True,
                "message": f"Support: {best_support:.2f}" + height_note,
            }
            
        # ✳️ ถ้า op2 และล้นความสูง → ไม่วาง
        if optional_check == "op2" and exceeds:
            return {
                "status": "Failed",
                "rotation": -1,
                "support": best_support,
                "exceeds_end_z": True,
                "message": "Box exceeds container height"
            }

        
    # ถ้าไม่มีตำแหน่งวางเลยเลย
    if optional_check == "op1":
        return {
            "status": "Failed",
            "rotation": -1,  # หมุนไม่หมุนก็ไม่เจอที่วาง
            "support": 0.0,
            "exceeds_end_z": False,
            "message": "No suitable position found"
        }
    else:
        return {
            "status": "Failed",
            "rotation": -1,  # สำหรับ non-op1 → ไม่พบตำแหน่ง
            "support": 0.0,
            "exceeds_end_z": False,
            "message": "No suitable position found"
        }

def place_box_human_like(container: Container, box: Box, optional_check: str = "op2"):
    def calculate_support_ratio(box: Box) -> float:
        support_area = 0
        total_area = box.length * box.width
        if box.z <= container.pallet_height:
            return 1.0
        for b in container.boxes:
            if abs(b.z + b.height - box.z) < 1e-6:
                overlap_x = max(0, min(box.x + box.length, b.x + b.length) - max(box.x, b.x))
                overlap_y = max(0, min(box.y + box.width, b.y + b.width) - max(box.y, b.y))
                support_area += overlap_x * overlap_y
        return support_area / total_area if total_area > 0 else 0.0

    def prioritize_nearby_positions(placed: Box) -> List[Tuple[int, int]]:
        candidates = set()
        for dx in [0, placed.length]:
            for dy in [0, placed.width]:
                x, y = placed.x + dx, placed.y + dy
                candidates.add((x, y))
        return sorted(list(candidates), key=lambda pos: (pos[1], pos[0]))  # 🔄 sort by y, then x

    max_z = container.end_z if optional_check == "op2" else container.total_height
    tried_positions = set()

    # 🔰 Try first box at corner
    if not container.boxes:
        for rotation in [False, True]:
            original_length, original_width = box.length, box.width
            if rotation:
                box.length, box.width = original_width, original_length

            x = int(container.start_x)
            y = int(container.start_y)
            box.set_position(x, y, container.pallet_height)

            can_place, reason = container.can_place(box, x, y, container.pallet_height, optional_check)
            if can_place and has_vertical_clearance(box, container.boxes, container.height):
                container.place_box(box)
                support = calculate_support_ratio(box)
                last_success_positions.append((x, y, container.pallet_height, rotation))
                print(f"[HumanLike ✅] Placed FIRST {box.sku} at ({x},{y},{container.pallet_height}) R={rotation}")
                return {
                    "status": "Confirmed",
                    "rotation": 0 if rotation else 1,
                    "support": support,
                    "exceeds_end_z": False,
                    "message": f"Human-like first placed with support {support:.2f}"
                }
            box.length, box.width = original_length, original_width

    z_levels = sorted(set(b.z + b.height for b in container.boxes))
    z_levels.insert(0, container.pallet_height)

    for z in z_levels:
        if z + box.height > max_z:
            continue
        for placed in sorted(container.boxes, key=lambda b: (b.y, b.x)):
            for x, y in prioritize_nearby_positions(placed):
                for rotation in [True, False]:
                    if (x, y, z, rotation) in tried_positions:
                        continue
                    tried_positions.add((x, y, z, rotation))

                    original_length, original_width = box.length, box.width
                    if rotation:
                        box.length, box.width = original_width, original_length
                    box.set_position(x, y, z)

                    can_place, reason = container.can_place(box, x, y, z, optional_check)
                    if not can_place:
                        box.length, box.width = original_length, original_width
                        continue

                    support = calculate_support_ratio(box)
                    if support >= min_support_ratio and has_vertical_clearance(box, container.boxes, container.height):
                        container.place_box(box)
                        last_success_positions.append((x, y, z, rotation))
                        print(f"[HumanLike ✅] Placed {box.sku} at ({x},{y},{z}) R={rotation}")
                        return {
                            "status": "Confirmed",
                            "rotation": 0 if rotation else 1,
                            "support": support,
                            "exceeds_end_z": False,
                            "message": f"Human-like placed with support {support:.2f}"
                        }
                    box.length, box.width = original_length, original_width

    print(f"[HumanLike ❌] No position found for {box.sku}")
    return {
        "status": "Failed",
        "rotation": -1,
        "support": 0.0,
        "exceeds_end_z": False,
        "message": "Human-like placement failed"
    }
    
def place_box_hybrid(container: Container, box: Box, optional_check: str = "op2"):
    def calculate_support_ratio(box: Box) -> float:
        if box.z <= container.pallet_height:
            return 1.0
        support_area = 0
        total_area = box.length * box.width
        for b in container.boxes:
            if abs(b.z + b.height - box.z) < 1e-6:
                overlap_x = max(0, min(box.x + box.length, b.x + b.length) - max(box.x, b.x))
                overlap_y = max(0, min(box.y + box.width, b.y + b.width) - max(box.y, b.y))
                support_area += overlap_x * overlap_y
        return support_area / total_area if total_area > 0 else 0.0

    def has_vertical_clearance(box: Box, placed_boxes: List[Box], container_height: int) -> bool:
        box_top = box.z + box.height
        for other in placed_boxes:
            if (
                other.z >= box_top and
                not (
                    box.x + box.length <= other.x or
                    box.x >= other.x + other.length or
                    box.y + box.width <= other.y or
                    box.y >= other.y + other.width
                )
            ):
                return False
        if not box.is_supported(placed_boxes, container.pallet_height):
            return False
        return True

    tried_positions = set()
    valid_placements = []

    all_positions = container.generate_candidate_positions()
    for b in container.boxes:
        for dx in [-box.length, b.length]:
            for dy in [-box.width, b.width]:
                all_positions.append((int(b.x + dx), int(b.y + dy), int(b.z)))

    candidate_positions = sorted(set(all_positions), key=lambda pos: (pos[2], pos[1], pos[0]))

    for x, y, z in candidate_positions:
        rotation_order = [True, False] if prefer_rotation_first else [False, True]
        for rotation in rotation_order:
            key = (x, y, z, rotation)
            if key in tried_positions:
                continue
            tried_positions.add(key)

            original_length, original_width = box.length, box.width
            if rotation:
                box.length, box.width = box.width, box.length

            if (
                x < container.start_x or
                y < container.start_y or
                z < container.pallet_height or
                x + box.length > container.end_x or
                y + box.width > container.end_y or
                z + box.height > container.end_z
            ):
                box.length, box.width = original_length, original_width
                continue

            box.set_position(x, y, z)
            can_place, reason = container.can_place(box, x, y, z, optional_check)
            if not can_place:
                box.length, box.width = original_length, original_width
                continue

            support_ratio = calculate_support_ratio(box)
            clearance_ok = has_vertical_clearance(box, container.boxes, container.height)
            if not clearance_ok or support_ratio < min_support_ratio:
                box.length, box.width = original_length, original_width
                continue
            
            rotation_sort_value = 0 if rotation else 1 
            if prefer_rotation_first:
                rotation_sort_value = 1 - rotation_sort_value  
                
            valid_placements.append((z, -support_ratio, rotation_sort_value, x, y, rotation))
            box.length, box.width = original_length, original_width

    if valid_placements:
        valid_placements.sort()
        z, neg_support, not_rot, x, y, rotation = valid_placements[0]
        support_ratio = -neg_support
        if rotation:
            box.length, box.width = box.width, box.length
        box.set_position(x, y, z)
        container.place_box(box)
        last_success_positions.append((x, y, z, rotation))
        print(f"[Hybrid ✅] Placed {box.sku} at ({x},{y},{z}) R={rotation}")
        return {
            "status": "Confirmed",
            "rotation": 0 if rotation else 1,
            "support": support_ratio,
            "exceeds_end_z": False,
            "message": f"Placed at Z={z} with support {support_ratio:.2f}"
        }

    print(f"[Hybrid ❌] No valid position found for {box.sku}")
    return {
        "status": "Failed",
        "rotation": -1,
        "support": 0.0,
        "exceeds_end_z": False,
        "message": "No suitable position found"
    }
    
def place_box_hybrid2(container: Container, box: Box, optional_check: str = "op2"):
    """
    Hybrid2 (Z,Y,X-first + roof-first + support-only stability + iterative SNAP):
      • คัดผู้สมัครเรียง (Z, Y, X)
      • หนีเงาหลังคาก่อน (ลง→ขวา→ขึ้น→ซ้าย) ให้เพดานโล่ง 100%
      • ความนิ่งใช้ 'support ratio + COM margin + Edge margin' (ไม่บังคับจำนวนพ่อรองรับ)
      • SNAP อัดชิด: ขึ้น(Y−) → ซ้าย(X−) + edge-glide โดยคง support ≥ floor
      • เลือกผู้ชนะ: (Z, -stability_score, Y, X, rotation_pref)
    ใช้ค่า config ภายนอก: prefer_rotation_first, min_support_ratio
    """

    # ====== ค่าคงที่ด้านความนิ่ง (ไม่แตะ config.ini) ======
    COM_MARGIN_RATIO    = 0.40   # ระยะยอมให้ COM ห่าง centroid รองรับ (สัดส่วนของ min(length,width))
    EDGE_MARGIN_RATIO   = 0.12   # กันตกขอบ
    HEAVY_WGT_THRESHOLD = 10.0   # weight ที่ถือว่าหนัก
    SLENDER_TALL_RATIO  = 0.80   # สูง/เพรียว (ต้องการ support เข้มสุด)

    # ---------- utils ----------
    def overlap_1d(a0, a1, b0, b1):
        return not (a1 <= b0 or a0 >= b1)

    def roof_is_clear(x, y, z, bx: Box) -> bool:
        """ต้องโล่ง 100% เหนือกล่อง ณ (x,y,z)"""
        top = z + bx.height
        ax0, ax1 = x, x + bx.length
        ay0, ay1 = y, y + bx.width
        for ob in container.boxes:
            if ob.z < top:
                continue
            bx0, bx1 = ob.x, ob.x + ob.length
            by0, by1 = ob.y, ob.y + ob.width
            if overlap_1d(ax0, ax1, bx0, bx1) and overlap_1d(ay0, ay1, by0, by1):
                return False
        return True

    def blockers_above_rect(x, y, z, bx: Box):
        top = z + bx.height
        ax0, ax1 = x, x + bx.length
        ay0, ay1 = y, y + bx.width
        out = []
        for ob in container.boxes:
            if ob.z < top:
                continue
            bx0, bx1 = ob.x, ob.x + ob.length
            by0, by1 = ob.y, ob.y + ob.width
            if overlap_1d(ax0, ax1, bx0, bx1) and overlap_1d(ay0, ay1, by0, by1):
                out.append(ob)
        return out

    def roof_escape_y_first(x, y, z, bx: Box, rounds: int = 3):
        """
        หนีเงาหลังคา: ลง(Y+) → ขวา(X+) → ขึ้น(Y−) → ซ้าย(X−) (กระโดดทีละทิศ)
        """
        for _ in range(rounds):
            if roof_is_clear(x, y, z, bx):
                return int(x), int(y)
            blks = blockers_above_rect(x, y, z, bx)
            if not blks:
                return int(x), int(y)

            moved = False
            # ลง (Y+)
            x0, x1 = x, x + bx.length
            ny = y
            for ob in blks:
                bx0, bx1 = ob.x, ob.x + ob.length
                if overlap_1d(x0, x1, bx0, bx1):
                    ny = max(ny, ob.y + ob.width)
            if ny != y and ny + bx.width <= container.end_y:
                y = ny; moved = True
            else:
                # ขวา (X+)
                y0, y1 = y, y + bx.width
                nx = x
                for ob in blks:
                    by0, by1 = ob.y, ob.y + ob.width
                    if overlap_1d(y0, y1, by0, by1):
                        nx = max(nx, ob.x + ob.length)
                if nx != x and nx + bx.length <= container.end_x:
                    x = nx; moved = True
                else:
                    # ขึ้น (Y−)
                    ny2 = y
                    for ob in blks:
                        bx0, bx1 = ob.x, ob.x + ob.length
                        if overlap_1d(x0, x1, bx0, bx1):
                            ny2 = min(ny2, ob.y - bx.width)
                    if ny2 != y and ny2 >= container.start_y:
                        y = ny2; moved = True
                    else:
                        # ซ้าย (X−)
                        nx2 = x
                        for ob in blks:
                            by0, by1 = ob.y, ob.y + ob.width
                            if overlap_1d(y0, y1, by0, by1):
                                nx2 = min(nx2, ob.x - bx.length)
                        if nx2 != x and nx2 >= container.start_x:
                            x = nx2; moved = True

            if not moved:
                return None
        return None

    # ---------- support / stability ----------
    def support_contacts(x, y, z, bx: Box):
        """[(pb, area, cx, cy), ...] top=z; PALLET คิดเป็น parent ได้ด้วย"""
        contacts = []
        ax0, ax1 = x, x + bx.length
        ay0, ay1 = y, y + bx.width
        for pb in container.boxes:
            if abs(pb.z + pb.height - z) > 1e-6:
                continue
            bx0, bx1 = pb.x, pb.x + pb.length
            by0, by1 = pb.y, pb.y + pb.width
            if overlap_1d(ax0, ax1, bx0, bx1) and overlap_1d(ay0, ay1, by0, by1):
                ox0, ox1 = max(ax0, bx0), min(ax1, bx1)
                oy0, oy1 = max(ay0, by0), min(ay1, by1)
                area = max(0, ox1 - ox0) * max(0, oy1 - oy0)
                if area > 0:
                    cx = (ox0 + ox1) * 0.5
                    cy = (oy0 + oy1) * 0.5
                    contacts.append((pb, area, cx, cy))
        if z <= container.pallet_height:
            cx = x + bx.length * 0.5
            cy = y + bx.width  * 0.5
            contacts.append(("PALLET", bx.length * bx.width, cx, cy))
        return contacts

    def support_ratio_and_centroid(x, y, z, bx: Box):
        cons = support_contacts(x, y, z, bx)
        tot = bx.length * bx.width
        sup_area = sum(a for _, a, _, _ in cons)
        if sup_area <= 0 or tot <= 0:
            return 0.0, (x + bx.length * 0.5, y + bx.width * 0.5), cons
        cx = sum(a * cx for _, a, cx, _ in cons) / sup_area
        cy = sum(a * cy for _, a, _, cy in cons) / sup_area
        return sup_area / tot, (cx, cy), cons

    def requires_full_support(bx: Box) -> bool:
        slender = bx.height >= max(bx.length, bx.width) * SLENDER_TALL_RATIO
        heavy   = getattr(bx, "wgt", 0) >= HEAVY_WGT_THRESHOLD
        return slender or heavy

    def com_inside_margin(bx_center, sup_center, bx: Box) -> bool:
        cx_box, cy_box = bx_center
        cx_sup, cy_sup = sup_center
        margin = min(bx.length, bx.width) * COM_MARGIN_RATIO * 0.5
        return (abs(cx_box - cx_sup) <= margin) and (abs(cy_box - cy_sup) <= margin)

    def edge_margin_ok(x, y, bx: Box, sup_center) -> bool:
        cx, cy = sup_center
        left   = cx - x
        right  = (x + bx.length) - cx
        bottom = cy - y
        top    = (y + bx.width) - cy
        m_req  = min(bx.length, bx.width) * EDGE_MARGIN_RATIO
        return min(left, right, bottom, top) >= m_req

    def stability_gate(x, y, z, bx: Box):
        """
        ✅ ไม่เช็กจำนวน parent อีกต่อไป
        เงื่อนไข:
          - ถ้าเป็นกล่อง 'สูง/เพรียว' หรือ 'หนัก' → ต้อง support=1.0
          - ถ้าไม่ใช่ → ต้อง support ≥ min_support_ratio
          - COM ต้องอยู่ใกล้ centroid รองรับ (ภายใน margin)
          - Centroid รองรับต้องห่างขอบ footprint (edge margin) พอสมควร
        คืนค่า: ok(bool), stability_score(float), floor(float)
        """
        sup_ratio, sup_centroid, cons = support_ratio_and_centroid(x, y, z, bx)

        if requires_full_support(bx):
            if sup_ratio + 1e-9 < 1.0:
                return False, 0.0, min_support_ratio
            floor = 1.0
        else:
            if sup_ratio + 1e-9 < min_support_ratio:
                return False, 0.0, min_support_ratio
            floor = min_support_ratio

        bx_center = (x + bx.length * 0.5, y + bx.width * 0.5)
        if not com_inside_margin(bx_center, sup_centroid, bx):
            return False, 0.0, floor
        if not edge_margin_ok(x, y, bx, sup_centroid):
            return False, 0.0, floor

        # stability score = support ratio ปรับด้วยระยะ COM (ยิ่งห่างยิ่งลด)
        from math import hypot
        dist = hypot(bx_center[0] - sup_centroid[0], bx_center[1] - sup_centroid[1])
        norm_d = dist / max(1.0, min(bx.length, bx.width))
        score = sup_ratio - 0.5 * norm_d
        return True, score, floor

    # ---------- SNAP อัดชิด ----------
    def snap_compact_iterative(x, y, z, bx: Box, floor: float, max_iters: int = 8):
        def _support_ok(xx, yy):
            s, _, _ = support_ratio_and_centroid(xx, yy, z, bx)
            return s, (s + 1e-9 >= floor and s + 1e-9 >= min_support_ratio)

        def _snap_up(xx, yy):
            ax0, ax1 = xx, xx + bx.length
            y_target = container.start_y
            for ob in container.boxes:
                if abs(ob.z + ob.height - z) > 1e-6: continue
                bx0, bx1 = ob.x, ob.x + ob.length
                if overlap_1d(ax0, ax1, bx0, bx1):
                    y_target = max(y_target, ob.y + ob.width)
            return min(yy, y_target)

        def _snap_left(xx, yy):
            ay0, ay1 = yy, yy + bx.width
            x_target = container.start_x
            for ob in container.boxes:
                if abs(ob.z + ob.height - z) > 1e-6: continue
                by0, by1 = ob.y, ob.y + ob.width
                if overlap_1d(ay0, ay1, by0, by1):
                    x_target = max(x_target, ob.x + ob.length)
            return min(xx, x_target)

        def _edge_glide(xx, yy):
            moved_local = True
            while moved_local:
                moved_local = False
                yy2 = _snap_up(xx, yy)
                if yy2 < yy and roof_is_clear(xx, yy2, z, bx) and container.can_place(bx, xx, yy2, z, optional_check)[0]:
                    s, ok = _support_ok(xx, yy2)
                    if ok: yy = yy2; moved_local = True
                xx2 = _snap_left(xx, yy)
                if xx2 < xx and roof_is_clear(xx2, yy, z, bx) and container.can_place(bx, xx2, yy, z, optional_check)[0]:
                    s, ok = _support_ok(xx2, yy)
                    if ok: xx = xx2; moved_local = True
            return xx, yy

        bx_, by_ = int(x), int(y)
        best_sup, _ = _support_ok(bx_, by_)

        for _ in range(max_iters):
            moved = False
            y_up = _snap_up(bx_, by_)
            if y_up < by_ and roof_is_clear(bx_, y_up, z, bx) and container.can_place(bx, bx_, y_up, z, optional_check)[0]:
                s, ok = _support_ok(bx_, y_up)
                if ok: by_, best_sup, moved = y_up, s, True
            x_left = _snap_left(bx_, by_)
            if x_left < bx_ and roof_is_clear(x_left, by_, z, bx) and container.can_place(bx, x_left, by_, z, optional_check)[0]:
                s, ok = _support_ok(x_left, by_)
                if ok: bx_, best_sup, moved = x_left, s, True
            gx, gy = _edge_glide(bx_, by_)
            if (gx, gy) != (bx_, by_):
                if roof_is_clear(gx, gy, z, bx) and container.can_place(bx, gx, gy, z, optional_check)[0]:
                    s, ok = _support_ok(gx, gy)
                    if ok: bx_, by_, best_sup, moved = gx, gy, s, True
            if not moved: break

        if (bx_ < container.start_x or by_ < container.start_y or
            bx_ + bx.length > container.end_x or by_ + bx.width > container.end_y):
            return None
        return int(bx_), int(by_), best_sup

    # ---------- main ----------
    tried = set()
    candidates = list(container.generate_candidate_positions())
    for b in container.boxes:
        # ขอบขวา และขอบล่าง ของกล่องที่มีอยู่ เพื่อเกิดคอลัมน์/เติมแถว
        candidates.append((int(b.x + b.length), int(b.y),           int(b.z)))
        candidates.append((int(b.x),            int(b.y + b.width),  int(b.z)))

    # ✅ จัดเรียง Z → Y → X (น้อยสุดก่อน)
    candidates = sorted(set(candidates), key=lambda p: (p[2], p[1], p[0]))

    rotation_order = [True, False] if prefer_rotation_first else [False, True]
    valids = []

    for (cx, cy, cz) in candidates:
        for rot in rotation_order:
            key = (cx, cy, cz, rot)
            if key in tried:
                continue
            tried.add(key)

            L0, W0 = box.length, box.width
            if rot:
                box.length, box.width = W0, L0

            # กรอบพื้นที่
            if (cx < container.start_x or cy < container.start_y or cz < container.pallet_height or
                cx + box.length > container.end_x or cy + box.width > container.end_y or
                cz + box.height > container.end_z):
                box.length, box.width = L0, W0
                continue

            # 1) Roof clear ก่อนเสมอ
            escaped = roof_escape_y_first(cx, cy, cz, box, rounds=3)
            if not escaped:
                box.length, box.width = L0, W0
                continue
            x, y = escaped

            # 2) Stability gate รอบแรก (support-only; ไม่เช็กจำนวนพ่อรองรับ)
            ok_stab, stab_score, floor = stability_gate(x, y, cz, box)
            if not ok_stab or not container.can_place(box, x, y, cz, optional_check)[0]:
                box.length, box.width = L0, W0
                continue

            # 3) SNAP อัดชิด
            snapped = snap_compact_iterative(x, y, cz, box, floor=floor, max_iters=8)
            if snapped:
                sx, sy, _ = snapped
            else:
                sx, sy = x, y

            # 4) Stability gate หลัง SNAP + ตรวจซ้ำ
            ok_stab2, stab_score2, _ = stability_gate(sx, sy, cz, box)
            if not ok_stab2 or not roof_is_clear(sx, sy, cz, box) or not container.can_place(box, sx, sy, cz, optional_check)[0]:
                box.length, box.width = L0, W0
                continue

            rot_sort = 0 if rot else 1
            if prefer_rotation_first:
                rot_sort = 1 - rot_sort

            # ผู้ชนะ: Z, -stability_score, Y, X
            valids.append((cz, -stab_score2, sy, sx, rot_sort, sx, sy, rot))
            box.length, box.width = L0, W0

    if not valids:
        return {"status": "Failed","rotation": -1,"support": 0.0,"exceeds_end_z": False,
                "message": ""}
                # "message": "[Hybrid2] No suitable position (support-only gate)"}

    valids.sort()
    z, _, _, _, _, fx, fy, rot = valids[0]

    if rot:
        box.length, box.width = box.width, box.length
    box.set_position(fx, fy, z)

    if not roof_is_clear(fx, fy, z, box):
        return {"status":"Failed","rotation":-1,"support":0.0,"exceeds_end_z":False,"message":"[Hybrid2] Final roof blocked"}
    if not container.can_place(box, fx, fy, z, optional_check)[0]:
        return {"status":"Failed","rotation":-1,"support":0.0,"exceeds_end_z":False,"message":"[Hybrid2] Final collision"}

    container.place_box(box)
    sup_final, _, _ = support_ratio_and_centroid(fx, fy, z, box)
    last_success_positions.append((fx, fy, z, rot))
    return {
        "status":"Confirmed",
        "rotation": 0 if rot else 1,
        "support": sup_final,
        "exceeds_end_z": False,
        # "message": "[Hybrid2] Z,Y,X-first + roof-clear + support-only stability + SNAP"
        "message": ""
    }

def place_box_hybrid3(container: Container, box: Box, optional_check: str = "op2"):
    """
    Hybrid3: Max-tight packing (ignore grouping/priority)
    - คงเงื่อนไข: roof-clear 100% + can_place + support >= min_support_ratio + ไม่ล้น end_z
    - ผู้สมัคร: ขอบคอนเทนเนอร์/ขอบกล่อง (right/bottom edges)
    - จัดลำดับผู้สมัคร: Z -> Y -> X (น้อยสุดก่อน)
    - SNAP อัดชิด (ไม่ใช้ grid): ขึ้น(Y-) -> ซ้าย(X-) + edge-glide จนขยับไม่ได้
    - เลือกผู้ชนะ: (Z, Y, X, rotation_pref, -support)
    - คืน schema ตรงกับ UI: status, rotation(0/1), support, exceeds_end_z, message
    """
    # ----- config (อ้างจากโมดูลระดับไฟล์) -----
    # ใช้ prefer_rotation_first และ min_support_ratio ที่ประกาศไว้ตอน import ด้านบนไฟล์นี้

    # ---------- helpers ----------
    def overlap_1d(a0, a1, b0, b1):
        return not (a1 <= b0 or a0 >= b1)

    def roof_is_clear(x, y, z, bx: Box) -> bool:
        """ด้านบน footprint ของ bx ที่ (x,y,z) ต้องโล่ง 100%"""
        top = z + bx.height
        ax0, ax1 = x, x + bx.length
        ay0, ay1 = y, y + bx.width
        for ob in container.boxes:
            if ob.z < top:
                continue  # ไม่บัง
            bx0, bx1 = ob.x, ob.x + ob.length
            by0, by1 = ob.y, ob.y + ob.width
            if overlap_1d(ax0, ax1, bx0, bx1) and overlap_1d(ay0, ay1, by0, by1):
                return False
        return True

    def support_ratio_at(x, y, z, bx: Box) -> float:
        """สัดส่วนพื้นที่รองรับของ bx ณ ระดับ z (ต้องอยู่บน top ของกล่องอื่น/พื้นพาเลท)"""
        if z <= container.pallet_height:
            return 1.0
        tot = bx.length * bx.width
        if tot <= 0: 
            return 0.0
        ax0, ax1 = x, x + bx.length
        ay0, ay1 = y, y + bx.width
        sup_area = 0
        for pb in container.boxes:
            # ใช้เฉพาะผิวบนที่ระดับ z
            if abs(pb.z + pb.height - z) > 1e-6:
                continue
            bx0, bx1 = pb.x, pb.x + pb.length
            by0, by1 = pb.y, pb.y + pb.width
            if overlap_1d(ax0, ax1, bx0, bx1) and overlap_1d(ay0, ay1, by0, by1):
                ox = max(0, min(ax1, bx1) - max(ax0, bx0))
                oy = max(0, min(ay1, by1) - max(ay0, by0))
                sup_area += ox * oy
        return sup_area / tot

    def snap_up(x, y, z, bx: Box) -> int:
        """หาค่า y ชิดขึ้น (Y-) แบบ exact โดยชนขอบล่างของกล่องในชั้นเดียวกันที่ทับช่วง X"""
        ax0, ax1 = x, x + bx.length
        y_target = container.start_y
        for ob in container.boxes:
            if abs(ob.z + ob.height - z) > 1e-6:
                continue
            bx0, bx1 = ob.x, ob.x + ob.length
            if overlap_1d(ax0, ax1, bx0, bx1):
                y_target = max(y_target, ob.y + ob.width)
        return min(y, y_target)

    def snap_left(x, y, z, bx: Box) -> int:
        """หาค่า x ชิดซ้าย (X-) แบบ exact โดยชนขอบขวาของกล่องในชั้นเดียวกันที่ทับช่วง Y"""
        ay0, ay1 = y, y + bx.width
        x_target = container.start_x
        for ob in container.boxes:
            if abs(ob.z + ob.height - z) > 1e-6:
                continue
            by0, by1 = ob.y, ob.y + ob.width
            if overlap_1d(ay0, ay1, by0, by1):
                x_target = max(x_target, ob.x + ob.length)
        return min(x, x_target)

    def snap_compact_exact(x, y, z, bx: Box, floor: float, max_iters: int = 12):
        """
        อัดชิดแบบ exact (ไม่ใช้ grid):
          วน: y <- snap_up(...), x <- snap_left(...), แล้ว edge-glide (up→left) จนขยับไม่ได้
          ทุกครั้งต้องผ่าน roof_clear + can_place + support ≥ max(floor, min_support_ratio)
        """
        best_x, best_y = int(x), int(y)
        best_sup = support_ratio_at(best_x, best_y, z, bx)
        sup_floor = max(floor, min_support_ratio) - 1e-9

        def _try(nx, ny):
            if nx < container.start_x or ny < container.start_y:
                return None
            if nx + bx.length > container.end_x or ny + bx.width > container.end_y:
                return None
            if not roof_is_clear(nx, ny, z, bx):
                return None
            ok, _ = container.can_place(bx, nx, ny, z, optional_check)
            if not ok:
                return None
            s = support_ratio_at(nx, ny, z, bx)
            if s < sup_floor:
                return None
            return int(nx), int(ny), s

        for _ in range(max_iters):
            moved = False
            # 1) ขึ้น (Y-)
            ny = snap_up(best_x, best_y, z, bx)
            if ny < best_y:
                probe = _try(best_x, ny)
                if probe:
                    best_x, best_y, best_sup = probe
                    moved = True
            # 2) ซ้าย (X-)
            nx = snap_left(best_x, best_y, z, bx)
            if nx < best_x:
                probe = _try(nx, best_y)
                if probe:
                    best_x, best_y, best_sup = probe
                    moved = True
            # 3) edge-glide (up → left) จนสุด
            while True:
                changed = False
                ny2 = snap_up(best_x, best_y, z, bx)
                if ny2 < best_y:
                    probe = _try(best_x, ny2)
                    if probe:
                        best_x, best_y, best_sup = probe
                        changed = True
                nx2 = snap_left(best_x, best_y, z, bx)
                if nx2 < best_x:
                    probe = _try(nx2, best_y)
                    if probe:
                        best_x, best_y, best_sup = probe
                        changed = True
                if not changed:
                    break
            if not moved:
                break

        return best_x, best_y, best_sup

    # ---------- รวบรวมผู้สมัคร (ขอบคอนเทนเนอร์/ขอบกล่อง) ----------
    candidates = set()
    candidates.add((int(container.start_x), int(container.start_y), int(container.pallet_height)))
    for b in container.boxes:
        candidates.add((int(b.x + b.length), int(b.y),           int(b.z)))  # ขอบขวา
        candidates.add((int(b.x),            int(b.y + b.width), int(b.z)))  # ขอบล่าง

    # ✅ เรียงผู้สมัคร Z → Y → X เพื่อเติมชั้นและอัดมุมซ้ายบนก่อน
    candidates = sorted(candidates, key=lambda p: (p[2], p[1], p[0]))

    rotation_order = [True, False] if prefer_rotation_first else [False, True]
    valids = []

    # ---------- ประเมินผู้สมัคร ----------
    for (cx, cy, cz) in candidates:
        for rot in rotation_order:
            L0, W0 = box.length, box.width
            if rot:
                box.length, box.width = W0, L0

            # guard ขอบเขตพื้นฐาน
            if (cx < container.start_x or cy < container.start_y or cz < container.pallet_height or
                cx + box.length > container.end_x or cy + box.width > container.end_y or
                cz + box.height > container.end_z):
                box.length, box.width = L0, W0
                continue

            # ต้องโล่งด้านบน 100%
            if not roof_is_clear(cx, cy, cz, box):
                box.length, box.width = L0, W0
                continue

            # ห้ามชน
            can, _ = container.can_place(box, cx, cy, cz, optional_check)
            if not can:
                box.length, box.width = L0, W0
                continue

            # ต้องมีพื้นที่รองรับเพียงพอ
            sup0 = support_ratio_at(cx, cy, cz, box)
            if sup0 + 1e-9 < min_support_ratio:
                box.length, box.width = L0, W0
                continue

            # SNAP อัดชิด (ขึ้น→ซ้าย) แบบ exact
            sx, sy, sfin = snap_compact_exact(cx, cy, cz, box, floor=sup0, max_iters=12)

            # ตรวจรอบสุดท้าย
            if not roof_is_clear(sx, sy, cz, box):
                box.length, box.width = L0, W0
                continue
            can2, _ = container.can_place(box, sx, sy, cz, optional_check)
            if not can2:
                box.length, box.width = L0, W0
                continue
            if sfin + 1e-9 < min_support_ratio:
                box.length, box.width = L0, W0
                continue

            rot_sort = 0 if rot else 1
            if prefer_rotation_first:
                rot_sort = 1 - rot_sort

            # เลือกชั้นล่าง → แถวบน → คอลัมน์ซ้าย → (ตาม rotation_pref) → support สูง
            valids.append((cz, sy, sx, rot_sort, -sfin, sx, sy, rot))
            box.length, box.width = L0, W0

    if not valids:
        return {
            "status": "Failed",
            "rotation": -1,
            "support": 0.0,
            "exceeds_end_z": False,
            "message": "[Hybrid3] No suitable position"
        }

    # ---------- เลือกผู้ชนะ ----------
    valids.sort()
    z, _, _, _, neg_sup, fx, fy, rot = valids[0]
    sup_best = -neg_sup

    # ตั้งค่าตาม schema UI (rotation: 0=หมุน, 1=ไม่หมุน)
    if rot:
        box.length, box.width = box.width, box.length
    box.set_position(int(fx), int(fy), int(z))

    exceeds = (box.z + box.height > container.end_z)
    if exceeds:
        return {
            "status": "Failed",
            "rotation": -1,
            "support": 0.0,
            "exceeds_end_z": True,
            "message": "[Hybrid3] Exceeds container height"
        }

    container.place_box(box)
    last_success_positions.append((int(fx), int(fy), int(z), rot))

    return {
        "status": "Confirmed",
        "rotation": 0 if rot else 1,
        "support": float(sup_best),
        "exceeds_end_z": False,
        "message": "[Hybrid3] Max-tight: Z,Y,X-first + roof-clear + exact SNAP (up→left)"
    }
