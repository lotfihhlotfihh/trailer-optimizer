import itertools
from dataclasses import dataclass
from typing import List, Tuple

COLORS = [
    '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7',
    '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9',
    '#82E0AA', '#F1948A', '#AED6F1', '#A9DFBF', '#FAD7A0',
    '#D7BDE2', '#A3E4D7', '#F9E79F', '#FADBD8', '#D5DBDB'
]

@dataclass
class Item:
    id: int
    name: str
    length: float
    width: float
    height: float
    weight: float
    fragile: bool = False
    can_rotate: bool = True
    non_gerbable: bool = False
    lot: str = ''
    color: str = '#4ECDC4'

    def get_rotations(self) -> List[Tuple[float, float, float]]:
        if not self.can_rotate:
            return [(self.length, self.width, self.height)]
        dims = [self.length, self.width, self.height]
        return list(set(itertools.permutations(dims)))

    @property
    def volume(self) -> float:
        return self.length * self.width * self.height


@dataclass
class Placement:
    item: Item
    x: float
    y: float
    z: float
    l: float
    w: float
    h: float


class TrailerOptimizer:
    def __init__(self, trailer_l: float, trailer_w: float, trailer_h: float, max_weight: float):
        self.tl = trailer_l
        self.tw = trailer_w
        self.th = trailer_h
        self.max_weight = max_weight
        self.placements: List[Placement] = []
        self.current_weight = 0.0
        self.extreme_points: List[Tuple[float, float, float]] = [(0.0, 0.0, 0.0)]

    def _overlaps(self, x1, y1, z1, l1, w1, h1, x2, y2, z2, l2, w2, h2, tol=1e-5) -> bool:
        return (
            x1 < x2 + l2 - tol and x1 + l1 > x2 + tol and
            y1 < y2 + w2 - tol and y1 + w1 > y2 + tol and
            z1 < z2 + h2 - tol and z1 + h1 > z2 + tol
        )

    def _can_place(self, x, y, z, l, w, h, item: Item) -> bool:
        tol = 1e-5
        # Bounds check
        if (x < -tol or y < -tol or z < -tol or
                x + l > self.tl + tol or
                y + w > self.tw + tol or
                z + h > self.th + tol):
            return False

        # Weight check
        if self.current_weight + item.weight > self.max_weight + tol:
            return False

        # Overlap check
        for p in self.placements:
            if self._overlaps(x, y, z, l, w, h, p.x, p.y, p.z, p.l, p.w, p.h):
                return False

        # Fragility: new item must NOT be placed on top of a fragile item
        # Non gerbable: nothing can be stacked on top of a non-stackable item
        for p in self.placements:
            if p.item.fragile or p.item.non_gerbable:
                if abs(z - (p.z + p.h)) < tol:
                    ox = min(x + l, p.x + p.l) - max(x, p.x)
                    oy = min(y + w, p.y + p.w) - max(y, p.y)
                    if ox > tol and oy > tol:
                        return False

        # Support check: if floating, must be supported >= 30% of base
        if z > tol:
            base_area = l * w
            supported = 0.0
            for p in self.placements:
                if abs(p.z + p.h - z) < tol:
                    ox = min(x + l, p.x + p.l) - max(x, p.x)
                    oy = min(y + w, p.y + p.w) - max(y, p.y)
                    if ox > tol and oy > tol:
                        supported += ox * oy
            if supported < 0.3 * base_area:
                return False

        return True

    def _add_extreme_points(self, p: Placement):
        candidates = [
            (p.x + p.l, p.y, p.z),
            (p.x, p.y + p.w, p.z),
            (p.x, p.y, p.z + p.h),
            (p.x + p.l, p.y + p.w, p.z),
            (p.x + p.l, p.y, p.z + p.h),
            (p.x, p.y + p.w, p.z + p.h),
        ]
        for pt in candidates:
            if pt not in self.extreme_points:
                self.extreme_points.append(pt)

    def optimize(self, items: List[Item]):
        # Non-fragile (heavy, large) first; fragile last (go on top)
        sorted_items = sorted(items, key=lambda i: (i.fragile, -i.volume))

        unplaced = []
        for item in sorted_items:
            best: Placement | None = None
            best_score = float('inf')

            # Sort extreme points: prefer low z, then low x, then low y
            sorted_eps = sorted(
                self.extreme_points,
                key=lambda pt: (round(pt[2], 4), round(pt[0], 4), round(pt[1], 4))
            )

            for ep in sorted_eps:
                x, y, z = ep
                for l, w, h in item.get_rotations():
                    if self._can_place(x, y, z, l, w, h, item):
                        score = z * 10000 + x * 100 + y
                        if score < best_score:
                            best_score = score
                            best = Placement(item, x, y, z, l, w, h)

            if best:
                self.placements.append(best)
                self.current_weight += item.weight
                self._add_extreme_points(best)
            else:
                unplaced.append(item)

        return self.placements, unplaced

    def get_stats(self) -> dict:
        if not self.placements:
            return {}
        used_vol = sum(p.l * p.w * p.h for p in self.placements)
        total_vol = self.tl * self.tw * self.th
        return {
            'fill_rate': used_vol / total_vol * 100,
            'total_weight': self.current_weight,
            'weight_rate': self.current_weight / self.max_weight * 100,
            'items_placed': len(self.placements),
            'trailer_volume': total_vol,
            'used_volume': used_vol,
        }
