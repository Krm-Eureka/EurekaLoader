import configparser
import os
from typing import List, Tuple
from Models.Box import Box
from Models.Container import Container
from Service.shared_state import last_success_positions

config = configparser.ConfigParser()
config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.ini")
config.read(config_path, encoding="utf-8")

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

    def distance_to_edge(x: int, y: int) -> float:
        dx = min(x - container.start_x, container.end_x - x)
        dy = min(y - container.start_y, container.end_y - y)
        return min(dx, dy)

    def count_adjacent_xy(box: Box) -> int:
        margin = 2
        count = 0
        for b in container.boxes:
            if abs(b.z - box.z) > 1e-6:
                continue
            if (
                abs(b.x + b.length - box.x) < margin or
                abs(box.x + box.length - b.x) < margin or
                abs(b.y + b.width - box.y) < margin or
                abs(box.y + box.width - b.y) < margin
            ):
                count += 1
        return count

    tried_positions = set()
    candidate_positions = container.generate_candidate_positions()

    # 🔁 จัดกลุ่มตาม Z แล้วพิจารณาทีละชั้น Z ต่ำก่อน
    z_groups = {}
    for pos in candidate_positions:
        z_groups.setdefault(pos[2], []).append(pos)
    for z in sorted(z_groups):
        # positions = sorted(z_groups[z], key=lambda pos: distance_to_edge(pos[0], pos[1]))
        positions = sorted(z_groups[z], key=lambda pos: (z, distance_to_edge(pos[0], pos[1]), pos[0], pos[1]))


        best_result = None
        best_score = -float("inf")

        for x, y, _ in positions:
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

                support_ratio = calculate_support_ratio(box)
                clearance_ok = has_vertical_clearance(box, container.boxes, container.height)
                if not clearance_ok or support_ratio < min_support_ratio:
                    box.length, box.width = original_length, original_width
                    continue

                if (box.x + box.length > container.end_x or
                    box.y + box.width > container.end_y or
                    box.z + box.height > container.end_z):
                    box.length, box.width = original_length, original_width
                    continue

                adjacent_count = count_adjacent_xy(box)
                z_bonus = 1.0 - (z / container.total_height)
                edge_penalty = 1.0 - min(1.0, adjacent_count * 0.3)
                score = (support_ratio * 1.5) + (adjacent_count * 0.1) + z_bonus - edge_penalty

                final_check, _ = container.can_place(box, x, y, z, optional_check)
                if not final_check:
                    box.length, box.width = original_length, original_width
                    continue

                if score > best_score:
                    best_score = score
                    best_result = {
                        "x": x, "y": y, "z": z,
                        "rotation": rotation,
                        "support": support_ratio,
                        "adjacent": adjacent_count,
                        "score": score
                    }

                box.length, box.width = original_length, original_width

        if best_result:
            if best_result["rotation"]:
                box.length, box.width = box.width, box.length
            box.set_position(best_result["x"], best_result["y"], best_result["z"])
            container.place_box(box)
            last_success_positions.append((best_result["x"], best_result["y"], best_result["z"], best_result["rotation"]))
            print(f"[Hybrid ✅] Placed {box.sku} at ({box.x},{box.y},{box.z}) R={best_result['rotation']} | Score={best_result['score']:.2f}")
            return {
                "status": "Confirmed",
                "rotation": 0 if best_result["rotation"] else 1,
                "support": best_result["support"],
                "exceeds_end_z": False,
                "message": f"Placed at Z={best_result['z']} with support {best_result['support']:.2f} and {best_result['adjacent']} neighbors"
            }

    print(f"[Hybrid ❌] No valid position found for {box.sku}")
    return {
        "status": "Failed",
        "rotation": -1,
        "support": 0.0,
        "exceeds_end_z": False,
        "message": "No suitable position found"
    }
