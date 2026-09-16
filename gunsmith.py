# -*- coding: utf-8 -*-
"""The drawing and solid-modelling half of the gun builder.

Three things live here, and none of them know anything about Minecraft.

`Sketch` is a side elevation drawn with shapes rather than characters. The earlier version of these
guns was typed out as ASCII at one character per model unit, which was readable but far too coarse to
draw a trigger guard you could see through or a muzzle that was round. Shapes take floating point model
units, so a guard is an actual annulus and a barrel is an actual circle, and the grid underneath can be
as fine as it likes - a third of a unit, here, which is four and a half millimetres at the scale a
Minecraft block is a metre.

`section` is the part that makes these solid rather than flat. Extruding a side view to a constant
thickness is what produced the slab-sided models: real weapons are round where they are round. Every
material carries a cross-section - a circle for barrels, a softened rectangle for receivers, a flat
slab for sights and levers - and the extruder asks, for every cell, how wide that material should be at
that height within its own run. A barrel therefore comes out round without anybody drawing it round.

`solidify` turns the result into the fewest boxes that will cover it, merging along all three axes.
That merge is the only reason this is affordable: a pistol is about a hundred and forty thousand cells
and comes out as a few hundred boxes.
"""
import math

RES = 3          # cells per model unit, in every axis


class Sketch:
    """A side elevation. x runs along the barrel, y runs up, both in model units."""

    def __init__(self, length, height):
        self.length = length
        self.height = height
        self.wide = int(round(length * RES))
        self.tall = int(round(height * RES))
        self.cells = [[None] * self.wide for _ in range(self.tall)]

    # -- helpers ---------------------------------------------------------
    def _put(self, cx, cy, material):
        if 0 <= cx < self.wide and 0 <= cy < self.tall:
            self.cells[cy][cx] = material

    def _cells_x(self, x0, x1):
        return range(max(0, int(math.floor(x0 * RES))),
                     min(self.wide, int(math.ceil(x1 * RES))))

    def _cells_y(self, y0, y1):
        # y is given in model units from the bottom; rows are stored top first.
        low = max(0, int(math.floor((self.height - y1) * RES)))
        high = min(self.tall, int(math.ceil((self.height - y0) * RES)))
        return range(low, high)

    # -- primitives ------------------------------------------------------
    def rect(self, material, x0, y0, x1, y1):
        for cy in self._cells_y(y0, y1):
            for cx in self._cells_x(x0, x1):
                self._put(cx, cy, material)
        return self

    def rrect(self, material, x0, y0, x1, y1, radius=0.4):
        """A rectangle with its corners taken off - the shape almost every gun part actually is."""
        for cy in self._cells_y(y0, y1):
            for cx in self._cells_x(x0, x1):
                x = (cx + 0.5) / RES
                y = self.height - (cy + 0.5) / RES
                dx = max(x0 + radius - x, 0, x - (x1 - radius))
                dy = max(y0 + radius - y, 0, y - (y1 - radius))
                if dx * dx + dy * dy <= radius * radius:
                    self._put(cx, cy, material)
        return self

    def ellipse(self, material, cx0, cy0, rx, ry):
        for cy in self._cells_y(cy0 - ry, cy0 + ry):
            for cx in self._cells_x(cx0 - rx, cx0 + rx):
                x = (cx + 0.5) / RES
                y = self.height - (cy + 0.5) / RES
                if ((x - cx0) / rx) ** 2 + ((y - cy0) / ry) ** 2 <= 1.0:
                    self._put(cx, cy, material)
        return self

    def ring(self, material, cx0, cy0, rx, ry, thickness):
        """An annulus. This is what a trigger guard is, and why one can now be seen through."""
        inner_x = max(0.05, rx - thickness)
        inner_y = max(0.05, ry - thickness)
        for cy in self._cells_y(cy0 - ry, cy0 + ry):
            for cx in self._cells_x(cx0 - rx, cx0 + rx):
                x = (cx + 0.5) / RES
                y = self.height - (cy + 0.5) / RES
                outside = ((x - cx0) / rx) ** 2 + ((y - cy0) / ry) ** 2
                inside = ((x - cx0) / inner_x) ** 2 + ((y - cy0) / inner_y) ** 2
                if outside <= 1.0 < inside:
                    self._put(cx, cy, material)
        return self

    def taper(self, material, x0, y0, x1, y1, top_shift=0.0, bottom_shift=0.0):
        """A quadrilateral: the top edge slid one way, the bottom edge the other.

        A pistol grip is this and nothing else - the whole thing leans back, and leaning is what the
        old stepped stack of boxes was pretending to do.
        """
        for cy in self._cells_y(y0, y1):
            y = self.height - (cy + 0.5) / RES
            share = (y - y0) / max(1e-6, y1 - y0)
            shift = bottom_shift + (top_shift - bottom_shift) * share
            for cx in self._cells_x(x0 + min(0, shift) - 0.1, x1 + max(0, shift) + 0.1):
                x = (cx + 0.5) / RES
                if x0 + shift <= x <= x1 + shift:
                    self._put(cx, cy, material)
        return self

    def recolour(self, material, x0, y0, x1, y1):
        """Repaints only where there is already something.

        A band round a roll of gauze, the fluid inside a syringe barrel, a label on a bottle: all of
        them are a rectangle that must stop at the edge of a curve somebody else drew. Painting them as
        rectangles instead gives a band with square ends sticking out of a circle.
        """
        for cy in self._cells_y(y0, y1):
            for cx in self._cells_x(x0, x1):
                if 0 <= cx < self.wide and 0 <= cy < self.tall and self.cells[cy][cx] is not None:
                    self.cells[cy][cx] = material
        return self

    def erase(self, x0, y0, x1, y1):
        for cy in self._cells_y(y0, y1):
            for cx in self._cells_x(x0, x1):
                self._put(cx, cy, None)
        return self

    def stripe(self, material, x0, y0, x1, y1, step, width):
        """Evenly spaced cuts - cooling slots in a handguard, grooves in a pump."""
        x = x0
        while x < x1:
            self.rect(material, x, y0, min(x1, x + width), y1)
            x += step
        return self


# ---------------------------------------------------------------- cross sections
def half_width(section, widest, share):
    """How wide a material is, at a height `share` of the way down its own run.

    This is the whole of the third dimension. A barrel asked at its top and bottom answers "almost
    nothing" and in the middle answers "all of it", so it comes out round; a receiver answers "all of
    it" until very near its edges and so comes out as a slab with the corners broken.
    """
    middle = 2.0 * share - 1.0          # -1 at the top of the run, +1 at the bottom
    if section == "round":
        return widest * math.sqrt(max(0.0, 1.0 - middle * middle))
    if section == "soft":
        return widest * (1.0 - 0.30 * middle ** 4)
    if section == "dee":
        # Flat on top, round underneath: a slide, a receiver with a rounded belly.
        return widest if middle <= 0 else widest * math.sqrt(max(0.0, 1.0 - middle * middle * 0.8))
    return widest


def quantise(value, steps, widest):
    """Rounds a half-width to one of a few values, so neighbouring cells merge instead of stepping."""
    if steps <= 1 or widest <= 0:
        return widest
    unit = widest / steps
    return max(unit, round(value / unit) * unit)


def solidify(sketch, materials, steps=5):
    """Turns the sketch into a voxel grid, then into the fewest boxes that cover it.

    Returns boxes as (material, x0, y0, z0, x1, y1, z1) in model units.
    """
    wide, tall = sketch.wide, sketch.tall
    cells = sketch.cells

    # How far each material's run extends in this column, so the cross section knows where it is.
    voxels = {}
    for cx in range(wide):
        cy = 0
        while cy < tall:
            material = cells[cy][cx]
            if material is None:
                cy += 1
                continue
            end = cy
            while end + 1 < tall and cells[end + 1][cx] == material:
                end += 1
            run = end - cy + 1
            widest, section = materials[material][2], materials[material][3]
            for step in range(run):
                share = (step + 0.5) / run
                half = quantise(half_width(section, widest, share), steps, widest)
                depth = max(1, int(round(half * RES)))
                for cz in range(-depth, depth):
                    voxels[(cx, cy + step, cz)] = material
            cy = end + 1

    # Greedy merge, x then y then z.
    taken = set()
    boxes = []
    for key in sorted(voxels):
        if key in taken:
            continue
        cx, cy, cz = key
        material = voxels[key]

        span = 1
        while voxels.get((cx + span, cy, cz)) == material and (cx + span, cy, cz) not in taken:
            span += 1
        deep = 1
        while all(voxels.get((cx + s, cy + deep, cz)) == material
                  and (cx + s, cy + deep, cz) not in taken for s in range(span)):
            deep += 1
        thick = 1
        while all(voxels.get((cx + s, cy + d, cz + thick)) == material
                  and (cx + s, cy + d, cz + thick) not in taken
                  for s in range(span) for d in range(deep)):
            thick += 1

        for s in range(span):
            for d in range(deep):
                for t in range(thick):
                    taken.add((cx + s, cy + d, cz + t))

        x0 = cx / float(RES)
        x1 = (cx + span) / float(RES)
        y1 = sketch.height - cy / float(RES)
        y0 = sketch.height - (cy + deep) / float(RES)
        z0 = 8.0 + cz / float(RES)
        z1 = 8.0 + (cz + thick) / float(RES)
        boxes.append((material, x0, y0, z0, x1, y1, z1))
    return boxes
